"""
MAF 핸즈온 워크샵용 진입점
기존 프로젝트의 main.py를 MAF용 app.py로 연결
"""
import os

from dotenv import load_dotenv

# Azure 환경 감지
RUNNING_ON_AZURE = os.getenv("WEBSITE_HOSTNAME") is not None or os.getenv("RUNNING_IN_PRODUCTION") is not None

if not RUNNING_ON_AZURE:
    load_dotenv()

# MAF 핸즈온용 app 사용
from app import app
