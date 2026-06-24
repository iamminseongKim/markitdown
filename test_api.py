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

def test_convert_txt_file_and_backup():
    # 모의 텍스트 파일 생성
    file_content = b"Hello, this is a test for MarkItDown Web Service. Let's see if this converts to Markdown properly!"
    file_name = "test.txt"
    
    files = {"file": (file_name, file_content, "text/plain")}
    response = client.post("/api/convert", files=files, data={"use_llm": "false"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"] == "test.txt"
    assert "Hello, this is a test" in data["markdown"]
    assert data["character_count"] > 0
    assert data["word_count"] > 0
    assert data["conversion_time_seconds"] >= 0

    # config.json에서 백업 경로 읽기
    with open("config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)
    backup_dir = config_data.get("BACKUP_DIR", "./backup")

    # 백업 파일이 정상 생성되었는지 검증
    assert os.path.exists(backup_dir)
    files_in_backup = os.listdir(backup_dir)
    
    # test.txt 및 test.txt.md 패턴 파일 필터링
    orig_backups = [f for f in files_in_backup if f.endswith("_test.txt")]
    md_backups = [f for f in files_in_backup if f.endswith("_test.txt.md")]

    assert len(orig_backups) > 0, "원본 백업 파일이 생성되지 않았습니다."
    assert len(md_backups) > 0, "마크다운 백업 파일이 생성되지 않았습니다."

    # 백업된 마크다운 내용 검증
    with open(os.path.join(backup_dir, md_backups[0]), "r", encoding="utf-8") as f:
        backup_content = f.read()
    assert "Hello, this is a test" in backup_content

    # 테스트 생성물 정리 (원격 저장소 및 로컬 테스트 클린업)
    for f in orig_backups + md_backups:
        os.unlink(os.path.join(backup_dir, f))

if __name__ == "__main__":
    print("--- 로컬 백엔드 API 및 백업 시스템 테스트 시작 ---")
    try:
        test_read_root()
        print("[OK] 루트 엔드포인트(/) 테스트 통과!")
        test_favicon()
        print("[OK] 동적 SVG 파비콘(/favicon.ico) 테스트 통과!")
        test_convert_txt_file_and_backup()
        print("[OK] 파일 변환 및 백업 생성 테스트 통과!")
        print("Success: 모든 로컬 백엔드 및 백업 검증 테스트가 성공적으로 완료되었습니다!")
    except AssertionError as e:
        print("[FAIL] 테스트 검증 실패:", str(e))
    except Exception as e:
        print("[ERROR] 테스트 중 예외 발생:", str(e))
