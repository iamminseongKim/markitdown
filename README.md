# MarkItDown Web Service

Microsoft의 [MarkItDown](https://github.com/microsoft/markitdown) 라이브러리를 활용하여 다양한 문서와 미디어 파일을 대규모 언어 모델(LLM) 및 RAG 파이프라인에 최적화된 마크다운(`.md`) 파일로 편리하게 변환하고 관리할 수 있는 반응형 웹 서비스입니다.

---

## ✨ 핵심 기능

1. **다양한 파일 포맷 변환 지원**
   - **문서**: PDF, Word(`.docx`), Excel(`.xlsx`), PowerPoint(`.pptx`), TXT, CSV, JSON 등
   - **미디어**: 이미지(EXIF 메타데이터 및 OCR 분석), 오디오(`.mp3`, `.wav`)
   - **압축 파일**: ZIP 아카이브 내 파일 재귀적 분석 지원
2. **선택적 Google Gemini AI 연동**
   - 브라우저 상에서 체크박스 하나로 Gemini API 연동 여부를 활성화할 수 있습니다.
   - 활성화 시, 이미지 OCR 고도화, 이미지 설명 생성, 오디오 녹취록 작성 등의 AI 특화 변환이 가능합니다.
   - 입력한 API Key는 브라우저 `localStorage`에만 보관되어 매번 재입력하지 않아도 됩니다.
3. **사용자 친화적 프리미엄 UI/UX**
   - 드래그 앤 드롭 파일 업로드 지원 및 마이크로 로딩 애니메이션 제공
   - 모던하고 미려한 딥 네이비 / 퍼플 그라데이션 포인트 다크 테마 적용
   - 실시간 마크다운 미리보기(HTML 렌더링) 및 Raw 코드 뷰어 제공
   - 원클릭 클립보드 텍스트 복사 및 원본명 기반의 `.md` 파일 다운로드 기능

---

## 🛠 기술 스택

- **Backend**: FastAPI, Uvicorn, Python-Multipart, OpenAI SDK (Gemini OpenAI 호환 API 연동용)
- **Frontend**: HTML5, Vanilla JavaScript, Vanilla CSS (Glassmorphism & Responsive layout), Marked.js, Lucide Icons
- **Deployment**: Docker, Docker-Compose, Nginx (Host OS Reverse Proxy), Certbot (SSL)

---

## 💻 로컬 실행 방법

### 1) Python 가상환경을 통한 직접 실행

의존성 라이브러리를 설치하고 FastAPI 서버를 직접 구동합니다.

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. Uvicorn 개발 서버 실행
python -m uvicorn main:app --reload
```
서버 실행 후 브라우저에서 `http://127.0.0.1:8000`에 접속합니다.

### 2) Docker를 통한 실행

로컬 환경에 Docker와 Docker Compose가 설치되어 있다면 한 줄의 명령어로 컨테이너 빌드 및 구동이 가능합니다.

```bash
docker-compose up -d --build
```
구동이 완료되면 동일하게 `http://127.0.0.1:8000`으로 접속하여 테스트할 수 있습니다.

---

## 🚀 실서버 배포 가이드 (Oracle Cloud / Ubuntu)

Oracle Cloud Infrastructure (OCI) A1.Flex 및 Ubuntu 환경에서 서비스 구축, 기존 Nginx 리버스 프록시 연동, Certbot SSL 적용에 대한 자세한 안내는 [DEPLOY_GUIDE.md](./DEPLOY_GUIDE.md) 문서를 참조하십시오.
