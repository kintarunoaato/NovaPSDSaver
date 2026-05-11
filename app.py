#!/usr/bin/env python3
"""
psd_layer_extract.py – Extracts layers from a PSD file
Usage: python psd_layer_extract.py comic.psd output_folder
"""

import sys
import os
from psd_tools import PSDImage

def extract_layers(input_path, output_folder):
    try:
        psd = PSDImage.open(input_path)
        print(f"Loaded PSD: {input_path}")

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        for i, layer in enumerate(psd.descendants()):
            if layer.is_group():
                continue  # skip groups, only export visible layers
            if layer.visible:
                image = layer.composite()
                if image:
                    filename = os.path.join(output_folder, f"layer_{i}_{layer.name}.png")
                    image.save(filename)
                    print(f"Saved: {filename}")

        print("Layer extraction complete.")

    except Exception as e:
        print(f"Extraction failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python psd_layer_extract.py input.psd output_folder")
    else:
        extract_layers(sys.argv[1], sys.argv[2])

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    filepath = os.path.join("/tmp", file.filename)
    file.save(filepath)

    output_folder = "/tmp/output"
    os.makedirs(output_folder, exist_ok=True)

    # Run the raw extractor
    extract_layers(filepath, output_folder)

    # Now zip the PNGs
    zip_path = os.path.join(output_folder, "layers.zip")
    import zipfile
    with zipfile.ZipFile(zip_path, "w") as z:
        for f in os.listdir(output_folder):
            if f.endswith(".png"):
                z.write(os.path.join(output_folder, f), f)

    return send_file(zip_path, as_attachment=True)
