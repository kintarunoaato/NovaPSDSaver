from flask import Flask, request, send_file
from psd_tools import PSDImage
import os, zipfile
from psd_layer_extract import save_visible_layers   # <-- clean import

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    filepath = os.path.join('/tmp', file.filename)
    file.save(filepath)
    print(f"DEBUG: File saved at {filepath} size= {os.path.getsize(filepath)}")

    psd = PSDImage.open(filepath)
    print(f"Loaded PSD: {filepath}")

    output_folder = '/tmp/output'
    os.makedirs(output_folder, exist_ok=True)

    saved_files = save_visible_layers(psd, output_folder)
    print("Layer extraction complete.")

    zip_path = '/tmp/layers.zip'
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for f in saved_files:
            zipf.write(f, os.path.basename(f))

    return send_file(zip_path, as_attachment=True)
