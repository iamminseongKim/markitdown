# OCI (Ubuntu ARM64) 배포 가이드 (서버 에이전트용)

본 문서는 오라클 클라우드 인프라(OCI) Ubuntu ARM64 서버의 에이전트가 본 프로젝트(MarkItDown 웹 서비스)를 무중단 도커 컨테이너로 빌드 및 배포하고, 기존 호스트 Nginx에 리버스 프록시로 연결하기 위해 참조해야 하는 작업 지침서입니다.

---

## 1. 사전 준비 사항
서버에 다음 패키지들이 설치되어 있는지 확인하고, 설치되어 있지 않다면 설치하십시오.
- **Docker & Docker-Compose**: 컨테이너 빌드 및 오케스트레이션용
- **Nginx**: 호스트 OS에서 포트 80/443 리버스 프록싱용
- **Certbot & python3-certbot-nginx**: Let's Encrypt SSL 인증서 발급용

---

## 2. 방화벽 설정 (UFW)
호스트 OS의 UFW 및 OCI VCN의 Ingress Rules에서 HTTP(80) 및 HTTPS(443) 포트가 열려 있는지 확인합니다.
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

---

## 3. 소스코드 빌드 및 컨테이너 실행
본 프로젝트 폴더(`/app` 또는 클론된 디렉토리) 내에서 Docker Compose를 사용하여 컨테이너를 빌드하고 백그라운드로 실행합니다.

```bash
# 1. 기존 컨테이너가 실행 중이라면 중지 및 리소스 정리
sudo docker-compose down --remove-orphans

# 2. 이미지 빌드 및 컨테이너 백그라운드 구동
sudo docker-compose up -d --build

# 3. 구동 상태 확인 (127.0.0.1:8000으로 정상 바인딩되었는지 확인)
sudo docker ps
```

---

## 4. 호스트 Nginx 리버스 프록시 설정
호스트 OS에 설치된 Nginx를 통해 외부 트래픽을 컨테이너로 전달합니다.

### 4.1. Nginx 설정 파일 작성
`/etc/nginx/sites-available/markitdown` 파일을 생성하고 아래 설정을 붙여넣습니다.
*(참고: `markitdown.duckdns.org` 부분은 실제 도메인으로 치환해야 합니다.)*

```nginx
# Rate Limit 설정 (기존 nginx.conf에 'mylimit' zone이 이미 존재한다면 아래 1라인은 제외해도 됩니다)
limit_req_zone $binary_remote_addr zone=mylimit:10m rate=10r/s;

server {
    server_name markitdown.duckdns.org; # <- 실제 연동할 도메인 주소로 치환

    location / {
        limit_req zone=mylimit burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000; # 도커 컨테이너 포트 (보안을 위해 localhost 바인딩 유지)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        # 큰 파일 변환 작업을 감안하여 최대 업로드 용량 제한을 50MB로 확장
        client_max_body_size 50M;
    }

    listen 80;
}
```

### 4.2. 설정 활성화 및 Nginx 재로딩
작성한 설정을 활성화하고 Nginx를 테스트 후 반영합니다.
```bash
# 1. 활성화 링크 생성
sudo ln -sf /etc/nginx/sites-available/markitdown /etc/nginx/sites-enabled/

# 2. Nginx 설정 구문 분석 테스트
sudo nginx -t

# 3. 설정에 문제 없으면 Nginx 리로드
sudo systemctl reload nginx
```

---

## 5. SSL (HTTPS) 적용 (Certbot)
보안 연결을 위해 SSL 인증서를 발급하고 Nginx에 자동 바인딩합니다.
```bash
sudo certbot --nginx -d markitdown.duckdns.org
```
*주의: `certbot` 명령어를 실행하면 이메일 입력 및 약관 동의 절차와 함께 80 포트로 유입되는 HTTP 트래픽을 443 HTTPS로 강제 리다이렉트하는 설정이 Nginx 파일에 자동으로 주입됩니다.*

---

## 6. 배포 상태 검증
배포 완료 후 서비스 상태가 정상인지 외부 혹은 로컬에서 검증합니다.
```bash
# 1. 로컬 컨테이너 HTTP 응답 테스트
curl -I http://127.0.0.1:8000

# 2. 도메인 연결 상태 테스트 (외부 DNS 확인 필수)
curl -I https://markitdown.duckdns.org
```
정상 구동 중일 경우 `HTTP/1.1 200 OK` 응답이 리턴됩니다.
