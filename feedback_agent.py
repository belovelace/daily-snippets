"""
6명 교수님 AI 피드백 에이전트 시스템
Notion 체크박스 감지 → 6명 동시 피드백 → Notion + 스니펫 사이트 저장

의존성: pip install openai requests
(notion-client 불필요 — Notion API를 requests로 직접 호출)
"""

import os
import time
import threading
import requests
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()  # .env 파일 로드

# ─────────────────────────────────────────
# 환경 설정
# ─────────────────────────────────────────
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

ai_client_genai = genai.Client(api_key=GOOGLE_API_KEY)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# ─────────────────────────────────────────
# Notion API 직접 호출 헬퍼 (notion_client 대체)
# ─────────────────────────────────────────

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

# ─────────────────────────────────────────
# 6명 교수님 페르소나 정의
# ─────────────────────────────────────────
PROFESSORS = [
    {
        "id": "jang_dae_ik",
        "name": "장대익 학장님",
        "title": "과학철학 · 인류학 · 진화론",
        "emoji": "🧬",
        "color": "#2D5A8E",
        "system_prompt": """당신은 장대익 학장님입니다.
전문 분야: 과학철학, 인류학, 진화론. '종의 기원' 한국어 초판 번역자.

피드백 스타일:
- 경청을 잘 하고, 학생이 이상하게 말해도 의도를 잘 파악해서 이해함
- 처음에는 끄덕끄덕 공감하듯 듣다가, 결론은 항상 비관적으로 마무리함. "그런데 결국..." 식으로 현실의 어두운 면을 짚음
- 반론을 매우 좋아함. 학생의 주장에 논리적 반론을 제기하며 더 깊이 생각하게 만듦
- 사회적 가치와 인류 전체에 미치는 영향을 중요하게 봄
- 진화론, 과학철학적 관점으로 아이디어를 해석함
- 논리적 허점은 반드시 짚되, 학생의 의도는 충분히 존중함

말투 예시: "음, 그렇군요. 그런데 결국...", "흥미로운 시도인데, 반론을 하나 드리자면...", "사회적 가치 측면에서 보면 이 부분이 걱정됩니다"

학생을 지칭할 때는 이름 대신 반드시 '학생'이라고 부르세요.
반드시 한국어로, 300자 내외로 피드백을 작성하세요."""
    },
    {
        "id": "choi_jae_hong",
        "name": "최재홍 교수님",
        "title": "정보통신",
        "emoji": "📡",
        "color": "#8B2252",
        "system_prompt": """당신은 최재홍 교수님입니다.
전문 분야: 정보통신.

피드백 스타일:
- 날카롭지만 유머가 넘침
- 고전 책의 명문장이나 거장들의 명대사를 자주 인용함 (출처 명시)
- 부족한 부분을 지적할 때 "이단 옆차기 날린다"고 표현함. 중요한 점은 이단 옆차기를 '학생에게' 날리는 것이 아니라, 교수님 본인이 '나(학생)에게' 날린다고 표현하는 것. 즉 "이단 옆차기 한 방 날립니다" 식으로 1인칭 시점으로 씀
- 본인 외모에 대한 자화자찬 유머를 가끔 씀 (예: "잘생긴 교수가 말하는데 안 들으면 손해죠")
- 정보통신 트렌드와 연결 지음

학생을 지칭할 때는 이름 대신 반드시 '학생'이라고 부르세요.
반드시 한국어로, 300자 내외로 피드백을 작성하세요."""
    },
    {
        "id": "hwang_sung_hyun",
        "name": "황성현 교수님",
        "title": "인사 및 조직",
        "emoji": "🏢",
        "color": "#1A6B3A",
        "system_prompt": """당신은 황성현 교수님입니다.
전문 분야: 인사 및 조직. 전 구글 직원, '가장 구글다운 사람'.

피드백 스타일:
- 해요체(~해요, ~이에요)를 절대 쓰지 않음. 반말이나 합쇼체(~합니다, ~입니다)만 사용
- 개그를 치기 전에 반드시 빌드업을 함. 진지하게 이야기를 쌓아가다가 마지막에 유머로 마무리
- 구글의 조직 문화, OKR, 데이터 기반 사고를 자주 언급함
- "구글에서는 이런 상황에서..." 식의 실제 경험을 공유함
- 가끔 연기처럼 과장된 감탄이나 반응을 보임
- 사람과 조직의 관점에서 아이디어의 실행 가능성을 봄

학생을 지칭할 때는 이름 대신 반드시 '학생'이라고 부르세요.
반드시 한국어로, 300자 내외로 피드백을 작성하세요."""
    },
    {
        "id": "kim_nam_joo",
        "name": "김남주 교수님",
        "title": "컴퓨터공학",
        "emoji": "💻",
        "color": "#5B2D8E",
        "system_prompt": """당신은 김남주 교수님입니다.
전문 분야: 컴퓨터공학.

피드백 스타일:
- 논리적이고 구조적으로 분석합니다
- '도발적인' 아이디어를 매우 좋아합니다 — 도발성이 있으면 크게 칭찬합니다
- 도발성이 부족하면 "좀 더 도발적으로 가져오세요"라고 직접 말합니다
- 기술적 실현 가능성을 중요하게 봅니다
- 아이디어의 혁신성과 파괴력을 평가합니다

학생을 지칭할 때는 이름 대신 반드시 '학생'이라고 부르세요.
반드시 한국어로, 300자 내외로 피드백을 작성하세요."""
    },
    {
        "id": "kim_ji_na",
        "name": "김지나 교수님",
        "title": "조경학 · 인류학 · 환경학",
        "emoji": "🌿",
        "color": "#4A7C59",
        "system_prompt": """당신은 김지나 교수님입니다.
전문 분야: 조경학, 인류학, 환경학. 말을 키우시고 승마가 취미.

피드백 스타일:
- 조용하고 조곤조곤 말씀하십니다
- '~요' 말투를 사용합니다 (예: "이 부분이 흥미롭네요", "좀 더 생각해보면 좋겠어요")
- 동물, 자연, 환경과 연결지어 생각합니다
- 경험의 중요성을 강조합니다 — "직접 경험해보셨나요?"
- 말이나 자연에서 비유를 가끔 가져옵니다

학생을 지칭할 때는 이름 대신 반드시 '학생'이라고 부르세요.
반드시 한국어로, 300자 내외로 피드백을 작성하세요."""
    },
    {
        "id": "lee_min_suk",
        "name": "이민석 교수님",
        "title": "인류학 · 진화학 · 심리학",
        "emoji": "🧠",
        "color": "#C4650A",
        "system_prompt": """당신은 이민석 교수님입니다.
전문 분야: 인류학, 진화학, 심리학. 교수님들 중 가장 어리십니다.

피드백 스타일:
- 따뜻하고 친근합니다
- '~하는' 말투를 자주 씁니다 (예: "이런 시도를 하는 게 중요하는", "생각을 발전시키는 것 같아서")
- 쪽지시험을 좋아하듯, 핵심 개념을 짚어주는 질문을 던집니다
- 심리학적, 인류학적 관점에서 인간 행동과 연결합니다
- 젊고 에너지 넘치는 톤으로 격려합니다

학생을 지칭할 때는 이름 대신 반드시 '학생'이라고 부르세요.
반드시 한국어로, 300자 내외로 피드백을 작성하세요."""
    }
]

# ─────────────────────────────────────────
# Notion 데이터 읽기
# ─────────────────────────────────────────

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


def get_page_title(page: dict) -> str:
    """Notion 페이지 제목 추출"""
    for prop_val in page.get("properties", {}).values():
        if prop_val.get("type") == "title":
            arr = prop_val.get("title", [])
            if arr:
                return arr[0].get("plain_text", "제목 없음")
    return "제목 없음"


def get_checked_pages() -> list:
    """피드백요청=True 인 페이지 조회 (중복 실행은 processed_ids로 방지)"""
    body = {
        "filter": {
            "property": "피드백요청",
            "checkbox": {"equals": True}
        }
    }
    try:
        return notion_post(f"/databases/{NOTION_DATABASE_ID}/query", body).get("results", [])
    except Exception as e:
        print(f"  ⚠ Notion 쿼리 오류: {e}")
        return []

# ─────────────────────────────────────────
# AI 피드백 생성
# ─────────────────────────────────────────

def generate_feedback(professor: dict, content: str, title: str) -> str:
    """단일 교수 에이전트 피드백 생성 (429 시 자동 재시도)"""
    import re
    prompt = f"""{professor["system_prompt"]}

---
제목: {title}

내용:
{content}

위 글에 교수님 스타일로 피드백해 주세요."""

    for attempt in range(3):  # 최대 3회 재시도
        try:
            response = ai_client_genai.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            err = str(e)
            # retry_delay 파싱해서 정확히 대기
            match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", err)
            wait = int(match.group(1)) + 5 if match else 60
            if "429" in err and attempt < 2:
                print(f"  [{professor['name']}] ⏳ 429 Rate Limit — {wait}초 대기 후 재시도...")
                time.sleep(wait)
            else:
                return f"피드백 생성 오류: {err[:100]}"
    return "피드백 생성 오류: 최대 재시도 횟수 초과"


def generate_all_feedbacks(content: str, title: str) -> list:
    """6명 병렬 피드백 생성 (Tier 1)"""
    results = [None] * len(PROFESSORS)

    def worker(idx, professor):
        print(f"  [{professor['name']}] 생성 중...")
        feedback = generate_feedback(professor, content, title)
        results[idx] = {
            "professor_id":    professor["id"],
            "professor_name":  professor["name"],
            "professor_title": professor["title"],
            "professor_emoji": professor["emoji"],
            "professor_color": professor["color"],
            "feedback":        feedback,
            "generated_at":    datetime.now().isoformat()
        }
        print(f"  [{professor['name']}] ✓ 완료")

    threads = [threading.Thread(target=worker, args=(i, p)) for i, p in enumerate(PROFESSORS)]
    for t in threads: t.start()
    for t in threads: t.join()
    return results

# ─────────────────────────────────────────
# 결과 저장
# ─────────────────────────────────────────

def save_feedback_to_notion(page_id: str, feedbacks: list):
    """피드백 블록을 Notion 페이지에 추가"""
    blocks = [
        {"object": "block", "type": "divider", "divider": {}},
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🎓 교수님 AI 피드백"}}]}},
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": [{"type": "text",
             "text": {"content": f"생성 일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}"},
             "annotations": {"color": "gray"}}]}}
    ]
    for fb in feedbacks:
        if not fb:
            continue
        blocks.append({"object": "block", "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {
                "content": f"{fb['professor_emoji']} {fb['professor_name']} — {fb['professor_title']}"}}]}})
        blocks.append({"object": "block", "type": "quote",
            "quote": {"rich_text": [{"type": "text", "text": {"content": fb["feedback"]}}]}})

    for i in range(0, len(blocks), 20):
        notion_patch(f"/blocks/{page_id}/children", {"children": blocks[i:i+20]})
    print("  ✓ Notion 저장 완료")


def get_snippet_id_by_content(page_content: str) -> int | None:
    """content 텍스트로 스니펫 id 조회 (앞 30자 매칭)"""
    headers = {"Authorization": f"Bearer {SCHOOL_API_TOKEN}"}
    try:
        r = requests.get(f"{SCHOOL_API_URL}/daily-snippets", headers=headers, timeout=10)
        r.raise_for_status()
        items = r.json().get("items", [])
        # content 앞 30자로 매칭
        keyword = page_content.strip()[:30]
        for item in items:
            snippet_content = (item.get("content") or "").strip()[:30]
            if keyword and keyword == snippet_content:
                return item["id"]
        # 매칭 실패 시 가장 최근 스니펫 id 반환
        if items:
            print(f"  ⚠ content 매칭 실패 — 가장 최근 스니펫(id: {items[0]['id']}) 사용")
            return items[0]["id"]
        return None
    except Exception as e:
        print(f"  ⚠ 스니펫 목록 조회 실패: {e}")
        return None


def save_feedback_to_snippet(page_id: str, feedbacks: list, title: str, content: str):
    """PUT /daily-snippets/{id} 로 피드백 저장"""
    headers = {"Authorization": f"Bearer {SCHOOL_API_TOKEN}", "Content-Type": "application/json"}

    # 오늘 날짜로 스니펫 id 조회
    snippet_id = get_snippet_id_by_content(content)

    if snippet_id is None:
        print("  ⚠ 스니펫 저장 실패 — 해당 날짜 스니펫 없음")
        return None

    # 6명 피드백을 하나의 텍스트로 합치기
    feedback_text = f"🎓 교수님 AI 피드백 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    for fb in feedbacks:
        if fb:
            feedback_text += f"{fb['professor_emoji']} {fb['professor_name']}\n{fb['feedback']}\n\n"

    # 기존 스니펫 content 조회 (PUT에 content 필드 필수)
    existing_content = content  # fallback
    try:
        r_get = requests.get(f"{SCHOOL_API_URL}/daily-snippets/{snippet_id}", headers=headers, timeout=10)
        if r_get.ok:
            existing_content = r_get.json().get("content", content)
    except Exception:
        pass

    payload = {"content": existing_content, "feedback": feedback_text}

    try:
        r = requests.put(
            f"{SCHOOL_API_URL}/daily-snippets/{snippet_id}",
            headers=headers, json=payload, timeout=15
        )
        r.raise_for_status()
        print(f"  ✓ 스니펫 피드백 저장 완료 (id: {snippet_id})")
        return r.json()
    except Exception as e:
        print(f"  ⚠ PUT /daily-snippets/{snippet_id} 실패: {e} — {r.text[:200] if 'r' in dir() else ''}")
        return None


def mark_feedback_done(page_id: str):
    """피드백 완료 후 피드백요청 체크박스를 False로 되돌려 중복 실행 방지"""
    try:
        notion_patch(f"/pages/{page_id}", {"properties": {"피드백요청": {"checkbox": False}}})
    except Exception:
        pass

# ─────────────────────────────────────────
# 메인 처리 흐름
# ─────────────────────────────────────────

def process_page(page: dict):
    page_id = page["id"]
    title   = get_page_title(page)
    print(f"\n{'='*50}\n📄 처리 중: {title}\n{'='*50}")

    content = get_page_text(page_id)
    if not content:
        print("  ⚠ 내용 없음, 스킵")
        return

    print(f"  글자 수: {len(content)}자")
    print(f"\n  🤖 6명 교수님 피드백 생성 중 (병렬)...")
    feedbacks = generate_all_feedbacks(content, title)

    print(f"\n  💾 Notion에 저장 중...")
    save_feedback_to_notion(page_id, feedbacks)
    print(f"\n  ✅ '{title}' 완료!")


def run_polling(interval_seconds: int = 30):
    """폴링 루프 — interval_seconds 마다 체크박스 확인"""
    print(f"🚀 피드백 에이전트 시작 (주기: {interval_seconds}초)")
    processed_ids = set()
    while True:
        try:
            for page in get_checked_pages():
                pid = page["id"]
                if pid not in processed_ids:
                    process_page(page)
                    processed_ids.add(pid)
                    mark_feedback_done(pid)
        except KeyboardInterrupt:
            print("\n👋 종료")
            break
        except Exception as e:
            print(f"\n⚠ 오류: {e}")
        time.sleep(interval_seconds)


def test_with_page_id(page_id: str):
    """특정 페이지 ID로 즉시 테스트"""
    page = notion_get(f"/pages/{page_id}")
    process_page(page)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_with_page_id(sys.argv[1])
    else:
        run_polling(interval_seconds=30)