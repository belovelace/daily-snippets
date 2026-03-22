"""
agents/template.py
──────────────────
자유롭게 작성된 글을 데일리 스니펫 템플릿으로 자동 변환
원본 글 → 7개 섹션 구조로 재구성
"""

from config import ai_client, GEMINI_MODEL, TEMPLATE_SECTIONS


def convert_to_template(raw_text: str, question: str | None) -> dict:
    """
    자유 글을 템플릿 7개 섹션으로 변환.
    반환: { "01 · What": "...", "02 · Why": "...", ... }
    """
    question_note = f"\n\n참고: 이 글에는 다음 질문이 포함되어 있습니다 — \"{question}\"" if question else ""

    prompt = f"""아래 자유롭게 작성된 글을 데일리 스니펫 템플릿 형식으로 재구성하세요.{question_note}

원본 글:
{raw_text}

템플릿 섹션:
1. [01 · What] 무엇을 했나요?
2. [02 · Why] 왜 그 일을 했나요?
3. [03 · Value Add] 어떤 가치를 만들었나요?
4. [04 · Highlight ✨] 잘된 점
5. [05 · Lowlight] 아쉬웠던 점
6. [06 · Tomorrow] 내일 할 일
7. [07 · Health Check] 오늘 컨디션 (10점 만점)

규칙:
- 원본 글의 내용을 최대한 살려서 각 섹션에 배치하세요
- 원본에 없는 내용은 "(작성 필요)" 라고 채우세요
- 각 섹션 내용은 반드시 bullet point(•) 개조식으로 작성하세요
  예시: • 교수님 에이전트 AI API 연동 완료
        • 공감의 반경 독서 후 핵심 인사이트 도출
- 각 bullet은 간결하게 한 줄로 작성하세요 (1~4개 bullet)
- 반드시 아래 형식으로만 답하세요. 다른 말은 하지 마세요.

출력 형식 (이 형식 그대로):
###01 · What###
• 내용
• 내용

###02 · Why###
• 내용

###03 · Value Add###
• 내용

###04 · Highlight ✨###
• 내용

###05 · Lowlight###
• 내용

###06 · Tomorrow###
• 내용

###07 · Health Check###
• 내용"""

    try:
        response = ai_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return _parse_template_response(response.text)
    except Exception as e:
        print(f"  ⚠ 템플릿 변환 오류: {e}")
        return {t: "(변환 실패)" for t, _ in TEMPLATE_SECTIONS}


def _parse_template_response(text: str) -> dict:
    """AI 응답을 섹션별 딕셔너리로 파싱"""
    result = {}
    current_key = None
    current_lines = []

    for line in text.splitlines():
        if line.startswith("###") and line.endswith("###"):
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = line.strip("###").strip()
            current_lines = []
        elif current_key:
            current_lines.append(line)

    if current_key:
        result[current_key] = "\n".join(current_lines).strip()

    for t, _ in TEMPLATE_SECTIONS:
        if t not in result:
            result[t] = "(작성 필요)"

    return result


def build_template_blocks(sections: dict, question: str | None) -> list:
    """템플릿 섹션을 Notion 블록 리스트로 변환 (bullet 개조식)"""
    blocks = []

    for t, _ in TEMPLATE_SECTIONS:
        content = sections.get(t, "(작성 필요)")

        blocks.append({
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": t}}]}
        })

        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("•") or line.startswith("-"):
                blocks.append({
                    "object": "block", "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line.lstrip("•-").strip()}}]
                    }
                })
            else:
                blocks.append({
                    "object": "block", "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
                })

    # 질문 섹션 — 항상 마지막에 추가
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    blocks.append({
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "08 · Question 💬"}}]}
    })
    if question:
        blocks.append({
            "object": "block", "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": question}}],
                "icon": {"emoji": "💬"}
            }
        })
    else:
        blocks.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text",
                "text": {"content": "(질문 없음 — 피드백이 생성되지 않습니다)"},
                "annotations": {"color": "gray"}}]}
        })

    return blocks