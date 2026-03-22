"""
uploader.py
───────────
노션 페이지 → 1000.school 업로드 메인 스크립트

사용 전: notion_auth.py 실행해서 NOTION_ACCESS_TOKEN을 먼저 받아두세요.

사용법:
  # 1000.school 스니펫 목록 조회
  python uploader.py --snippets

  # 특정 스니펫 단건 조회
  python uploader.py --snippet <SNIPPET_ID>

  # 노션 페이지 목록 보기
  python uploader.py --list

  # 노션 단일 페이지 업로드
  python uploader.py --page <PAGE_ID>

  # 검색해서 업로드
  python uploader.py --search "블로그 포스트"

  # 데이터베이스 전체 업로드
  python uploader.py --database <DATABASE_ID>
"""

import os
import json
import time
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

from notion_reader   import NotionReader, download_image
from school_uploader import SchoolUploader

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── 설정 ────────────────────────────────────────────────────────
NOTION_TOKEN  = os.getenv("NOTION_ACCESS_TOKEN", "")
SCHOOL_TOKEN  = os.getenv("SCHOOL_API_TOKEN", "")
IMAGE_DIR     = Path(os.getenv("IMAGE_DIR", "./downloaded_images"))
IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def _check_env(need_notion: bool = True):
    missing = []
    if need_notion and not NOTION_TOKEN:
        missing.append("NOTION_ACCESS_TOKEN (notion_auth.py 먼저 실행)")
    if not SCHOOL_TOKEN:
        missing.append("SCHOOL_API_TOKEN")
    if missing:
        for m in missing:
            log.error(f"누락된 환경변수: {m}")
        raise SystemExit(1)


# ── 1000.school 조회 ─────────────────────────────────────────────
def show_snippets(uploader: SchoolUploader):
    """GET /daily-snippets — 전체 목록 출력"""
    log.info("📋 1000.school 스니펫 목록 조회 중...")
    data = uploader.list_snippets()
    print(json.dumps(data, ensure_ascii=False, indent=2))


def show_snippet(snippet_id: str, uploader: SchoolUploader):
    """GET /daily-snippets/{id} — 단건 출력"""
    log.info(f"🔍 스니펫 조회: {snippet_id}")
    data = uploader.get_snippet(snippet_id)
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ── 노션 → 업로드 파이프라인 ─────────────────────────────────────
def upload_page(page_id: str, reader: NotionReader, uploader: SchoolUploader) -> dict:
    log.info(f"📄 노션 페이지 가져오는 중: {page_id}")
    page  = reader.get_page(page_id)
    title = reader.extract_title(page)
    log.info(f"   제목: {title}")

    log.info("📝 본문 파싱 중...")
    body, image_urls = reader.parse_page(page_id)
    log.info(f"   본문 {len(body)}자 / 이미지 {len(image_urls)}개")

    if image_urls:
        log.info("🖼️  이미지 다운로드 중...")
        for url in image_urls:
            path = download_image(url, IMAGE_DIR)
            if path:
                log.info(f"   저장: {path.name}")

    log.info("🚀 1000.school /daily-snippets 에 업로드 중...")
    result = uploader.create_snippet(title, body)
    log.info("✅ 업로드 완료!")
    log.info(f"   응답: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def list_notion_pages(reader: NotionReader):
    """접근 가능한 노션 페이지 목록 출력"""
    log.info("📋 접근 가능한 노션 페이지 목록:")
    pages = reader.search_pages()
    if not pages:
        log.info("  (없음 — 노션에서 Integration 연결이 필요합니다)")
        return
    for p in pages:
        pid   = p["id"]
        title = reader.extract_title(p)
        print(f"  [{pid}] {title}")


def upload_by_search(query: str, reader: NotionReader, uploader: SchoolUploader):
    log.info(f"🔍 '{query}' 검색 중...")
    pages = reader.search_pages(query)
    if not pages:
        log.warning("검색 결과 없음")
        return
    log.info(f"   {len(pages)}개 페이지 발견")
    for page in pages:
        upload_page(page["id"], reader, uploader)
        time.sleep(0.5)


def upload_database(db_id: str, reader: NotionReader, uploader: SchoolUploader,
                    filter_body: dict = None):
    pages = reader.query_database(db_id, filter_body)
    log.info(f"📊 데이터베이스 페이지 {len(pages)}개")
    for i, page in enumerate(pages, 1):
        log.info(f"[{i}/{len(pages)}] 처리 중...")
        try:
            upload_page(page["id"], reader, uploader)
        except Exception as e:
            log.error(f"  실패: {e}")
        time.sleep(0.5)


# ── CLI ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="노션 → 1000.school 업로더")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--snippets",  action="store_true",  help="1000.school 스니펫 전체 목록 조회")
    group.add_argument("--snippet",   metavar="ID",         help="1000.school 스니펫 단건 조회")
    group.add_argument("--list",      action="store_true",  help="접근 가능한 노션 페이지 목록")
    group.add_argument("--page",      metavar="PAGE_ID",    help="노션 단일 페이지 업로드")
    group.add_argument("--search",    metavar="쿼리",        help="검색어로 노션 페이지 찾아 업로드")
    group.add_argument("--database",  metavar="DB_ID",      help="노션 데이터베이스 전체 업로드")
    args = parser.parse_args()

    # 조회 전용 명령은 NOTION_TOKEN 불필요
    need_notion = args.page or args.list or args.search or args.database
    _check_env(need_notion=bool(need_notion))

    uploader = SchoolUploader(SCHOOL_TOKEN)

    if args.snippets:
        show_snippets(uploader)
    elif args.snippet:
        show_snippet(args.snippet, uploader)
    else:
        reader = NotionReader(NOTION_TOKEN)
        if args.list:
            list_notion_pages(reader)
        elif args.page:
            upload_page(args.page, reader, uploader)
        elif args.search:
            upload_by_search(args.search, reader, uploader)
        elif args.database:
            upload_database(args.database, reader, uploader)


if __name__ == "__main__":
    main()