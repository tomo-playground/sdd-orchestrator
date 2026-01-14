# Project: Shorts Producer

## Overview
`shorts-producer` is a workspace for automating short-form video content production.
It currently consists of a Python FastAPI backend for image generation (via Stable Diffusion) and a Next.js frontend.

## Directory Structure
- `backend/`: FastAPI application.
    - `main.py`: Entry point. Handles translation (Korean -> English) and calls the Stable Diffusion API.
    - Run with: `uv run main.py` or `python main.py` (ensure `.venv` is active).
- `frontend/`: Next.js application.
    - `app/page.tsx`: Main UI for prompt input and image display.
    - Run with: `npm run dev`.

## Setup Status
- [x] Version Control Initialized (User to confirm)
- [x] Backend Scaffolding (FastAPI, deep-translator, httpx)
- [x] Frontend Scaffolding (Next.js, Tailwind, Axios)
- [x] Basic Integration (Frontend connects to Backend `POST /generate`)

## Prerequisites
- **Stable Diffusion WebUI**: Must be running locally on port 7860 with `--api` enabled.
  - URL: `http://127.0.0.1:7860`

## Next Steps
1.  **Run the servers:** Start both backend and frontend.
2.  **Test:** Generate an image via the web interface.
3.  **Expand:** Add video generation or stitching capabilities.