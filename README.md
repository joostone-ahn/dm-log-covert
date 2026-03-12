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

### 방법 1: Docker 사용 (권장)

Docker를 사용하면 scat과 tshark가 자동으로 설치되어 별도의 설정 없이 바로 사용할 수 있습니다.

```bash
# GitHub Container Registry에서 이미지 다운로드
docker pull ghcr.io/joostone-ahn/dm-log-covert:latest

# 컨테이너 실행
docker run -d -p 9090:9090 ghcr.io/joostone-ahn/dm-log-covert:latest
```

또는 docker-compose 사용:

```bash
# 저장소 클론
git clone https://github.com/joostone-ahn/dm-log-covert.git
cd dm-log-covert

# Docker Compose로 실행
docker-compose up -d
```

서버가 시작되면 브라우저에서 `http://localhost:9090`으로 접속하세요.

### 방법 2: 로컬 실행

#### 사전 요구사항

- Python 3.8+
- scat (DM 로그 변환 도구) - [설치 가이드](https://github.com/fgsect/scat)
- tshark (Wireshark CLI)

#### 설치

```bash
# 저장소 클론
git clone https://github.com/joostone-ahn/dm-log-covert.git
cd dm-log-covert

# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

#### 실행

```bash
python src/app.py
```

서버가 시작되면 브라우저에서 `http://localhost:9090`으로 접속하세요.

## 지원 파일 형식

- `.qmdl` - Qualcomm
- `.hdf` - Qualcomm
- `.dlf` - Qualcomm
- `.sdm` - Samsung

## Wireshark에서 변환된 PCAP 파일 분석하기

변환된 PCAP 파일을 Wireshark에서 제대로 분석하려면 SCAT Lua 플러그인을 설치해야 합니다.

### 1. Lua 플러그인 파일 준비

이 저장소의 `wireshark/scat.lua` 파일을 사용합니다.

### 2. Wireshark 플러그인 경로 확인

Wireshark 버전 및 운영체제에 따라 플러그인 폴더 위치가 다릅니다.

1. Wireshark를 실행합니다
2. 상단 메뉴에서 `Help > About Wireshark`를 클릭합니다
3. `Folders` 탭을 선택합니다
4. `Personal Plugins` 항목의 경로를 확인합니다

일반적인 경로:
- **Windows**: `C:\Users\<사용자명>\AppData\Roaming\Wireshark\plugins`
- **macOS**: `~/.local/lib/wireshark/plugins` 또는 `~/.wireshark/plugins`
- **Linux**: `~/.local/lib/wireshark/plugins` 또는 `~/.wireshark/plugins`

### 3. Lua 파일 복사 및 적용

1. 위에서 확인한 Personal Plugins 폴더로 이동합니다 (폴더가 없다면 직접 생성)
2. `scat.lua` 파일을 해당 폴더 안에 복사합니다
3. Wireshark를 재시작하거나, 이미 실행 중이라면 `Ctrl + Shift + L`을 눌러 Lua 엔진을 리로드합니다

### 4. 적용 여부 확인 및 필터 설정

**적용 확인**:
- `Help > About Wireshark > Plugins` 탭에서 `scat.lua`가 Lua Script 유형으로 목록에 있는지 확인합니다

**필터 적용**:
- Wireshark 상단 필터창(Display Filter)에 아래 명령어를 입력하여 SCAT을 통해 캡처된 트래픽만 선별합니다:

```
gsmtap_extra || gsmtap
```

- `gsmtap`: 표준 패킷
- `gsmtap_extra`: SCAT의 Lua 플러그인이 해석하는 확장 정보(Qualcomm/Samsung 특정 메타데이터 등)

### 주요 참고 사항

- **Wireshark 버전**: GSMTAPv3 및 최신 5G 디코딩을 위해 Wireshark 3.0.0 이상을 권장하며, 안정적인 동작을 위해 4.2.5 이상 사용이 유리합니다
- **GSMTAPv3 지원**: SCAT 1.3.0 이상 버전에서 생성된 PCAP 데이터는 표준 Wireshark 메인라인에 아직 통합되지 않은 GSMTAPv3 정의를 사용하므로, 이 Lua 플러그인이 있어야만 5G NR 메시지가 정상적으로 보입니다

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

## License

MIT License

## Third-Party Licenses

**SCAT (Signaling Collection and Analysis Tool)**
- Source: [fgsect/scat](https://github.com/fgsect/scat)
- License: GNU General Public License v2.0 or later
- Used: `wireshark/scat.lua` (Wireshark Lua plugin)
- Copyright (c) fgsect - Security in Telecommunications, TU Berlin
