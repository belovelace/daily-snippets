"""
Notion DB 속성명 확인 스크립트
실행: python check_notion_db.py
"""
import requests

NOTION_ACCESS_TOKEN = "ntn_e30437794997CBnSymhC9mx7QSOUvmrWnq5u2AJrjT0fmq"
NOTION_DATABASE_ID  = "3270b56c-63ab-8039-8288-da19d277ec80"

headers = {
    "Authorization": f"Bearer {NOTION_ACCESS_TOKEN}",
    "Notion-Version": "2022-06-28",
}

# DB 속성 목록 조회
r = requests.get(
    f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}",
    headers=headers
)
print(f"Status: {r.status_code}")
if r.ok:
    db = r.json()
    print(f"\n📋 DB 이름: {db.get('title', [{}])[0].get('plain_text', '?')}\n")
    print("📌 속성 목록:")
    for name, prop in db.get("properties", {}).items():
        print(f"  - '{name}' ({prop['type']})")
else:
    print(r.text)