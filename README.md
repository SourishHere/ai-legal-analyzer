# CaseLens AI — AI Legal Case Analyzer

A hackathon MVP that combines an incident description with uploaded photo/video evidence to produce an evidence-grounded case assessment.

## What it does

1. Describe what happened.
2. Upload photos and/or videos.
3. Video files are sampled into representative frames.
4. OpenAI vision analyzes the visuals alongside the description.
5. The app returns an incident summary, evidence observations, potentially relevant issues, an evidence-strength score, missing evidence, and practical next steps.

The score is **not** a probability of winning and the app does not provide legal advice.

## Run in Codespaces

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put your OpenAI API key in `backend/.env`.

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the forwarded Vite port in the Codespaces **Ports** tab.

If the frontend cannot reach the backend, set `VITE_API_URL` to the forwarded backend URL before starting Vite.

## Notes

- Maximum 8 evidence files per analysis.
- Images are sent as vision inputs.
- Videos are sampled into representative frames for this MVP.
- Uploaded files are temporary and deleted after analysis.
- Never commit a real API key to GitHub.
