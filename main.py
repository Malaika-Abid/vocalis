import io
import os
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from vocalis.analyzer import AudioAnalyzer
from vocalis.models import AnalysisResponse

app = FastAPI(title="Vocalis", description="Acoustic Speech Delivery & Dynamics Analyzer")

# Allow CORS for development ease
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

analyzer = AudioAnalyzer()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return FileResponse(index_file)

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_audio(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        result = analyzer.analyze(content)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/api/sample")
async def analyze_sample():
    sample_file = BASE_DIR / "sample_test.wav"
    if not sample_file.exists():
        raise HTTPException(status_code=404, detail="Sample audio not found")
    
    try:
        result = analyzer.analyze(str(sample_file))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze sample: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Vocalis Web Server")
    parser.add_argument("--ssl", action="store_true", help="Force HTTPS using SSL certificates")
    parser.add_argument("--no-ssl", action="store_true", help="Force plain HTTP")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface")
    args, _ = parser.parse_known_args()

    port = int(os.environ.get("PORT", args.port))
    use_ssl = args.ssl and cert_path.exists() and key_path.exists()

    if use_ssl and cert_path.exists() and key_path.exists():
        print(f"\n🔒 Running Vocalis with HTTPS (Secure Context for Mic Access):")
        print(f" • Local: https://localhost:{port}/")
        print(f" • Team:  https://10.128.192.151:{port}/\n")
        uvicorn.run(
            "main:app",
            host=args.host,
            port=port,
            reload=True,
            ssl_keyfile=str(key_path),
            ssl_certfile=str(cert_path),
        )
    else:
        print(f"\n⚡ Running Vocalis with HTTP:")
        print(f" • Local: http://localhost:{port}/")
        print(f" • Team:  http://10.128.192.151:{port}/\n")
        uvicorn.run("main:app", host=args.host, port=port, reload=True)

