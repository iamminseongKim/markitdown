import os
import shutil
import tempfile
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from markitdown import MarkItDown
from openai import OpenAI

app = FastAPI(title="MarkItDown Web Service")

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)

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
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    # Create temporary file
    suffix = os.path.splitext(file.filename)[1]
    # Use delete=False so we can close the file and pass it to MarkItDown safely, then unlink in finally block
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = temp_file.name
        try:
            # Write uploaded content to temp file
            shutil.copyfileobj(file.file, temp_file)
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise HTTPException(status_code=500, detail=f"Failed to save temporary file: {str(e)}")

    start_time = time.time()
    try:
        # Initialize MarkItDown
        if use_llm and gemini_api_key and gemini_api_key.strip():
            # Configure Gemini via OpenAI-compatible endpoint
            client = OpenAI(
                api_key=gemini_api_key.strip(),
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            # gemini-2.0-flash is the standard fast & multimodal model
            md = MarkItDown(llm_client=client, llm_model="gemini-2.0-flash")
        else:
            md = MarkItDown()

        # Perform conversion
        result = md.convert(temp_path)
        markdown_content = result.text_content
        conversion_time = round(time.time() - start_time, 2)

        return JSONResponse(content={
            "status": "success",
            "filename": file.filename,
            "size_bytes": os.path.getsize(temp_path),
            "conversion_time_seconds": conversion_time,
            "character_count": len(markdown_content),
            "word_count": len(markdown_content.split()),
            "markdown": markdown_content
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# Mount static directory for JS and CSS files
app.mount("/static", StaticFiles(directory="static"), name="static")
