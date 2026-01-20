# shorts-producer MVP

Script-first storyboard tool with manual image uploads.

## Flow
1. Enter a topic and generate a storyboard.
2. Edit scene scripts/descriptions as needed.
3. Upload a custom image for each scene.
4. Render a video with optional subtitles, narration, and BGM.

## Requirements
- Python 3.10+
- Node.js 18+
- FFmpeg installed and available on PATH
- `GEMINI_API_KEY` set in `.env` for storyboard generation

## Run
Backend:
```bash
cd backend
uv run main.py
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.
