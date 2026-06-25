import os
import json
import time
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
    "LOG_FILE": "conversion.log"
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
    log_file = current_config.get("LOG_FILE", "conversion.log")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    status = "SUCCESS" if success else f"FAILED (Reason: {error_msg})"
    log_line = f"[{timestamp}] - {filename} - {status}\n"
    
    # Print to console (stdout for Docker logs)
    print(log_line.strip(), flush=True)
    
    # Append to local log file
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"Warning: Failed to write to log file: {str(e)}", flush=True)

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
    gemini_api_key: str = Form(None)
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
            # Chunk writing instead of copying whole file object is safer
            for chunk in iter(lambda: file.file.read(8192), b""):
                buffer.write(chunk)
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        write_conversion_log(file.filename, False, f"Failed to save upload file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save upload file: {str(e)}")

    start_time = time.time()
    try:
        # Initialize MarkItDown
        if use_llm and gemini_api_key and gemini_api_key.strip():
            client = OpenAI(
                api_key=gemini_api_key.strip(),
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            md = MarkItDown(llm_client=client, llm_model="gemini-2.0-flash")
        else:
            md = MarkItDown()

        # Perform conversion
        result = md.convert(temp_path)
        markdown_content = result.text_content
        conversion_time = round(time.time() - start_time, 2)
        size_bytes = os.path.getsize(temp_path)

        # Log conversion success without client IP
        write_conversion_log(file.filename, True)

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
        write_conversion_log(file.filename, False, str(e))
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    finally:
        # Clean up temp upload file immediately to maintain OCI storage
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# Mount static directory for JS and CSS files
app.mount("/static", StaticFiles(directory="static"), name="static")
