import base64
import json
import os
import shutil
import tempfile
from pathlib import Path

import cv2
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

load_dotenv()

app = FastAPI(title="AI Legal Case Analyzer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use a real API model by default. It supports image input through the Responses API.
MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
UPLOAD_DIR = Path(tempfile.gettempdir()) / "ai-legal-analyzer"
UPLOAD_DIR.mkdir(exist_ok=True)


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured in backend/.env")
    return OpenAI(api_key=api_key)


def image_data_url(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def extract_video_frames(video_path: Path, max_frames: int = 6) -> list[Path]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise HTTPException(status_code=400, detail="Could not read the uploaded video")

    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = capture.get(cv2.CAP_PROP_FPS) or 25
    count = min(max_frames, max(1, total))
    positions = [int(i * max(total - 1, 0) / max(count - 1, 1)) for i in range(count)]
    paths = []

    for index, position in enumerate(positions):
        capture.set(cv2.CAP_PROP_POS_FRAMES, position)
        ok, frame = capture.read()
        if not ok:
            continue
        frame_path = UPLOAD_DIR / f"frame_{os.getpid()}_{index}.jpg"
        cv2.imwrite(str(frame_path), frame)
        paths.append(frame_path)

    capture.release()
    return paths


def parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "incident_summary": text,
            "evidence_observations": [],
            "potential_legal_issues": [],
            "case_strength": 0,
            "case_strength_reason": "The AI returned an unstructured response, so no reliable score was assigned.",
            "missing_evidence": [],
            "next_steps": [],
            "disclaimer": "This is an AI-assisted assessment, not legal advice or a prediction of a court outcome.",
        }


@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL}


@app.post("/api/analyze")
async def analyze_case(
    description: str = Form(...),
    evidence: list[UploadFile] = File(default=[]),
):
    if not description.strip():
        raise HTTPException(status_code=400, detail="Please describe what happened")
    if len(evidence) > 8:
        raise HTTPException(status_code=400, detail="Please upload at most 8 evidence files")

    client = get_client()
    saved_files: list[Path] = []
    all_frames: list[Path] = []
    evidence_labels: list[str] = []

    try:
        for index, upload in enumerate(evidence):
            suffix = Path(upload.filename or "evidence").suffix.lower()
            allowed = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi", ".mkv"}
            if suffix not in allowed:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

            path = UPLOAD_DIR / f"upload_{os.getpid()}_{index}{suffix}"
            with path.open("wb") as buffer:
                shutil.copyfileobj(upload.file, buffer)
            saved_files.append(path)

            if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
                evidence_labels.append(upload.filename or "image")
            else:
                frames = extract_video_frames(path)
                all_frames.extend(frames)
                evidence_labels.append(f"{upload.filename or 'video'} ({len(frames)} representative frames)")

        visual_paths = [p for p in saved_files if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}] + all_frames

        content = [{
            "type": "input_text",
            "text": f"""
You are an evidence-grounded legal case analysis assistant for a hackathon demo.

USER'S DESCRIPTION:
{description}

EVIDENCE FILES:
{', '.join(evidence_labels) if evidence_labels else 'No visual evidence uploaded.'}

Analyze only what can reasonably be inferred from the description and visible evidence. Do not invent facts, laws, identities, dates, locations, or events. Do not claim that the user will win a case. The case_strength score is an evidence-quality/consistency assessment from 0 to 10, not a probability of winning.

Return ONLY valid JSON with this exact structure:
{{
  "incident_summary": "short summary",
  "evidence_observations": ["observation with confidence wording where appropriate"],
  "potential_legal_issues": ["possible issue or claim; avoid definitive legal conclusions"],
  "case_strength": 0,
  "case_strength_reason": "why the evidence supports this score",
  "missing_evidence": ["specific useful evidence still missing"],
  "next_steps": ["practical evidence-preservation or information-gathering step"],
  "disclaimer": "This is an AI-assisted assessment, not legal advice or a prediction of a court outcome."
}}
"""
        }]

        for image_path in visual_paths[:8]:
            content.append({"type": "input_image", "image_url": image_data_url(image_path)})

        response = client.responses.create(
            model=MODEL,
            input=[{"role": "user", "content": content}],
        )
        result = parse_json(response.output_text)
        result["evidence_files"] = evidence_labels
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {exc}") from exc
    finally:
        for path in saved_files + all_frames:
            path.unlink(missing_ok=True)
        for upload in evidence:
            await upload.close()
