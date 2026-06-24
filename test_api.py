import os
import io
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    # index.html이 존재하므로 text/html 응답이어야 함
    assert "text/html" in response.headers["content-type"]

def test_convert_txt_file():
    # 모의 텍스트 파일 생성
    file_content = b"Hello, this is a test for MarkItDown Web Service. Let's see if this converts to Markdown properly!"
    file_name = "test.txt"
    
    files = {"file": (file_name, file_content, "text/plain")}
    # Form 데이터는 문자열 형태로 전송
    response = client.post("/api/convert", files=files, data={"use_llm": "false"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"] == "test.txt"
    assert "Hello, this is a test" in data["markdown"]
    assert data["character_count"] > 0
    assert data["word_count"] > 0
    assert data["conversion_time_seconds"] >= 0

if __name__ == "__main__":
    print("--- 로컬 백엔드 API 테스트 시작 ---")
    try:
        test_read_root()
        print("[OK] 루트 엔드포인트(/) 테스트 통과!")
        test_convert_txt_file()
        print("[OK] 파일 변환 API(/api/convert) 테스트 통과!")
        print("Success: 모든 로컬 백엔드 테스트가 성공적으로 완료되었습니다!")
    except AssertionError as e:
        print("[FAIL] 테스트 검증 실패:", str(e))
    except Exception as e:
        print("[ERROR] 테스트 중 예외 발생:", str(e))
