"""
notion_reader.py
────────────────
노션 페이지/데이터베이스의 내용을 읽어오는 모듈.
OAuth Access Token으로 인증합니다.
"""

import os
import time
import mimetypes
import requests
from pathlib import Path
from typing import Optional


NOTION_VERSION = "2022-06-28"


class NotionReader:
    BASE = "https://api.notion.com/v1"

    def __init__(self, access_token: str):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    # ── 내부 요청 헬퍼 ──────────────────────────────────────────
    def _get(self, path: str) -> dict:
        res = requests.get(f"{self.BASE}{path}", headers=self.headers, timeout=20)
        res.raise_for_status()
        return res.json()

    def _post(self, path: str, body: dict) -> dict:
        res = requests.post(f"{self.BASE}{path}", headers=self.headers, json=body, timeout=20)
        res.raise_for_status()
        return res.json()

    def _fmt_id(self, raw: str) -> str:
        """32자리 hex → UUID 포맷 (이미 포맷돼 있으면 그대로)"""
        c = raw.replace("-", "")
        if len(c) != 32:
            return raw
        return f"{c[:8]}-{c[8:12]}-{c[12:16]}-{c[16:20]}-{c[20:]}"

    # ── 검색 (접근 가능한 페이지 목록) ─────────────────────────
    def search_pages(self, query: str = "") -> list[dict]:
        body = {"filter": {"value": "page", "property": "object"}}
        if query:
            body["query"] = query
        data = self._post("/search", body)
        return data.get("results", [])

    def search_databases(self, query: str = "") -> list[dict]:
        body = {"filter": {"value": "database", "property": "object"}}
        if query:
            body["query"] = query
        data = self._post("/search", body)
        return data.get("results", [])

    # ── 페이지 ─────────────────────────────────────────────────
    def get_page(self, page_id: str) -> dict:
        return self._get(f"/pages/{self._fmt_id(page_id)}")

    def extract_title(self, page: dict) -> str:
        for prop in page.get("properties", {}).values():
            if prop.get("type") == "title":
                return "".join(p.get("plain_text", "") for p in prop.get("title", []))
        # 타이틀 속성이 없는 경우 (child_page 등)
        return page.get("properties", {}).get("title", {}).get("plain_text", "Untitled")

    # ── 블록 (본문) ────────────────────────────────────────────
    def get_blocks(self, block_id: str, cursor: Optional[str] = None) -> dict:
        path = f"/blocks/{self._fmt_id(block_id)}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        return self._get(path)

    def parse_page(self, page_id: str) -> tuple[str, list[str]]:
        """
        페이지 전체 블록을 재귀적으로 파싱합니다.
        Returns:
            body_md    : 마크다운 본문
            image_urls : 이미지 URL 목록
        """
        return self._parse_blocks(page_id)

    def _rich_text(self, rt_list: list) -> str:
        return "".join(r.get("plain_text", "") for r in rt_list)

    def _parse_blocks(self, block_id: str, depth: int = 0) -> tuple[str, list[str]]:
        lines: list[str] = []
        image_urls: list[str] = []
        indent = "  " * depth
        cursor = None

        while True:
            data = self.get_blocks(block_id, cursor)

            for block in data.get("results", []):
                btype = block["type"]
                b     = block[btype]
                text  = self._rich_text(b.get("rich_text", []))

                if   btype == "paragraph":           lines.append(f"{indent}{text}")
                elif btype == "heading_1":           lines.append(f"# {text}")
                elif btype == "heading_2":           lines.append(f"## {text}")
                elif btype == "heading_3":           lines.append(f"### {text}")
                elif btype == "bulleted_list_item":  lines.append(f"{indent}- {text}")
                elif btype == "numbered_list_item":  lines.append(f"{indent}1. {text}")
                elif btype == "quote":               lines.append(f"> {text}")
                elif btype == "callout":
                    icon = b.get("icon", {})
                    em   = icon.get("emoji", "💡") if icon.get("type") == "emoji" else "💡"
                    lines.append(f"> {em} {text}")
                elif btype == "code":
                    lang = b.get("language", "")
                    lines.append(f"```{lang}\n{text}\n```")
                elif btype == "divider":             lines.append("---")
                elif btype == "to_do":
                    checked = "x" if b.get("checked") else " "
                    lines.append(f"{indent}- [{checked}] {text}")
                elif btype == "toggle":              lines.append(f"{indent}▶ {text}")
                elif btype == "image":
                    img_type = b.get("type")
                    url = b.get(img_type, {}).get("url", "") if img_type in ("file", "external") else ""
                    caption = self._rich_text(b.get("caption", []))
                    if url:
                        image_urls.append(url)
                        lines.append(f"![{caption}]({url})")
                elif btype == "file":
                    file_url = b.get("file", {}).get("url", "") or b.get("external", {}).get("url", "")
                    lines.append(f"[파일]({file_url})")
                elif btype == "video":
                    vid_url = b.get("file", {}).get("url", "") or b.get("external", {}).get("url", "")
                    lines.append(f"[동영상]({vid_url})")
                elif btype == "bookmark":
                    lines.append(f"[{b.get('url', '')}]({b.get('url', '')})")
                elif btype == "table_of_contents":
                    lines.append("*[목차]*")
                elif btype == "equation":
                    lines.append(f"$${b.get('expression', '')}$$")

                # 자식 블록 재귀
                if block.get("has_children"):
                    child_body, child_imgs = self._parse_blocks(block["id"], depth + 1)
                    if child_body.strip():
                        lines.append(child_body)
                    image_urls.extend(child_imgs)

            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")

        return "\n\n".join(ln for ln in lines if ln.strip()), image_urls

    # ── 데이터베이스 ───────────────────────────────────────────
    def query_database(self, db_id: str, filter_body: Optional[dict] = None) -> list[dict]:
        body = filter_body or {}
        data = self._post(f"/databases/{self._fmt_id(db_id)}/query", body)
        return data.get("results", [])


# ── 이미지 다운로드 ─────────────────────────────────────────────
def download_image(url: str, save_dir: Path) -> Optional[Path]:
    try:
        res = requests.get(url, timeout=30, stream=True)
        res.raise_for_status()
        content_type = res.headers.get("Content-Type", "image/jpeg")
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".jpg"
        ext = ext.replace(".jpe", ".jpg")
        stem = Path(url.split("?")[0].split("/")[-1]).stem or f"img_{int(time.time())}"
        path = save_dir / f"{stem}{ext}"
        with open(path, "wb") as f:
            for chunk in res.iter_content(8192):
                f.write(chunk)
        return path
    except Exception as e:
        print(f"  ⚠️  이미지 다운로드 실패: {e}")
        return None