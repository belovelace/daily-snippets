"""
스니펫 API 구조 확인
실행: python check_snippets.py
"""
import requests
import json
from dotenv import load_dotenv
load_dotenv()

SCHOOL_API_URL   = "https://api.1000.school"
SCHOOL_API_TOKEN = "44Gtdx9FB5KAe5a0m10Ecxgl0z_rckb22yi_YNdn18A"

headers = {
    "Authorization": f"Bearer {SCHOOL_API_TOKEN}",
    "Content-Type": "application/json"
}

# 1. 스니펫 목록 조회
print("📋 GET /daily-snippets")
r = requests.get(f"{SCHOOL_API_URL}/daily-snippets", headers=headers, timeout=10)
print(f"  Status: {r.status_code}")
if r.ok:
    data = r.json()
    print(f"  응답 구조: {json.dumps(data, ensure_ascii=False, indent=2)[:800]}")
else:
    print(f"  오류: {r.text[:300]}")

print()

# 2. 교수용 페이지 데이터
print("📋 GET /daily-snippets/professor/page-data")
r2 = requests.get(f"{SCHOOL_API_URL}/daily-snippets/professor/page-data", headers=headers, timeout=10)
print(f"  Status: {r2.status_code}")
if r2.ok:
    data2 = r2.json()
    print(f"  응답 구조: {json.dumps(data2, ensure_ascii=False, indent=2)[:800]}")
else:
    print(f"  오류: {r2.text[:300]}")