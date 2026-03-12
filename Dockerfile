FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    tshark \
    wget \
    && rm -rf /var/lib/apt/lists/*

# scat 설치
RUN wget https://github.com/fgsect/scat/releases/latest/download/scat -O /usr/local/bin/scat \
    && chmod +x /usr/local/bin/scat

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY src/ ./src/
COPY templates/ ./templates/

# 포트 노출
EXPOSE 9090

# 애플리케이션 실행
CMD ["python", "src/app.py"]
