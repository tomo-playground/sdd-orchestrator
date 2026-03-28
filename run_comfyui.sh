#!/bin/bash
cd /home/tomo/ComfyUI
source .venv/bin/activate
python3 main.py --listen 0.0.0.0 --port 8188
