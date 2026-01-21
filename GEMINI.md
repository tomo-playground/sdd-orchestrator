# Project: Shorts Producer

## Overview
`shorts-producer` is an AI-driven automation workspace for creating short-form videos. It orchestrates Google Gemini (Logic/Vision), Stable Diffusion (Generation), and FFmpeg (Rendering) to transform text topics into polished videos.

## Architecture

### 1. Backend (`/backend`)
Built with **FastAPI**. Currently heavily centralized in `main.py`.
- **Core Logic**:
    - **Storyboarder**: Uses `google-genai` and Jinja2 templates to plan video scripts and visual prompts.
    - **Image Pipeline**: Connects to local Stable Diffusion WebUI API. Features a **Validation Loop** using WD14 (local ONNX) and Gemini Vision to ensure image quality and relevance.
    - **Renderer**: Constructs complex FFmpeg command lines to stitch images, TTS audio (EdgeTTS), subtitles (with custom fonts), and overlays.
- **Key Files**:
    - `main.py`: Main entry point (Monolith).
    - `keywords.json`: Central config for prompt engineering, synonyms, and ignored tokens.
    - `assets/`: Stores persistent assets (fonts, overlays, default audio).

### 2. Frontend (`/frontend`)
Built with **Next.js 14+ (App Router)** and **Tailwind CSS**.
- **State Management**:
    - **Autopilot**: A client-side state machine in `app/page.tsx` that automates the [Storyboard -> Generate -> Validate -> Render] pipeline.
    - **Manual Mode**: Allows scene-by-scene editing of scripts and prompts.
- **Key Pages**:
    - `/`: Main Studio (Creation & Editing).
    - `/manage`: Keyword & Asset Manager.

## Setup Status
- [x] Version Control Initialized
- [x] Backend Core Logic (FastAPI + AI Integration)
- [x] Frontend Studio UI (Next.js + Autopilot State Machine)
- [x] Image Validation Pipeline (WD14 + Gemini)
- [x] FFmpeg Rendering Pipeline (Overlays, Subtitles, Audio)

## Critical Maintenance Targets
1.  **Refactor `backend/main.py`**: Split into `routers/` (API) and `services/` (Logic) to reduce file size (~2300 lines) and improve maintainability.
2.  **Refactor `frontend/app/page.tsx`**: Extract logic into custom hooks (`useAutopilot`) and sub-components.

## Prerequisites
- **Stable Diffusion WebUI**: `http://127.0.0.1:7860` (launch with `--api`).
- **Env Vars**: `GEMINI_API_KEY` required in `backend/.env`.
