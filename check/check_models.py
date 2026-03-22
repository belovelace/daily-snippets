"""
현재 사용 가능한 Gemini 모델 목록 확인
실행: python check_models.py
"""
import google.generativeai as genai
from dotenv import load_dotenv
import os
load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("📋 사용 가능한 모델 목록:\n")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"  ✅ {m.name}")