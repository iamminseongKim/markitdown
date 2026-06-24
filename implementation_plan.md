# MarkItDown 기반 파일 변환 웹 서비스 구축 계획

본 프로젝트는 Microsoft의 `markitdown` 라이브러리를 활용하여 다양한 형식의 파일(PDF, Word, Excel, PPTX, 이미지 등)을 Markdown(`.md`) 형식으로 변환하고, 이를 다운로드하거나 즉시 복사할 수 있는 반응형 웹 서비스를 구축하는 계획입니다. 사용자님의 피드백을 반영하여 **선택적 Gemini API 연동** 및 **GitHub + Docker 배포 방안**을 중점적으로 구성했습니다.

---

## 1. 아키텍처 개요

전체 시스템은 다음과 같은 흐름으로 작동합니다. 사용자가 브라우저를 통해 파일을 업로드하고, 선택적으로 Gemini API 사용 여부와 API Key를 입력하면 백엔드에서 이를 적용하여 고도화된 변환을 수행합니다.

```mermaid
graph TD
    Client[웹 브라우저 프론트엔드] -->|1. 파일 및 API Key 전송| API[FastAPI 백엔드 (Docker)]
    API -->|2. Gemini 활성화 시| Gemini[Google Gemini API]
    Gemini -->|3. OCR/이미지 설명 응답| API
    API -->|4. 파일 변환| MID[MarkItDown 라이브러리]
    MID -->|5. 결과 추출| API
    API -->|6. 결과 JSON 반환| Client
    Client -->|7. 복사 또는 .md 다운로드| Client
```

---

## 2. 기술 스택 및 개발 스펙

### 백엔드 (Backend)
- **Language**: Python 3.10+
- **Framework**: **FastAPI**
- **Libraries**:
  - `markitdown>=0.0.1a2`
  - `openai>=1.0.0` (Gemini API를 OpenAI 호환 엔드포인트로 연동하기 위함)
  - `python-multipart` (파일 업로드 지원)

### 프론트엔드 (Frontend)
- **Structure & Logic**: HTML5 + Vanilla JavaScript (SPA 구조)
- **Styling**: Vanilla CSS (딥 퍼플/인디고 다크 모드, 글래스모피즘 테마)
- **주요 UI 요소**:
  - **Gemini 옵션 토글**: "구글 Gemini API로 변환 개선 (이미지 설명 등)" 체크박스
  - **API Key 입력 필드**: 사용자가 직접 자신의 Gemini API Key (무료/유료)를 입력할 수 있는 필드 (로컬 스토리지에 안전하게 저장하여 재입력 방지)
  - **마크다운 뷰어**: 렌더링 뷰어(Marked.js) 및 Raw 코드 뷰어 제공

### 배포 환경 (Deployment)
- **Repository**: GitHub
- **Container**: Docker + Docker-Compose
- **Reverse Proxy**: Host OS에 기설치된 Nginx (사용자님의 기존 Nginx 설정 활용)

---

## 3. 상세 제안 변경 사항 (Proposed Changes)

### [백엔드 & 전체 설정]

#### [NEW] [main.py](file:///c:/study/markitdown/main.py)
- API 엔트리 포인트. `/api/convert`에서 파일과 함께 선택적으로 전달된 `gemini_api_key`를 받습니다.
- 키가 제공되면 `openai.OpenAI` 클라이언트를 생성하여 `base_url="https://generativelanguage.googleapis.com/v1beta/openai/"`로 설정하고 `MarkItDown(llm_client=client, llm_model="gemini-2.0-flash")` 인스턴스를 동적으로 생성하여 처리합니다.
- 키가 없으면 기본 `MarkItDown()` 인스턴스를 사용하여 오프라인으로 고속 변환합니다.

#### [NEW] [requirements.txt](file:///c:/study/markitdown/requirements.txt)
- 의존성 패키지 명시:
  ```text
  fastapi>=0.100.0
  uvicorn>=0.22.0
  python-multipart>=0.0.6
  markitdown>=0.0.1a2
  openai>=1.0.0
  ```

### [프론트엔드]

#### [NEW] [index.html](file:///c:/study/markitdown/static/index.html)
- 드래그 앤 드롭 업로드 카드.
- Gemini API 연동 설정 영역 (체크박스 및 패스워드 타입의 API Key 입력란).
- 실시간 변환 렌더링 미리보기 및 Raw 마크다운 텍스트 뷰어 카드.

#### [NEW] [style.css](file:///c:/study/markitdown/static/style.css)
- 딥 블랙/네온 인디고 톤의 세련된 다크 모드 스타일시트.
- 업로드 영역 점선 테두리 애니메이션 및 버튼 마이크로 인터랙션 구현.

#### [NEW] [app.js](file:///c:/study/markitdown/static/app.js)
- 파일 드래그/셀렉트 및 FormData 생성 로직.
- API Key 입력값을 브라우저 `localStorage`에 자동 저장/로드하는 로직.
- 백엔드 변환 요청 후 결과 데이터를 받아 다운로드 처리 및 코드 복사 기능 제어.

---

## 4. 오라클 A1.Flex 배포 및 Nginx 연동 가이드

기존 OCI Ubuntu 인스턴스에 적용하실 수 있도록 GitHub과 Docker를 활용한 상세 배포 가이드를 제공합니다.

### 1단계: 프로젝트 컨테이너화

#### [NEW] [Dockerfile](file:///c:/study/markitdown/Dockerfile)
ARM64 아키텍처 환경에서 가볍고 빠르게 빌드되도록 Python 3.11-slim 기반으로 작성합니다.
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### [NEW] [docker-compose.yml](file:///c:/study/markitdown/docker-compose.yml)
포트 8000번으로 바인딩하여 백그라운드 구동하도록 설정합니다.
```yaml
version: '3.8'

services:
  markitdown-web:
    build: .
    image: markitdown-web:latest
    container_name: markitdown-web-app
    ports:
      - "127.0.0.1:8000:8000"
    restart: always
```
> [!NOTE]
> 보안을 위해 포트를 외부 전체(`0.0.0.0:8000`)에 열지 않고 로컬호스트(`127.0.0.1:8000`)에만 바인딩하여, 오직 호스트의 Nginx를 통해서만 트래픽이 접근하도록 설계합니다.

---

### 2단계: Nginx 역방향 프록시 연동 (기존 설정 반영)

사용자님의 기존 Nginx 설정 패턴(Rate limit 및 SSL 적용)을 유지하면서 새 도메인(예: `markitdown.duckdns.org`)을 연결하는 프록시 설정 예시입니다. Host OS의 `/etc/nginx/sites-available/`에 아래 설정을 등록합니다.

```nginx
# Rate Limit 설정 (기존 nginx.conf에 이미 정의되어 있다면 중복 정의하지 않아도 됩니다)
# limit_req_zone $binary_remote_addr zone=mylimit:10m rate=10r/s;

server {
    server_name markitdown.duckdns.org; # 새로운 서브도메인 또는 OCI 도메인 입력

    location / {
        limit_req zone=mylimit burst=20 nodelay;
        proxy_pass http://localhost:8000; # 도커 컨테이너 포트(8000)로 전달
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        # 파일 업로드 용량 제한 해제 (마크다운 변환할 대용량 PDF 등을 감안하여 50MB로 설정)
        client_max_body_size 50M;
    }

    listen 443 ssl; # Certbot으로 SSL 인증서 발급 필요
    ssl_certificate /etc/letsencrypt/live/markitdown.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/markitdown.duckdns.org/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if ($host = markitdown.duckdns.org) {
        return 301 https://$host$request_uri;
    }

    listen 80;
    server_name markitdown.duckdns.org;
    return 404;
}
```

---

### 3단계: OCI Ubuntu 실서버 배포 프로세스

1. **로컬 개발 완료 후 GitHub 푸시**:
   ```bash
   git init
   git add .
   git commit -m "feat: initial commit for markitdown web service"
   git remote add origin <사용자_깃허브_레포_주소>
   git branch -M main
   git push -u origin main
   ```

2. **OCI Ubuntu 서버 접속 후 클론**:
   ```bash
   git clone <사용자_깃허브_레포_주소> markitdown-web
   cd markitdown-web
   ```

3. **Docker Compose 빌드 및 실행**:
   ```bash
   sudo docker-compose up -d --build
   ```

4. **Nginx 설정 및 SSL 등록**:
   - `/etc/nginx/sites-available/markitdown` 파일 생성 후 위 2단계 Nginx 템플릿 입력.
   - 활성화 링크 생성: `sudo ln -s /etc/nginx/sites-available/markitdown /etc/nginx/sites-enabled/`
   - Nginx 테스트 및 재시작: `sudo nginx -t && sudo systemctl reload nginx`
   - SSL 인증서 적용: `sudo certbot --nginx -d markitdown.duckdns.org`

---

## 5. 검증 및 테스트 계획

### 자동화 테스트
- `pytest`를 활용하여 `/api/convert` 엔드포인트 테스트 수행.
- Gemini API 키 제공 시와 미제공 시의 변환 분기 로직 정상 작동 여부 유닛 테스트.

### 수동 검증
- PDF, DOCX, XLSX, 이미지 파일을 업로드하여 텍스트 및 이미지 설명이 정상적으로 Markdown화 되는지 확인.
- 변환된 마크다운을 브라우저에서 다운로드하여 온전한 `.md` 파일이 되는지 체크.
- 프론트엔드의 "텍스트 복사" 버튼을 클릭하여 클립보드에 마크다운 형식이 그대로 복사되는지 검증.
