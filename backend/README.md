# Backend (MVP)

Minimal API for storyboard generation and video rendering.

## Endpoints
- `POST /storyboard/create` Generate scenes from a topic
- `GET /audio/list` List BGM files in `assets/audio`
- `POST /video/create` Render the final video

## Run
```bash
uv run main.py
```

## Env
- `GEMINI_API_KEY` required for storyboard generation
- `LOG_FILE` optional (default `logs/backend.log`)
