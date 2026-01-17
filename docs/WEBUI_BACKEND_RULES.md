# WebUI Integration Rules

## Goal
All communication with Stable Diffusion WebUI must be handled by the backend.
The frontend should never call WebUI directly or rely on manual WebUI setup.

## Scope
- Applies to all image generation, ControlNet, and model configuration flows.
- Covers both txt2img and img2img.

## Rules
1) Frontend only talks to the backend API.
2) Backend owns all WebUI calls:
   - options/config updates
   - txt2img/img2img requests
   - alwayson_scripts (ControlNet, ADetailer, etc.)
3) WebUI UI is optional and treated as a debug console only.
4) Any ControlNet settings required for a run must be sent in the backend payload.
5) The backend should be the single source of truth for:
   - model selection
   - ControlNet unit settings
   - reference image handling
6) Errors from WebUI should be surfaced by the backend with actionable messages.

## Backend Settings API
Use backend-only endpoints for WebUI configuration:
- `GET /settings/webui` → returns current model + options
- `POST /settings/webui` → updates model/options
- `GET /settings/controlnet` → returns ControlNet status + backend presets

The frontend should never call WebUI config endpoints directly.

## Implementation Notes
- Keep WebUI URLs, auth, and timeouts in backend config/env.
- Frontend should expose high-level controls only (intent, not WebUI details).
- If a setting is not supported in backend, it should not appear in frontend UI.

## Non-Goals
- Manual WebUI configuration is not part of the production flow.
- Frontend does not expose raw WebUI endpoints.
