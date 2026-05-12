from flask import Flask, request, send_file, jsonify
from psd_tools import PSDImage
import os
from psd_layer_extract import save_visible_layers
from psd_layer_force_visible import extract_layers_force_visible

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    mode = request.form.get('mode', 'visible')  # default to visible
    filepath = os.path.join('/tmp', file.filename)
    file.save(filepath)
    size = os.path.getsize(filepath)
    print(f"DEBUG: File saved at {filepath} size= {size}")

    # Enforce tier limits
    if mode == 'visible' and size > 5 * 1024 * 1024:
        return jsonify({"error": "File exceeds 5MB limit for visible-only recovery"}), 400
    if mode == 'force' and size > 30 * 1024 * 1024:
        return jsonify({"error": "File exceeds 20MB limit for forced recovery"}), 400

    output_folder = '/tmp/output'
    os.makedirs(output_folder, exist_ok=True)

    if mode == 'visible':
        psd = PSDImage.open(filepath)
        saved_files = save_visible_layers(psd, output_folder)
        # zip & return
    else:
        zip_path = extract_layers_force_visible(filepath, output_folder)
        return send_file(zip_path, as_attachment=True)

    # zip visible layers
    zip_path = os.path.join(output_folder, "layers.zip")
    return send_file(zip_path, as_attachment=True)
