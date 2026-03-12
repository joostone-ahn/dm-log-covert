FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 및 빌드 도구 설치
RUN apt-get update && apt-get install -y \
    tshark \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# scat 설치 (pip)
RUN pip install --no-cache-dir "signalcat[fastcrc]"

# 애플리케이션 파일 복사
COPY src/ ./src/
COPY templates/ ./templates/

# 포트 노출
EXPOSE 9090

# 애플리케이션 실행
CMD ["python", "src/app.py"]
