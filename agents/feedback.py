# -*- coding: utf-8 -*-
"""
agents/feedback.py
------------------
질문 없음 -> 6명 각자 피드백 (병렬)
질문 있음 -> 6명 각자 피드백 + 3라운드 토론 요약 + 결론
"""

import re
import time
import threading
from datetime import datetime
from config import ai_client, GEMINI_MODEL

PROFESSORS = [
    {
        "id": "jang_dae_ik",
        "name": "장대익 학장님",
        "title": "과학철학 · 인류학 · 진화론",
        "emoji": "🧬",
        "system_prompt": """당신은 장대익 학장님입니다.
전문 분야: 과학철학, 인류학, 진화론. '종의 기원' 한국어 초판 번역자.
- 경청을 잘 하고, 학생이 이상하게 말해도 의도를 잘 파악해서 이해함
- 처음에는 끄덕끄덕 공감하듯 듣다가, 결론은 항상 비관적으로 마무리함. "그런데 결국..." 식으로 현실의 어두운 면을 짚음
- 반론을 매우 좋아함. 학생의 주장에 논리적 반론을 제기하며 더 깊이 생각하게 만듦
- 사회적 가치와 인류 전체에 미치는 영향을 중요하게 봄
- 진화론, 과학철학적 관점으로 아이디어를 해석함
말투: "음, 그렇군요. 그런데 결국...", "흥미로운 시도인데, 반론을 하나 드리자면..."
학생을 지칭할 때는 반드시 '학생'이라고 부르세요. 반드시 한국어로 답하세요."""
    },
    {
        "id": "choi_jae_hong",
        "name": "최재홍 교수님",
        "title": "정보통신",
        "emoji": "📡",
        "system_prompt": """당신은 최재홍 교수님입니다.
전문 분야: 정보통신.
- 날카롭지만 유머가 넘침
- 고전 책의 명문장이나 거장들의 명대사를 자주 인용함 (출처 명시)
- 부족한 부분을 지적할 때 교수님 본인이 '나(학생)에게' 이단 옆차기를 날린다고 1인칭으로 표현함
- 본인 외모에 대한 자화자찬 유머를 가끔 씀
- 정보통신 트렌드와 연결 지음
학생을 지칭할 때는 반드시 '학생'이라고 부르세요. 반드시 한국어로 답하세요."""
    },
    {
        "id": "hwang_sung_hyun",
        "name": "황성현 교수님",
        "title": "인사 및 조직",
        "emoji": "🏢",
        "system_prompt": """당신은 황성현 교수님입니다.
전문 분야: 인사 및 조직. 전 구글 직원, '가장 구글다운 사람'.
- 해요체(~해요, ~이에요)를 절대 쓰지 않음. 합쇼체(~합니다)만 사용
- 개그를 치기 전에 반드시 빌드업을 함. 진지하게 쌓아가다 마지막에 유머로 마무리
- 구글 조직 문화, OKR, 데이터 기반 사고를 자주 언급함
- "구글에서는 이런 상황에서..." 식의 경험을 공유함
학생을 지칭할 때는 반드시 '학생'이라고 부르세요. 반드시 한국어로 답하세요."""
    },
    {
        "id": "kim_nam_joo",
        "name": "김남주 교수님",
        "title": "컴퓨터공학",
        "emoji": "💻",
        "system_prompt": """당신은 김남주 교수님입니다.
전문 분야: 컴퓨터공학.
- 논리적이고 구조적으로 분석함
- '도발적인' 아이디어를 매우 좋아함. 도발성이 있으면 크게 칭찬하고, 없으면 "좀 더 도발적으로 가져오세요"라고 직접 말함
- 기술적 실현 가능성과 아이디어의 혁신성을 평가함
학생을 지칭할 때는 반드시 '학생'이라고 부르세요. 반드시 한국어로 답하세요."""
    },
    {
        "id": "kim_ji_na",
        "name": "김지나 교수님",
        "title": "조경학 · 인류학 · 환경학",
        "emoji": "🌿",
        "system_prompt": """당신은 김지나 교수님입니다.
전문 분야: 조경학, 인류학, 환경학. 말을 키우시고 승마가 취미.
- 조용하고 조곤조곤 말씀하심
- '~요' 말투를 사용함 (예: "흥미롭네요", "생각해보면 좋겠어요")
- 동물, 자연, 환경과 연결지어 생각함
- 경험의 중요성을 강조함. "직접 경험해보셨나요?"
학생을 지칭할 때는 반드시 '학생'이라고 부르세요. 반드시 한국어로 답하세요."""
    },
    {
        "id": "lee_min_suk",
        "name": "이민석 교수님",
        "title": "인류학 · 진화학 · 심리학",
        "emoji": "🧠",
        "system_prompt": """당신은 이민석 교수님입니다.
전문 분야: 인류학, 진화학, 심리학. 교수님들 중 가장 어리심.
- 따뜻하고 친근함
- '~하는' 말투를 자주 씀 (예: "이런 시도를 하는 게 중요하는")
- 쪽지시험처럼 핵심 개념을 짚어주는 질문을 던짐
- 심리학적, 인류학적 관점에서 인간 행동과 연결함
학생을 지칭할 때는 반드시 '학생'이라고 부르세요. 반드시 한국어로 답하세요."""
    }
]


def _call_ai(prompt: str, label: str = "") -> str:
    for attempt in range(3):
        try:
            response = ai_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            err = str(e)
            match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", err)
            wait = int(match.group(1)) + 5 if match else 60
            if "429" in err and attempt < 2:
                print(f"  [{label}] 429 -- {wait}초 대기 후 재시도...")
                time.sleep(wait)
            else:
                return f"오류: {err[:100]}"
    return "오류: 최대 재시도 횟수 초과"


# ── 6명 개인 피드백 (병렬) ───────────────────────────────────────

def _generate_single_feedback(professor: dict, context: str, question: str | None) -> str:
    if question:
        prompt = f"""{professor["system_prompt"]}

---
학생의 질문:
{question}

학생의 오늘 활동 맥락:
{context}

질문에 대해 교수님 스타일로 200자 내외로 답변해 주세요."""
    else:
        prompt = f"""{professor["system_prompt"]}

---
학생의 오늘 활동 기록:
{context}

위 내용에 대해 교수님 스타일로 200자 내외로 피드백해 주세요."""
    return _call_ai(prompt, professor["name"])


def generate_all_feedbacks(question: str | None, raw_text: str) -> list:
    """6명 병렬 피드백 생성"""
    results = [None] * len(PROFESSORS)

    def worker(idx, professor):
        print(f"  [{professor['name']}] 피드백 생성 중...")
        feedback = _generate_single_feedback(professor, raw_text, question)
        results[idx] = {
            "professor_id":    professor["id"],
            "professor_name":  professor["name"],
            "professor_title": professor["title"],
            "professor_emoji": professor["emoji"],
            "feedback":        feedback,
        }
        print(f"  [{professor['name']}] 완료")

    threads = [threading.Thread(target=worker, args=(i, p)) for i, p in enumerate(PROFESSORS)]
    for t in threads: t.start()
    for t in threads: t.join()
    return results


# ── 3라운드 토론 ─────────────────────────────────────────────────

def _run_debate_round(round_num: int, question: str, context: str,
                      previous: dict) -> dict:
    results = {}
    lock = threading.Lock()

    instructions = {
        1: "이 질문에 대한 첫 번째 의견을 150자 내외로 말씀해 주세요.",
        2: "다른 교수님들의 의견을 보고 반박 또는 동의 의견을 150자 내외로 말씀해 주세요. 누구의 의견인지 명시하세요.",
        3: "지금까지의 토론을 바탕으로 최종 마무리 발언을 100자 내외로 해주세요."
    }

    def worker(professor):
        prev_text = ""
        if previous:
            prev_text = "\n\n[다른 교수님들의 의견]\n"
            for name, opinion in previous.items():
                if name != professor["name"]:
                    prev_text += f"{name}: {opinion}\n"

        prompt = f"""{professor["system_prompt"]}

---
토론 주제 (학생의 질문): {question}
학생의 활동 맥락: {context}
{prev_text}
[{round_num}라운드] {instructions[round_num]}"""

        opinion = _call_ai(prompt, professor["name"])
        with lock:
            results[professor["name"]] = opinion
        print(f"  [{professor['name']}] R{round_num} 완료")

    threads = [threading.Thread(target=worker, args=(p,)) for p in PROFESSORS]
    for t in threads: t.start()
    for t in threads: t.join()
    return results


def _generate_debate_summary(question: str, all_rounds: list) -> tuple[str, str]:
    """토론 전체를 요약 + 결론으로 압축"""
    debate_text = f"토론 주제: {question}\n\n"
    for i, opinions in enumerate(all_rounds, 1):
        debate_text += f"=== {i}라운드 ===\n"
        for name, opinion in opinions.items():
            debate_text += f"[{name}]: {opinion}\n\n"

    prompt = f"""아래 교수님들의 토론 내용을 읽고 요약해 주세요.

{debate_text}

반드시 아래 형식으로만 답하세요:
###요약###
[교수님 이름]: 핵심 주장 한 줄
[교수님 이름]: 핵심 주장 한 줄
[교수님 이름]: 핵심 주장 한 줄
[교수님 이름]: 핵심 주장 한 줄
[교수님 이름]: 핵심 주장 한 줄
[교수님 이름]: 핵심 주장 한 줄

###결론###
토론 전체를 아우르는 결론 2~3문장"""

    raw = _call_ai(prompt)
    summary, conclusion = "", ""
    if "###결론###" in raw:
        parts = raw.split("###결론###")
        summary = parts[0].replace("###요약###", "").strip()
        conclusion = parts[1].strip()
    else:
        summary = raw.replace("###요약###", "").strip()
    return summary, conclusion


def run_debate(question: str, context: str) -> dict:
    """3라운드 토론 실행"""
    print(f"\n  [토론] 주제: {question[:50]}...")
    all_rounds = []
    previous = {}

    for r in range(1, 4):
        label = ["첫 발언", "반박", "마무리"][r-1]
        print(f"\n  -- R{r} {label} --")
        opinions = _run_debate_round(r, question, context, previous)
        all_rounds.append(opinions)
        previous = opinions

    print("\n  [요약] 토론 요약 생성 중...")
    summary, conclusion = _generate_debate_summary(question, all_rounds)
    return {"rounds": all_rounds, "summary": summary, "conclusion": conclusion}


# ── Notion 블록 빌더 ─────────────────────────────────────────────

def _toggle_block(title: str, children: list) -> dict:
    """토글 블록 생성"""
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": title}}],
            "children": children
        }
    }


def _paragraph(text: str, color: str = "default") -> dict:
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text",
            "text": {"content": text},
            "annotations": {"color": color}}]}
    }


def _heading2(text: str) -> dict:
    return {
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}
    }


def _bullet(text: str) -> dict:
    return {
        "object": "block", "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}
    }


def build_feedback_blocks(feedbacks: list) -> list:
    """
    노션용: 각 교수님 피드백을 토글로 작성
    """
    blocks = [
        {"object": "block", "type": "divider", "divider": {}},
        _heading2("🎓 교수님 피드백"),
        _paragraph(f"생성 일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}", "gray"),
    ]

    for fb in feedbacks:
        if not fb:
            continue
        toggle_title = f"{fb['professor_emoji']} {fb['professor_name']} — {fb['professor_title']}"
        blocks.append(_toggle_block(toggle_title, [_paragraph(fb["feedback"])]))

    return blocks


def build_debate_blocks(question: str, debate: dict) -> list:
    """
    노션용: 각 교수님 피드백(토글) + 핵심 발언 요약 + 결론
    토론 상세 내용은 토글 안에 숨김
    """
    blocks = [
        {"object": "block", "type": "divider", "divider": {}},
        _heading2("🗣 교수님 토론"),
        _paragraph(f"생성 일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')} · 3라운드 토론", "gray"),
        {
            "object": "block", "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"💬 {question}"}}],
                "icon": {"emoji": "💬"}
            }
        },
        {"object": "block", "type": "divider", "divider": {}},
    ]

    # 각 교수님 토글 (3라운드 발언 모두 포함)
    for prof in PROFESSORS:
        round_children = []
        labels = ["1라운드 · 첫 발언", "2라운드 · 반박", "3라운드 · 마무리"]
        for label, opinions in zip(labels, debate["rounds"]):
            opinion = opinions.get(prof["name"], "")
            if opinion:
                round_children.append(_paragraph(f"[{label}]", "gray"))
                round_children.append(_paragraph(opinion))

        toggle_title = f"{prof['emoji']} {prof['name']} — {prof['title']}"
        blocks.append(_toggle_block(toggle_title, round_children))

    # 핵심 발언 요약
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    blocks.append(_heading2("📌 핵심 발언 요약"))
    for line in debate["summary"].splitlines():
        line = line.strip()
        if line:
            blocks.append(_bullet(line))

    # 결론
    if debate["conclusion"]:
        blocks.append({"object": "block", "type": "divider", "divider": {}})
        blocks.append(_heading2("🏁 결론"))
        blocks.append(_paragraph(debate["conclusion"]))

    return blocks


# ── 마크다운 변환 (스니펫 사이트용) ─────────────────────────────

def feedbacks_to_markdown(feedbacks: list, question: str | None,
                          debate: dict | None = None) -> str:
    """스니펫 사이트 content 필드용 마크다운 생성"""
    lines = []
    lines.append("---")
    lines.append("## 🎓 교수님 피드백")
    lines.append("")

    for fb in feedbacks:
        if not fb:
            continue
        lines.append(f"### {fb['professor_emoji']} {fb['professor_name']}")
        lines.append(fb["feedback"])
        lines.append("")

    if question and debate:
        lines.append("---")
        lines.append("## 📌 핵심 발언 요약")
        lines.append("")
        for line in debate["summary"].splitlines():
            if line.strip():
                lines.append(f"- {line.strip()}")
        lines.append("")
        if debate["conclusion"]:
            lines.append("---")
            lines.append("## 🏁 결론")
            lines.append(debate["conclusion"])

    return "\n".join(lines)