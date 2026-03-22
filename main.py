# -*- coding: utf-8 -*-
"""
main.py
-------
진입점 -- Notion DB 폴링 루프

질문 없음 -> 6명 각자 피드백 (토글)
질문 있음 -> 6명 각자 피드백 (토글) + 3라운드 토론 요약 + 결론
"""

import sys
import os
import time
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from notion_api import (
    get_page, get_page_title, get_page_text,
    delete_all_blocks, append_blocks,
    get_checked_pages, uncheck_property
)
from agents.question import detect_question
from agents.template import convert_to_template, build_template_blocks
from agents.feedback import (
    generate_all_feedbacks, build_feedback_blocks,
    run_debate, build_debate_blocks
)


def process_page(page: dict):
    page_id = page["id"]
    title   = get_page_title(page)
    print(f"\n{'='*50}\n[처리중] {title}\n{'='*50}")

    raw_text = get_page_text(page_id)
    if not raw_text.strip():
        print("  [경고] 내용 없음, 스킵")
        return

    print(f"  글자 수: {len(raw_text)}자")

    # 1. 질문 감지
    print("  [1] 질문 감지 중...")
    question = detect_question(raw_text)
    if question:
        print(f"  [질문 발견] {question[:60]}...")
    else:
        print("  -- 질문 없음 -> 개인 피드백 모드")

    # 2. 템플릿 변환
    print("  [2] 템플릿 변환 중...")
    sections = convert_to_template(raw_text, question)

    # 3. 원본 삭제 후 템플릿 작성
    print("  [3] 원본 블록 삭제 중...")
    delete_all_blocks(page_id)
    template_blocks = build_template_blocks(sections, question)
    append_blocks(page_id, template_blocks)
    print("  [OK] 템플릿 작성 완료")

    # 4. 피드백 생성 (질문 유무로 분기)
    print("\n  [4] 6명 교수님 피드백 생성 중 (병렬)...")
    feedbacks = generate_all_feedbacks(question, raw_text)
    feedback_blocks = build_feedback_blocks(feedbacks)
    append_blocks(page_id, feedback_blocks)
    print("  [OK] 피드백 저장 완료")

    # 5. 질문 있으면 토론 추가 실행
    if question:
        print("\n  [5] 3라운드 토론 시작...")
        debate = run_debate(question, raw_text)
        debate_blocks = build_debate_blocks(question, debate)
        append_blocks(page_id, debate_blocks)
        print("  [OK] 토론 결과 저장 완료")

    print(f"\n  [완료] '{title}' 처리 완료!")


def run_polling(interval: int = 30):
    print(f"[시작] 피드백 에이전트 (폴링 주기: {interval}초)")
    processed_ids = set()

    while True:
        try:
            for page in get_checked_pages():
                pid = page["id"]
                if pid not in processed_ids:
                    process_page(page)
                    processed_ids.add(pid)
                    uncheck_property(pid, "피드백요청")
        except KeyboardInterrupt:
            print("\n[종료]")
            break
        except Exception as e:
            print(f"\n[오류] {e}")
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="노션 피드백 에이전트")
    parser.add_argument("--interval", type=int, default=30, help="폴링 주기(초)")
    parser.add_argument("--once", type=str, metavar="PAGE_ID", help="단일 페이지 즉시 처리")
    args = parser.parse_args()

    if args.once:
        page = get_page(args.once)
        process_page(page)
    else:
        run_polling(args.interval)