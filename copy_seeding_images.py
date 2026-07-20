import os
import shutil

src_dir = r"C:\Users\Dell\.gemini\antigravity\brain\60f721b9-94f7-4cf0-8d18-fc69715a3912"
dest_dir = r"d:\KhetSeva\khetseva_backend\media\provider_equipments"

os.makedirs(dest_dir, exist_ok=True)

mappings = {
    "rotavator_default_1784382281865.png": "rotavator.png",
    "harvester_default_1784382297600.png": "harvester.png",
    "borewell_default_1784382311636.png": "borewell.png"
}

for src_name, dest_name in mappings.items():
    src_path = os.path.join(src_dir, src_name)
    dest_path = os.path.join(dest_dir, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} to {dest_name}")
    else:
        print(f"Source file not found: {src_path}")
