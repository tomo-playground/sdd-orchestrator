import os
from PIL import Image, ImageOps
import numpy as np

def clean_image(input_path, output_path):
    print(f"Processing {input_path}...")
    img = Image.open(input_path).convert("RGB")
    width, height = img.size
    
    # 1. Crop margins (Top 10%, Bottom 10% usually contains text)
    top_margin = int(height * 0.1)
    bottom_margin = int(height * 0.1)
    img_cropped = img.crop((0, top_margin, width, height - bottom_margin))
    
    # 2. Resize back to original height or standard 512x768 (Optional, but let's keep it centered)
    # Actually, for ControlNet, it's better to just have a clean white background.
    
    # 3. Suppress Grids: convert to grayscale and threshold
    # Most grids are light gray. We can push everything near white to pure white.
    data = np.array(img_cropped)
    # If R, G, B are all > 200, it's likely background/grid -> make it 255
    mask = (data[:, :, 0] > 200) & (data[:, :, 1] > 200) & (data[:, :, 2] > 200)
    data[mask] = [255, 255, 255]
    
    cleaned_img = Image.fromarray(data)
    
    # 4. Final expansion back to 512x768 if needed, but let's just save the cleaned content
    cleaned_img.save(output_path)
    print(f"Saved cleaned image to {output_path}")

if __name__ == "__main__":
    assets_dir = "backend/assets/poses"
    target_files = [
        "crouching_neutral.png",
        "lying_neutral.png",
        "kneeling_neutral.png",
        "pointing_forward.png",
        "covering_face.png"
    ]
    
    for filename in target_files:
        path = os.path.join(assets_dir, filename)
        if os.path.exists(path):
            backup_path = path + ".bak"
            if not os.path.exists(backup_path):
                os.rename(path, backup_path)
                clean_image(backup_path, path)
            else:
                clean_image(backup_path, path)
        else:
            print(f"File not found: {path}")
