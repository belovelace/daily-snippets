"""
notion_api.py
─────────────
Notion REST API 직접 호출 헬퍼
"""

import requests
from config import NOTION_HEADERS, NOTION_DATABASE_ID


def notion_get(path: str) -> dict:
    r = requests.get(f"https://api.notion.com/v1{path}", headers=NOTION_HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def notion_post(path: str, body: dict) -> dict:
    r = requests.post(f"https://api.notion.com/v1{path}", headers=NOTION_HEADERS, json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def notion_patch(path: str, body: dict) -> dict:
    r = requests.patch(f"https://api.notion.com/v1{path}", headers=NOTION_HEADERS, json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def get_page(page_id: str) -> dict:
    return notion_get(f"/pages/{page_id}")


def get_page_title(page: dict) -> str:
    """Notion 페이지 제목 추출"""
    for prop_val in page.get("properties", {}).values():
        if prop_val.get("type") == "title":
            arr = prop_val.get("title", [])
            if arr:
                return arr[0].get("plain_text", "제목 없음")
    return "제목 없음"


def get_page_text(page_id: str) -> str:
    """Notion 페이지 블록에서 텍스트 추출"""
    data = notion_get(f"/blocks/{page_id}/children")
    text_parts = []
    for block in data.get("results", []):
        block_type = block.get("type")
        if block_type in ["paragraph", "heading_1", "heading_2", "heading_3",
                           "bulleted_list_item", "numbered_list_item", "quote", "callout"]:
            for rt in block.get(block_type, {}).get("rich_text", []):
                text_parts.append(rt.get("plain_text", ""))
    return "\n".join(text_parts).strip()


def get_all_block_ids(page_id: str) -> list:
    """페이지의 모든 블록 ID 목록 반환"""
    data = notion_get(f"/blocks/{page_id}/children")
    return [block["id"] for block in data.get("results", [])]


def delete_all_blocks(page_id: str):
    """페이지의 모든 블록 삭제 (원본 글 초기화)"""
    block_ids = get_all_block_ids(page_id)
    for block_id in block_ids:
        try:
            requests.delete(
                f"https://api.notion.com/v1/blocks/{block_id}",
                headers=NOTION_HEADERS,
                timeout=10
            )
        except Exception as e:
            print(f"  ⚠ 블록 삭제 실패 ({block_id}): {e}")


def append_blocks(page_id: str, blocks: list):
    """블록 목록을 페이지에 추가 (20개씩 분할)"""
    for i in range(0, len(blocks), 20):
        notion_patch(f"/blocks/{page_id}/children", {"children": blocks[i:i+20]})


def get_checked_pages(checkbox_prop: str = "피드백요청") -> list:
    """체크박스가 True인 페이지 목록 조회"""
    body = {
        "filter": {
            "property": checkbox_prop,
            "checkbox": {"equals": True}
        }
    }
    try:
        return notion_post(f"/databases/{NOTION_DATABASE_ID}/query", body).get("results", [])
    except Exception as e:
        print(f"  ⚠ Notion 쿼리 오류: {e}")
        return []


def uncheck_property(page_id: str, prop: str = "피드백요청"):
    """체크박스를 False로 되돌려 중복 실행 방지"""
    try:
        notion_patch(f"/pages/{page_id}", {"properties": {prop: {"checkbox": False}}})
    except Exception:
        pass