"""
agents/question.py
──────────────────
자유 글에서 질문 감지
질문이 있어야 교수님 피드백이 생성됨
"""

import re
from config import QUESTION_KEYWORDS, ai_client, GEMINI_MODEL


def detect_question(text: str) -> str | None:
    """
    텍스트에서 질문 추출.
    - 'Q.', 'q.', '질문:' 키워드로 시작하는 문장 우선 감지
    - 없으면 AI로 질문 여부 판단
    반환: 질문 문자열 or None (질문 없음)
    """
    # 1. 키워드 기반 감지
    for line in text.splitlines():
        line = line.strip()
        for kw in QUESTION_KEYWORDS:
            if line.startswith(kw):
                question = line[len(kw):].strip()
                if question:
                    return question
                # 키워드만 있고 내용이 다음 줄에 있을 수 있음
                return line

    # 2. '?' 포함 문장 감지
    sentences = re.split(r'[.。\n]', text)
    for s in sentences:
        if '?' in s and len(s.strip()) > 5:
            return s.strip()

    # 3. AI로 질문 의도 판단 (위 방법으로 못 찾은 경우)
    prompt = f"""아래 글에 교수님께 피드백을 요청하는 질문이 있는지 판단하세요.

글:
{text}

질문이 명확히 있으면 그 질문을 그대로 추출해서 반환하세요.
질문이 없으면 정확히 "없음" 이라고만 답하세요.
다른 말은 하지 마세요."""

    try:
        response = ai_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        result = response.text.strip()
        return None if result == "없음" else result
    except Exception as e:
        print(f"  ⚠ 질문 감지 오류: {e}")
        return None