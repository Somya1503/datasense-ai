"""FastAPI application: routing, validation and CORS for DataSense AI."""

import logging
import os
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from analyzer import CSVAnalysisError, analyze_csv_bytes

logger = logging.getLogger("datasense")
logging.basicConfig(level=logging.INFO)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Comma-separated list of allowed origins. Later, set this on Render, e.g.
# CORS_ORIGINS=http://localhost:5173,https://your-app.vercel.app
DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

app = FastAPI(title="DataSense AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/analyze")
async def analyze(file: Optional[UploadFile] = File(default=None)):
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded. Send a CSV as form field 'file'.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    # Read at most limit + 1 bytes so oversized uploads are detected without loading everything.
    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File is too large. Maximum size is 10 MB.")
    if not content.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if b"\x00" in content[:8192]:
        raise HTTPException(status_code=400, detail="The file looks binary, not a text CSV.")

    try:
        analysis = await run_in_threadpool(analyze_csv_bytes, content)
    except CSVAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Unexpected error while analyzing %s", file.filename)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while analyzing the file. Please try another CSV.",
        )

    return {"filename": file.filename, "analysis": analysis}