"""
watcher.py
──────────
노션 "데일리 스니펫" DB를 폴링하여
'스니펫 업로드' 체크박스가 체크된 페이지를
자동으로 1000.school /daily-snippets 에 업로드합니다.

사용법:
  python watcher.py              # 기본 (60초마다 폴링)
  python watcher.py --interval 30  # 30초마다 폴링

흐름:
  1. DB에서 '스니펫 업로드 = True' 이고 아직 처리 안 된 페이지 조회
  2. 페이지 본문(content) 파싱
  3. POST /daily-snippets { date, content }
  4. 업로드 완료 후 노션 페이지의 '스니펫 업로드' 체크박스를 False로 되돌림
     (중복 업로드 방지)
"""

import os
import json
import time
import logging
import argparse
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from notion_reader import NotionReader

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
SCHOOL_URL    = os.getenv("SCHOOL_API_URL", "https://api.1000.school")

# 노션 DB ID — 하이픈 포함/미포함 둘 다 허용
_raw_db_id    = os.getenv("NOTION_DATABASE_ID", "3270b56c63ab80398288da19d277ec80")
DATABASE_ID   = _raw_db_id  # 노션 API는 하이픈 포함 UUID를 그대로 받음

# 노션 DB 컬럼명 (스크린샷 기준)
COL_UPLOAD    = "스니펫 업로드"   # Checkbox 컬럼
NOTION_VERSION = "2022-06-28"


# ── 노션 API ─────────────────────────────────────────────────────
def notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def query_db_pending() -> list[dict]:
    """'스니펫 업로드' 체크박스가 True인 페이지 목록 조회"""
    res = requests.post(
        f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
        headers=notion_headers(),
        json={
            "filter": {
                "property": COL_UPLOAD,
                "checkbox": {"equals": True},
            }
        },
        timeout=20,
    )
    res.raise_for_status()
    return res.json().get("results", [])


def uncheck_upload(page_id: str):
    """업로드 완료 후 체크박스를 False로 되돌려 중복 방지"""
    requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=notion_headers(),
        json={
            "properties": {
                COL_UPLOAD: {"checkbox": False}
            }
        },
        timeout=20,
    )


def get_page_blocks(page_id: str) -> tuple[str, str]:
    """페이지 제목 + 본문 마크다운 반환"""
    reader = NotionReader(NOTION_TOKEN)
    page   = reader.get_page(page_id)
    title  = reader.extract_title(page)
    body, _= reader.parse_page(page_id)
    return title, body


def get_created_date(page: dict) -> str:
    """페이지 생성 일시 → 'YYYY-MM-DD' 형식"""
    created = page.get("created_time", "")
    if created:
        return created[:10]  # "2026-03-18T..." → "2026-03-18"
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── 1000.school API ──────────────────────────────────────────────
def upload_snippet(date: str, content: str) -> dict:
    """POST /daily-snippets"""
    res = requests.post(
        f"{SCHOOL_URL}/daily-snippets",
        headers={
            "Authorization": f"Bearer {SCHOOL_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "date":    date,
            "content": content,
        },
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


# ── 메인 루프 ────────────────────────────────────────────────────
def process_once():
    """한 번 폴링: 대기 중인 페이지 모두 처리"""
    try:
        pending = query_db_pending()
    except requests.HTTPError as e:
        log.error(f"DB 조회 실패: {e.response.status_code} {e.response.text[:200]}")
        return

    if not pending:
        log.debug("업로드 대기 페이지 없음")
        return

    log.info(f"📋 업로드 대기 페이지 {len(pending)}개 발견")

    for page in pending:
        page_id = page["id"]
        date    = get_created_date(page)

        try:
            title, body = get_page_blocks(page_id)
            log.info(f"  📄 처리 중: [{date}] {title or '제목없음'}")

            if not body.strip():
                log.warning(f"  ⚠️  본문이 비어있어 건너뜀: {page_id}")
                continue

            result = upload_snippet(date, body)
            snippet_id = result.get("id", "?")
            log.info(f"  ✅ 업로드 완료 → snippet_id: {snippet_id}")

            # 체크박스 해제 (중복 방지)
            uncheck_upload(page_id)
            log.info(f"  🔄 체크박스 해제 완료")

        except requests.HTTPError as e:
            log.error(f"  ❌ 업로드 실패: {e.response.status_code} {e.response.text[:300]}")
        except Exception as e:
            log.error(f"  ❌ 오류: {e}")

        time.sleep(0.3)  # API 속도 제한 방지


def run(interval: int):
    log.info("=" * 50)
    log.info("  노션 → 1000.school 자동 업로더 시작")
    log.info(f"  폴링 간격: {interval}초")
    log.info(f"  DB ID    : {DATABASE_ID}")
    log.info("=" * 50)
    log.info("노션에서 '스니펫 업로드' 체크박스를 체크하면 자동 업로드됩니다.")
    log.info("종료: Ctrl+C\n")

    while True:
        process_once()
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="노션 DB → 1000.school 자동 업로더")
    parser.add_argument("--interval", type=int, default=60, help="폴링 간격(초), 기본 60")
    parser.add_argument("--once",     action="store_true",  help="한 번만 실행하고 종료")
    args = parser.parse_args()

    if args.once:
        process_once()
    else:
        run(args.interval)