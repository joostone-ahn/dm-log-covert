# DM Log Converter

DM 로그를 PCAP으로 변환하는 웹 도구입니다.

## 지원 파일

- Qualcomm: `.qmdl`, `.hdf`, `.dlf`
- Samsung: `.sdm`

## 실행 방법

### 1. Docker 이미지 다운로드

```bash
docker pull ghcr.io/joostone-ahn/dm-log-covert:latest
```

### 2. 작업 디렉토리 생성

원하는 위치에 작업 디렉토리를 만들고 그 안에 `logs` 폴더를 생성합니다.

```bash
# 작업 디렉토리 생성 및 이동
mkdir dm-converter
cd dm-converter

# logs 폴더 생성
mkdir logs
```

### 3. 변환할 파일 복사

변환할 DM 로그 파일을 `logs` 폴더에 복사합니다.

```bash
# 예시: 다른 위치의 로그 파일을 logs 폴더로 복사
cp /path/to/your/logs/*.qmdl logs/
```

### 4. 컨테이너 실행

작업 디렉토리(`dm-converter`)에서 Docker 컨테이너를 실행합니다.

**macOS / Linux**
```bash
docker run -d \
  -p 9090:9090 \
  -v $(pwd)/logs:/logs \
  --name dm-log-converter \
  ghcr.io/joostone-ahn/dm-log-covert:latest
```

**Windows (PowerShell)**
```powershell
docker run -d `
  -p 9090:9090 `
  -v ${PWD}/logs:/logs `
  --name dm-log-converter `
  ghcr.io/joostone-ahn/dm-log-covert:latest
```

**Apple Silicon Mac**
```bash
docker run -d \
  --platform linux/amd64 \
  -p 9090:9090 \
  -v $(pwd)/logs:/logs \
  --name dm-log-converter \
  ghcr.io/joostone-ahn/dm-log-covert:latest
```

### 5. 웹 UI 접속

브라우저에서 http://localhost:9090 접속

## 사용 방법

1. 웹 페이지에서 `logs` 폴더의 파일 목록 확인
2. 필요시 변환 옵션 조정 (레이어, GSMTAPv3)
3. "일괄 변환" 버튼 클릭
4. 변환 완료 후 `logs` 폴더에서 생성된 `.pcap` 파일 확인

> 원본 파일(`.qmdl`, `.hdf` 등)과 변환된 파일(`.pcap`)이 같은 `logs` 폴더에 저장됩니다.

## 디렉토리 구조 예시

```
dm-converter/              # 작업 디렉토리
└── logs/                  # 로그 파일 폴더
    ├── test1.qmdl        # 원본 DM 로그
    ├── test1.pcap        # 변환된 PCAP (변환 후 생성)
    ├── test2.hdf         # 원본 DM 로그
    └── test2.pcap        # 변환된 PCAP (변환 후 생성)
```

## Docker 명령어

```bash
# 중지/시작/재시작
docker stop dm-log-converter
docker start dm-log-converter
docker restart dm-log-converter

# 삭제
docker rm -f dm-log-converter

# 로그 확인
docker logs -f dm-log-converter

# 이미지 업데이트
docker pull ghcr.io/joostone-ahn/dm-log-covert:latest
docker rm -f dm-log-converter
# 위의 실행 명령어로 재실행
```

## 라이선스

MIT License | SCAT: GPL v2.0

