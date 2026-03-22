"""
config.py
─────────
환경변수 로드 및 공통 설정
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

# ── 환경변수 ────────────────────────────────────────────────────
NOTION_ACCESS_TOKEN = os.getenv("NOTION_ACCESS_TOKEN")
NOTION_DATABASE_ID  = os.getenv("NOTION_DATABASE_ID")
SCHOOL_API_URL      = os.getenv("SCHOOL_API_URL", "https://api.1000.school")
SCHOOL_API_TOKEN    = os.getenv("SCHOOL_API_TOKEN")
GOOGLE_API_KEY      = os.getenv("GOOGLE_API_KEY")

# 필수 환경변수 누락 시 조기 종료
_required = {
    "NOTION_ACCESS_TOKEN": NOTION_ACCESS_TOKEN,
    "NOTION_DATABASE_ID":  NOTION_DATABASE_ID,
    "SCHOOL_API_TOKEN":    SCHOOL_API_TOKEN,
    "GOOGLE_API_KEY":      GOOGLE_API_KEY,
}
_missing = [k for k, v in _required.items() if not v]
if _missing:
    raise EnvironmentError(f"❌ .env에 다음 변수가 없습니다: {', '.join(_missing)}")

# ── AI 클라이언트 ────────────────────────────────────────────────
ai_client = genai.Client(api_key=GOOGLE_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

# ── Notion API 헤더 ──────────────────────────────────────────────
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# ── 템플릿 섹션 정의 ─────────────────────────────────────────────
TEMPLATE_SECTIONS = [
    ("01 · What",        "무엇을 했나요?"),
    ("02 · Why",         "왜 그 일을 했나요?"),
    ("03 · Value Add",   "어떤 가치를 만들었나요?"),
    ("04 · Highlight ✨", "잘된 점"),
    ("05 · Lowlight",    "아쉬웠던 점"),
    ("06 · Tomorrow",    "내일 할 일"),
    ("07 · Health Check","(10점 만점)"),
]

# ── 질문 감지 키워드 ─────────────────────────────────────────────
QUESTION_KEYWORDS = ["Q.", "q.", "질문:", "질문 :", "?"]