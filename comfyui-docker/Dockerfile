# syntax=docker/dockerfile:1
# ComfyUI on NVIDIA CUDA 12.8
FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev git wget curl \
    libgl1 libglib2.0-0 ffmpeg \
    libgoogle-perftools-dev && \
    rm -rf /var/lib/apt/lists/*

# Non-root user
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} comfyui && \
    useradd -m -u ${USER_ID} -g ${GROUP_ID} comfyui

RUN mkdir -p /workspace/ComfyUI && \
    chown comfyui:comfyui /workspace/ComfyUI

WORKDIR /workspace/ComfyUI
USER comfyui

# Virtual environment
RUN python3 -m venv venv

# Layer 1: Torch + CUDA
RUN --mount=type=cache,target=/home/comfyui/.cache/pip,uid=${USER_ID},gid=${GROUP_ID} \
    venv/bin/pip install --upgrade pip setuptools && \
    venv/bin/pip install torch torchvision \
        --index-url https://download.pytorch.org/whl/cu128

# Layer 2: xformers
RUN --mount=type=cache,target=/home/comfyui/.cache/pip,uid=${USER_ID},gid=${GROUP_ID} \
    venv/bin/pip install xformers

# Clone ComfyUI
RUN git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git . && \
    rm -rf .git

# Layer 3: ComfyUI dependencies
RUN --mount=type=cache,target=/home/comfyui/.cache/pip,uid=${USER_ID},gid=${GROUP_ID} \
    venv/bin/pip install -r requirements.txt

# Custom nodes: ComfyUI-Manager
RUN git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager && \
    rm -rf custom_nodes/ComfyUI-Manager/.git

# Runtime directories
RUN mkdir -p output input models/checkpoints models/loras models/embeddings \
    models/controlnet models/clip_vision models/vae

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8188/system_stats || exit 1

EXPOSE 8188
CMD ["/bin/bash", "-lc", "source venv/bin/activate && python main.py --listen 0.0.0.0 --port 8188"]
