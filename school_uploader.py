"""
school_uploader.py
──────────────────
1000.school API 연동 모듈
API 문서: https://api.1000.school/docs

엔드포인트 (daily-snippets):
  GET    /daily-snippets                    → 목록 조회
  GET    /daily-snippets/page-data          → 페이지 데이터 조회
  GET    /daily-snippets/professor/page-data→ 교수용 페이지 데이터 조회
  GET    /daily-snippets/{snippet_id}       → 단건 조회
  POST   /daily-snippets                    → 생성
  PUT    /daily-snippets/{snippet_id}       → 수정
  DELETE /daily-snippets/{snippet_id}       → 삭제
  POST   /daily-snippets/organize           → 정렬

인증: Authorization: Bearer <token>
"""

import requests
from typing import Optional


class SchoolUploader:
    BASE = "https://api.1000.school"

    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ── 조회 ────────────────────────────────────────────────────

    def list_snippets(self) -> dict:
        """GET /daily-snippets — 전체 목록 조회"""
        res = requests.get(
            f"{self.BASE}/daily-snippets",
            headers=self.headers,
            timeout=20,
        )
        res.raise_for_status()
        return res.json()

    def get_snippet(self, snippet_id: str) -> dict:
        """GET /daily-snippets/{snippet_id} — 단건 조회"""
        res = requests.get(
            f"{self.BASE}/daily-snippets/{snippet_id}",
            headers=self.headers,
            timeout=20,
        )
        res.raise_for_status()
        return res.json()

    def get_page_data(self) -> dict:
        """GET /daily-snippets/page-data — 페이지 데이터 조회"""
        res = requests.get(
            f"{self.BASE}/daily-snippets/page-data",
            headers=self.headers,
            timeout=20,
        )
        res.raise_for_status()
        return res.json()

    def get_professor_page_data(self) -> dict:
        """GET /daily-snippets/professor/page-data — 교수용 페이지 데이터 조회"""
        res = requests.get(
            f"{self.BASE}/daily-snippets/professor/page-data",
            headers=self.headers,
            timeout=20,
        )
        res.raise_for_status()
        return res.json()

    # ── 생성 ────────────────────────────────────────────────────

    def create_snippet(self, title: str, content: str, extra: Optional[dict] = None) -> dict:
        """POST /daily-snippets — 새 스니펫 생성 (노션 페이지 업로드)"""
        payload = {
            "title":   title,
            "content": content,
            **(extra or {}),
        }
        res = requests.post(
            f"{self.BASE}/daily-snippets",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        res.raise_for_status()
        return res.json()

    # ── 수정 ────────────────────────────────────────────────────

    def update_snippet(self, snippet_id: str, title: str, content: str,
                       extra: Optional[dict] = None) -> dict:
        """PUT /daily-snippets/{snippet_id} — 스니펫 수정"""
        payload = {
            "title":   title,
            "content": content,
            **(extra or {}),
        }
        res = requests.put(
            f"{self.BASE}/daily-snippets/{snippet_id}",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        res.raise_for_status()
        return res.json()

    # ── 삭제 ────────────────────────────────────────────────────

    def delete_snippet(self, snippet_id: str) -> dict:
        """DELETE /daily-snippets/{snippet_id} — 스니펫 삭제"""
        res = requests.delete(
            f"{self.BASE}/daily-snippets/{snippet_id}",
            headers=self.headers,
            timeout=20,
        )
        res.raise_for_status()
        return res.json()

    # ── 정렬 ────────────────────────────────────────────────────

    def organize_snippets(self, order: list[str]) -> dict:
        """POST /daily-snippets/organize — 스니펫 순서 정렬"""
        res = requests.post(
            f"{self.BASE}/daily-snippets/organize",
            headers=self.headers,
            json={"order": order},
            timeout=20,
        )
        res.raise_for_status()
        return res.json()