import os
import json
import time
import base64
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from markitdown import MarkItDown
from openai import OpenAI

app = FastAPI(title="MarkItDown Web Service")

# --- Configuration Management ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "UPLOAD_DIR": "./workspace",
    "LOG_FILE": "./workspace/conversion.log"
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            return DEFAULT_CONFIG
        except Exception:
            return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG

config = load_config()

# Ensure directories exist
os.makedirs("static", exist_ok=True)
os.makedirs(config.get("UPLOAD_DIR", "./workspace"), exist_ok=True)

# --- Logging System ---
def write_conversion_log(filename: str, success: bool, error_msg: str = None):
    current_config = load_config()
    log_file = current_config.get("LOG_FILE", "./workspace/conversion.log")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    status = "SUCCESS" if success else f"FAILED (Reason: {error_msg})"
    log_line = f"[{timestamp}] - {filename} - {status}\n"
    
    # Print to console (stdout for Docker logs)
    print(log_line.strip(), flush=True)
    
    # Append to local log file
    try:
        # Ensure parent log directory exists
        parent_dir = os.path.dirname(log_file)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"Warning: Failed to write to log file: {str(e)}", flush=True)

# --- Audio Transcription via Gemini API ---
AUDIO_MIME_TYPES = {
    ".m4a": "audio/x-m4a",
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".webm": "audio/webm",
    ".mp4": "audio/mp4"
}

def transcribe_audio_with_gemini(file_path: str, api_key: str, mime_type: str, model_name: str = "gemini-2.0-flash") -> str:
    # Use selected Gemini model for multimodal speech transcription
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    with open(file_path, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")
        
    payload = {
        "contents": [{
            "parts": [
                {
                    "text": (
                        "이 오디오 파일의 음성을 한글로 텍스트 변환(녹취록 작성)해 주고, "
                        "대화자가 여러 명이라면 최대한 대화 형식을 유지하여 마크다운 문서로 정교하게 작성해 주세요. "
                        "문서 최하단에는 대화 내용 요약(Summary)을 한글로 추가해 주십시오."
                    )
                },
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": audio_data
                    }
                }
            ]
        }]
    }
    
    headers = {"Content-Type": "application/json"}
    # Set a long timeout (180s) because long call recordings can take time for AI to process
    with httpx.Client(timeout=180.0) as client:
        response = client.post(url, json=payload, headers=headers)
        
    if response.status_code != 200:
        raise Exception(f"Gemini API Error (Status {response.status_code}): {response.text}")
        
    result = response.json()
    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return text
    except (KeyError, IndexError):
        raise Exception(f"Failed to parse Gemini response: {json.dumps(result)}")

# --- Dynamic SVG Favicon ---
@app.get("/favicon.ico")
def get_favicon():
    # Apple-like minimalist dark gray document icon with a blue AI accent dot
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect width="100" height="100" rx="22" fill="#1d1d1f"/>
        <path d="M30 35h40v5H30zm0 12h40v5H30zm0 12h25v5H30z" fill="#f5f5f7" opacity="0.9"/>
        <circle cx="65" cy="62" r="6" fill="#0071e3"/>
    </svg>"""
    return Response(content=svg, media_type="image/svg+xml")

@app.get("/")
def read_root():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Welcome to MarkItDown Web Service. Frontend files are being prepared."}

@app.post("/api/convert")
def convert_file(
    file: UploadFile = File(...),
    use_llm: bool = Form(False),
    gemini_api_key: str = Form(None),
    gemini_model: str = Form("gemini-2.0-flash")
):
    # Reload config dynamically
    current_config = load_config()
    upload_dir = current_config.get("UPLOAD_DIR", "./workspace")

    os.makedirs(upload_dir, exist_ok=True)

    if not file.filename:
        write_conversion_log("Unknown", False, "No file uploaded (empty filename)")
        raise HTTPException(status_code=400, detail="No file uploaded.")

    # Generate path in OCI local workspace
    timestamp_ms = int(time.time() * 1000)
    safe_filename = f"tmp_{timestamp_ms}_{file.filename}"
    temp_path = os.path.join(upload_dir, safe_filename)

    try:
        # Save file to upload directory
        with open(temp_path, "wb") as buffer:
            for chunk in iter(lambda: file.file.read(8192), b""):
                buffer.write(chunk)
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        write_conversion_log(file.filename, False, f"Failed to save upload file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save upload file: {str(e)}")

    start_time = time.time()
    try:
        file_ext = os.path.splitext(file.filename.lower())[1]
        is_audio_file = file_ext in AUDIO_MIME_TYPES

        # Bypassing MarkItDown default audio converter if Gemini is active to handle large/complex audio files
        if is_audio_file and use_llm and gemini_api_key and gemini_api_key.strip():
            # Check file size limit (20MB limit for Gemini generateContent inlineData REST payload)
            size_bytes = os.path.getsize(temp_path)
            if size_bytes > 20 * 1024 * 1024:
                raise Exception("오디오 파일 크기가 20MB 제한을 초과했습니다. 더 짧게 분할하거나 압축하여 업로드해 주세요.")
                
            mime_type = AUDIO_MIME_TYPES[file_ext]
            markdown_content = transcribe_audio_with_gemini(temp_path, gemini_api_key.strip(), mime_type, gemini_model.strip())
            conversion_time = round(time.time() - start_time, 2)
        else:
            # Initialize standard MarkItDown
            if use_llm and gemini_api_key and gemini_api_key.strip():
                client = OpenAI(
                    api_key=gemini_api_key.strip(),
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                md = MarkItDown(llm_client=client, llm_model=gemini_model.strip())
            else:
                md = MarkItDown()

            # Perform conversion
            result = md.convert(temp_path)
            markdown_content = result.text_content
            conversion_time = round(time.time() - start_time, 2)

        # Log conversion success without client IP
        write_conversion_log(file.filename, True)
        size_bytes = os.path.getsize(temp_path)

        return JSONResponse(content={
            "status": "success",
            "filename": file.filename,
            "size_bytes": size_bytes,
            "conversion_time_seconds": conversion_time,
            "character_count": len(markdown_content),
            "word_count": len(markdown_content.split()),
            "markdown": markdown_content
        })
    except Exception as e:
        error_msg = str(e)
        # Catch SpeechRecognition's UnknownValueError and provide a user friendly guidance
        if "UnknownValueError" in error_msg:
            friendly_msg = (
                "음성 인식(Speech Recognition)이 거부되었습니다. "
                "대용량 녹음 파일이나 특수 코덱 음성은 구글 Gemini API 키 연동을 활성화하고 변환해야 합니다. "
                "'Google Gemini API 연동 활성화' 체크박스를 켜고 API Key를 입력한 뒤 다시 시도해 주십시오."
            )
            write_conversion_log(file.filename, False, "SpeechRecognition UnknownValueError")
            raise HTTPException(status_code=400, detail=friendly_msg)
            
        write_conversion_log(file.filename, False, error_msg)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {error_msg}")
    finally:
        # Clean up temp upload file immediately to maintain OCI storage
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# Mount static directory for JS and CSS files
app.mount("/static", StaticFiles(directory="static"), name="static")
