from flask import Flask, request, send_file, jsonify
from psd_tools import PSDImage
import os, io, zipfile
from psd_layer_extract import save_visible_layers
from psd_layer_force_visible import extract_layers_force_visible

app = Flask(__name__)

BASE_DIR = "/home/renderuser"  # adjust to your Render project root
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    mode = request.form.get('mode', 'visible')  # default to visible
    filename = file.filename
    filepath = os.path.join('/tmp', filename)
    file.save(filepath)
    size = os.path.getsize(filepath)
    print(f"DEBUG: File saved at {filepath} size={size} mode={mode}")

    # Enforce tier limits
    if mode == 'visible' and size > 5 * 1024 * 1024:
        return jsonify({"error": "File exceeds 5MB limit for visible-only recovery"}), 400
    if mode == 'force' and size > 50 * 1024 * 1024:
        return jsonify({"error": "File exceeds 50MB limit for forced recovery"}), 400

    if mode == 'visible':
        psd = PSDImage.open(filepath)
        saved_files = save_visible_layers(psd, '/tmp/output')
        # zip visible layers
        zip_path = os.path.join(PROCESSED_DIR, f"{os.path.splitext(filename)[0]}_visible.zip")
        with zipfile.ZipFile(zip_path, "w") as z:
            for f in saved_files:
                z.write(f, os.path.basename(f))
        return send_file(zip_path, as_attachment=True)

    else:  # force mode
        zip_path = extract_layers_force_visible(filepath, '/tmp/output')
        final_zip = os.path.join(PROCESSED_DIR, f"{os.path.splitext(filename)[0]}_force.zip")
        os.replace(zip_path, final_zip)
        return send_file(final_zip, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
