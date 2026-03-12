# FTP DM Log Converter

FTP 서버의 DM 로그를 자동으로 PCAP으로 변환하는 웹 애플리케이션

## 주요 기능

- **FTP 서버 연결**: FTP 서버에 접속하여 디렉토리 탐색
- **자동 변환**: 선택한 디렉토리의 DM 로그 파일(HDF, SDM, QMDL)을 PCAP으로 변환
- **중복 방지**: 동일 이름의 PCAP 파일이 있으면 건너뛰기
- **실시간 진행 상황**: SSE를 통한 실시간 변환 진행 상황 표시

## 작동 방식

1. FTP 서버에 접속하여 디렉토리 탐색 후 원하는 디렉토리 선택
2. 선택한 디렉토리의 DM 로그 파일만 변환 (하위 디렉토리 미포함)
3. 동일 이름의 .pcap 파일이 있으면 건너뛰기
4. 변환 후 같은 위치에 파일명 동일하게 .pcap 파일 업로드

## 설치 및 실행

### 사전 요구사항

- Python 3.8+
- scat (DM 로그 변환 도구)

### 설치

```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 실행

```bash
python src/app.py
```

서버가 시작되면 브라우저에서 `http://localhost:9090`으로 접속하세요.

## 지원 파일 형식

- `.qmdl` - Qualcomm
- `.hdf` - Qualcomm
- `.dlf` - Qualcomm
- `.sdm` - Samsung

## 기술 스택

- **백엔드**: Flask 3.0.0
- **프론트엔드**: Vanilla JavaScript
- **외부 도구**: scat (DM 로그 → PCAP 변환)

## 프로젝트 구조

```
.
├── src/
│   ├── app.py           # Flask 웹 서버
│   ├── converter.py     # 변환 로직
│   └── ftp_handler.py   # FTP 연결 및 파일 처리
├── templates/
│   └── index.html       # 웹 UI
├── requirements.txt     # Python 의존성
└── README.md
```

## 라이선스

MIT License
