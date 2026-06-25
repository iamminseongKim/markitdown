import os
import io
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_favicon():
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    assert "</svg>" in response.text

def test_convert_txt_file_and_check_log():
    # 모의 텍스트 파일 생성
    file_content = b"Hello, this is a test for MarkItDown Web Service. Let's see if this converts to Markdown properly!"
    file_name = "test_run.txt"
    
    files = {"file": (file_name, file_content, "text/plain")}
    response = client.post("/api/convert", files=files, data={"use_llm": "false"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"] == "test_run.txt"
    assert "Hello, this is a test" in data["markdown"]

    # config.json에서 로그 경로 읽기
    with open("config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)
    log_file = config_data.get("LOG_FILE", "conversion.log")

    # 로그 파일이 정상 생성되었는지 검증
    assert os.path.exists(log_file), "로그 파일이 생성되지 않았습니다."
    
    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
    
    # [시간] - test_run.txt - SUCCESS 형태로 기록되었는지 검증
    assert "test_run.txt - SUCCESS" in log_content, "성공 로그가 정상 포맷으로 기록되지 않았습니다."
    assert "IP" not in log_content, "IP 주소가 로그에 기록되어서는 안 됩니다."

    # 테스트 로그 복구 (깨끗한 상태 유지)
    # 실제 운영 로그에 영향을 안 주려면 해당 라인만 필터링하거나 지워줍니다.
    lines = log_content.splitlines()
    remaining_lines = [line for line in lines if "test_run.txt" not in line]
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("\n".join(remaining_lines) + ("\n" if remaining_lines else ""))

if __name__ == "__main__":
    print("--- 로컬 백엔드 API 및 개인정보 보호 로깅 테스트 시작 ---")
    try:
        test_read_root()
        print("[OK] 루트 엔드포인트(/) 테스트 통과!")
        test_favicon()
        print("[OK] 동적 SVG 파비콘(/favicon.ico) 테스트 통과!")
        test_convert_txt_file_and_check_log()
        print("[OK] 파일 변환 및 로그 기록 검증 테스트 통과!")
        print("Success: 모든 로컬 백엔드 및 로깅 검증 테스트가 성공적으로 완료되었습니다!")
    except AssertionError as e:
        print("[FAIL] 테스트 검증 실패:", str(e))
    except Exception as e:
        print("[ERROR] 테스트 중 예외 발생:", str(e))
