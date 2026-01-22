# API Specification (Lite)

프론트엔드와 백엔드 간 데이터 통신을 위한 핵심 약속입니다.

## 🎬 Storyboard
### `POST /storyboard/create`
*   **Input**:
    ```json
    {
      "topic": "string",
      "duration": 10,
      "style": "Anime",
      "language": "Korean"
    }
    ```
*   **Output**: `scenes: [{ script, image_prompt, duration, ... }]`

## 🖼️ Image Generation
### `POST /scene/generate`
*   **Input**:
    ```json
    {
      "prompt": "1girl, coffee...",
      "width": 512,
      "height": 512,
      "steps": 27,
      "enable_hr": true,
      "hr_scale": 2.0
    }
    ```
*   **Output**: `image: "base64_string..."`

## 🚀 Video Rendering
### `POST /video/create`
*   **Input (Critical Fields)**:
    *   `layout_style`: "full" | "post" (※ snake_case 주의)
    *   `motion_style`: "slow_zoom" | "none"
    *   `narrator_voice`: "ko-KR-..."
*   **Output**: `video_url: "http://..."`

## 🧠 Intelligence
### `POST /keywords/append`
*   **Input**: `{"tag": "new word", "category": "optional"}`
*   **Output**: `{"ok": true, "category": "assigned_category"}`
