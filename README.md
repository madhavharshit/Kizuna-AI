# SkillBridge AR — one-day hackathon starter

This starter is aligned with `Team Project Brief` and covers the required demo: PDF Document RAG, video/audio transcription with timestamps, draft SOP generation, expert edit/approve/reject, React dashboard, Expo mobile training, quiz/progress tracking, and a separate MindAR + A-Frame AR page.

> Important: this is an MVP starter, not production-grade industrial software. Every AI-created procedure starts as a draft. A human expert must verify all steps, tools, values and safety warnings before approval. Never use this demo as an authoritative safety procedure on live machinery.

## Free tools used

- Python + FastAPI for APIs; PostgreSQL via Docker Compose for app data.
- PDF extraction: `pypdf`; chunking: LangChain text splitters.
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`; vector retrieval: FAISS. The model weights download on first use.
- Speech transcription: `faster-whisper` local model (CPU `int8`, base model). Model weights download on first video.
- Optional local LLM: [Ollama](https://ollama.com/download) + `qwen2.5:3b`. There is no paid LLM API requirement. If Ollama is unavailable, RAG returns the retrieved source passages, and SOP draft generation uses a conservative extraction fallback.
- React + Vite trainer dashboard; React Native + Expo learner app; MindAR + A-Frame static web AR.

## Before starting (30–60 minutes)

Install Node.js LTS, Python 3.11, Docker Desktop, and Git. Install Expo Go on the test phone. Check that the laptop has enough free disk space: local AI packages/model weights are large.

### 1. Create a Git repo and open the project

Unzip this starter, then in its directory:

```bash
git init
git add .
git commit -m "Initial SkillBridge AR MVP scaffold"
```

Agree on the API URL and data formats before changing components. Use the supplied API as the contract.

### 2. Start PostgreSQL

```bash
docker compose up -d db
docker compose ps
```

If Docker is unavailable, install local PostgreSQL and update `DATABASE_URL` in `backend/.env`. The target stack in the brief is PostgreSQL; only use SQLite as an emergency demo fallback, and disclose it.

### 3. Start the backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --env-file .env --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for interactive API docs and `http://localhost:8000/api/health` for the health check. On first upload, embedding model weights download; on first video, Whisper weights download. Allow for this time.

### 4. Optional local LLM for better answers and SOPs

Install Ollama, then in a separate terminal:

```bash
ollama pull qwen2.5:3b
ollama run qwen2.5:3b
```

Leave Ollama running. The FastAPI app calls its local API. If your computer cannot run the model, do not lose hours: continue using the safe evidence-only fallback and focus on the complete user workflow. No OpenAI paid API key is needed. Ollama documents its local API at <https://github.com/ollama/ollama/blob/main/docs/api.md>.

### 5. Start the web trainer dashboard

In a new terminal from the project root:

```bash
cd web
npm install
cp .env.example .env
npm run dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`). The dashboard lets the trainer upload source material, ask source-backed questions, generate/edit SOP drafts, approve/reject them, and inspect training progress.

### 6. Start the Expo learner app

Find the laptop's LAN IP on the same Wi-Fi as the phone. On macOS use `ipconfig getifaddr en0` (Wi-Fi interface is often `en0`). Then edit `mobile/.env.example` or create `mobile/.env` with the actual LAN IP, not `localhost`, for example:

```bash
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000
EXPO_PUBLIC_AR_URL=https://YOUR-AR-SITE.example/ar/
```

Then run:

```bash
cd mobile
npm install
npx expo install --check
npx expo start --lan
```

Use Expo Go to scan the terminal's QR code. Your phone and laptop must be on the same Wi-Fi, and the API port must be reachable. For iPhone physical-device development, Expo may ask you to sign in to a free Expo account. If the React Native version combination installed by npm does not agree with Expo SDK, follow Expo's install output and use `npx expo install` for compatible package versions.

### 7. Test AR early — do not leave this until the final hour

The `ar/index.html` folder is a separate web AR experience. The starter uses the published MindAR sample image target by default so that you can quickly test camera tracking; the overlay text is populated from the procedure link. Open the matching target image on a second device or print it: <https://cdn.jsdelivr.net/gh/hiukim/mind-ar-js@1.2.5/examples/image-tracking/assets/card-example/card.png>. For the real station image, follow `AR-TARGET-AND-DEPLOY.md` and compile your own `.mind` file. Camera use on a phone requires a secure context (HTTPS) or localhost. Deploy the static AR page to a free HTTPS static host.

The mobile app reads `EXPO_PUBLIC_AR_URL` and passes the approved procedure title, current step, and safety note as URL parameters. A custom deployed AR page is necessary for a reliable phone demo; test the camera and target on a real phone before building other polish.

## Exact one-day build order

The order follows the PDF's implementation sequence, with one change required by the brief: prove AR camera/tracking in the very first hour so you catch device and secure-context problems early.

| Timebox | Deliverable | Must pass before moving on |
|---|---|---|
| 0:00–0:45 | Repo + API contract + test the AR sample on a phone | Target image tracked; one overlay visible |
| 0:45–2:00 | PostgreSQL + FastAPI health + source/procedure schema | `/api/health` and `/docs` open |
| 2:00–4:00 | PDF upload + extraction + chunking + embeddings + FAISS | Upload PDF, ask a question, see source/page citations |
| 4:00–5:30 | Video upload + faster-whisper transcript timestamps | Upload 30–90 sec clip and show timestamped transcript chunks |
| 5:30–7:00 | Draft SOP + edit + approve/reject | Draft has tools/warnings/steps and status; only approved SOPs publish |
| 7:00–9:00 | React dashboard integration | Trainer can complete uploads → ask → draft → approve |
| 9:00–10:30 | Expo learner app | Approved SOP → previous/next → quiz → progress saved |
| 10:30–12:00 | AR page + app link | Sample target recognized and contextual overlay visible |
| 12:00–14:00 | End-to-end rehearsal and fixes | Repeat the exact final demo twice from a clean start |

Do not spend the day on advanced visual recognition, 3D machine reconstruction, analytics, user management, or enterprise integrations; the brief explicitly excludes these from the initial prototype.

## Suggested three-person split

- **Harshit — backend/integration:** PostgreSQL, FastAPI schemas/endpoints, CORS, API integration, final complete demo and Git merge.
- **Diya — UI/mobile:** React dashboard, Expo training steps/quiz/progress, visual consistency and mobile testing.
- **Siddarth — AI + AR:** PDF chunk retrieval/FAISS, Whisper transcription, local LLM/fallback SOP draft, MindAR tracking and overlay.

Because these assignments are parallel, agree on these API contracts on minute one and don't rename endpoints independently:

- `POST /api/documents/upload` — `multipart/form-data`, field `file` (PDF) → source metadata + chunks created.
- `POST /api/videos/upload` — field `file` (video/audio) → source metadata + timestamped transcript.
- `POST /api/ask` — JSON `{ "question": "...", "source_type": null }` → `{ "answer": "...", "sources": [...] }`.
- `POST /api/procedures/draft/{source_id}` → procedure with `status: draft`.
- `GET /api/procedures?status=draft`, `PUT /api/procedures/{id}`, `POST /api/procedures/{id}/review` with `{ "action": "approve" | "reject", "note": "..." }`.
- `GET /api/training/procedures` → approved procedures only.
- `POST /api/training/progress` → saved step/quiz/completion data.

## Final demo script (3–4 minutes)

1. Trainer uploads a text-readable sample PDF and a short expert video with clear speech.
2. Ask a question. Show answer plus the source filename/page or video timestamp.
3. Generate a draft SOP. Edit one step and an explicit warning; point out it is labelled draft.
4. Approve it as a human reviewer. Show it becomes available in the approved library.
5. Open the Expo app; select the SOP, navigate steps, answer the short knowledge check, and save progress.
6. Tap **Open camera AR guidance**. Point the phone at the compiled sample target on a second device or a printout. Show the instruction and caution overlay.
7. Show the dashboard's training record and explain the local storage / source trace.

## Troubleshooting first

- **DB connection refused:** `docker compose ps`, then `docker compose up -d db`; verify port 5432 isn't already in use.
- **CORS / frontend network error:** backend and web use the same API URL; restart Vite after changing `.env`.
- **Phone cannot reach API:** use the laptop LAN IP in `mobile/.env`, ensure same Wi-Fi, and keep port 8000 open. Never use `localhost` from a physical phone to refer to the laptop.
- **FAISS / Torch install issue:** create the venv with Python 3.11; don't mix packages from the global Python environment. Install in `backend/.venv`.
- **Slow transcription:** use a 30–90 second clip, Whisper `base`; if needed use `tiny` in `backend/.env` as `WHISPER_MODEL=tiny` and restart.
- **RAG answer hallucinates:** confirm uploaded text is extractable and sources appear in the UI. Use fallback evidence mode if Ollama output is unreliable. Never approve uncited steps.
- **AR camera does not start:** deploy/open over HTTPS, grant camera permission, use Chrome/Safari on a real phone, check the console and ensure the image target is visible and well lit.

## Definition of done (match your PDF)

- [ ] Upload sample PDF and expert demo video.
- [ ] Ask a question and show document evidence.
- [ ] Show timestamped video citation.
- [ ] Generate draft SOP, edit it, approve/reject it.
- [ ] Publish approved SOP in mobile training app.
- [ ] Previous/next procedure steps work.
- [ ] Quiz and training completion progress save to API/PostgreSQL.
- [ ] Mobile AR page opens camera, tracks a sample image, and displays an instruction/warning overlay.
- [ ] Repeat full demo twice.

Current stack and official references: [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/), [FAISS](https://faiss.ai/), [Sentence Transformers model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Expo setup](https://docs.expo.dev/get-started/create-a-project/), [Expo Camera](https://docs.expo.dev/versions/latest/sdk/camera/), [MindAR image target compiler](https://hiukim.github.io/mind-ar-js-doc/tools/compile/), and [Ollama local API](https://github.com/ollama/ollama/blob/main/docs/api.md).
