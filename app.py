#!/usr/bin/env python3
"""
app.py – Flask service using raw PSD extractor
"""

import os, zipfile
from flask import Flask, request, send_file
from psd_tools import PSDImage

# === Raw extractor function ===
def extract_layers(input_path, output_folder):
    try:
        psd = PSDImage.open(input_path)
        print(f"Loaded PSD: {input_path}")

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        for i, layer in enumerate(psd.descendants()):
            if layer.is_group():
                continue  # skip groups
            if layer.visible:
                image = layer.composite()
                if image:
                    filename = os.path.join(output_folder, f"layer_{i}_{layer.name}.png")
                    image.save(filename)
                    print(f"Saved: {filename}")

        print("Layer extraction complete.")

    except Exception as e:
        print(f"Extraction failed: {e}")

# === Flask app must be defined BEFORE routes ===
app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    filepath = os.path.join("/tmp", file.filename)
    file.save(filepath)

    output_folder = "/tmp/output"
    os.makedirs(output_folder, exist_ok=True)

    # Run the raw extractor
    extract_layers(filepath, output_folder)

    # Zip the PNGs
    zip_path = os.path.join(output_folder, "layers.zip")
    with zipfile.ZipFile(zip_path, "w") as z:
        for f in os.listdir(output_folder):
            if f.endswith(".png"):
                z.write(os.path.join(output_folder, f), f)

    return send_file(zip_path, as_attachment=True)

# === Entry point ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
