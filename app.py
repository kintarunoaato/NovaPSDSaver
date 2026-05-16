from flask import Flask, request, send_file, jsonify
from psd_tools import PSDImage
import os, zipfile, tempfile
from werkzeug.utils import secure_filename
from psd_layer_extract import save_visible_layers
from psd_layer_force_visible import extract_layers_force_visible

app = Flask(__name__)

BASE_DIR = "/home/renderuser"
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    print(f"DEBUG: request.files keys: {list(request.files.keys())}")
    print(f"DEBUG: request.form: {request.form}")

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    mode = request.form.get('mode', 'visible')

    # Sanitize filename to strip any InfinityFree path
    filename = secure_filename(file.filename)

    # Save into /tmp (always exists in Render)
    filepath = os.path.join(tempfile.gettempdir(), filename)
    file.save(filepath)
    size = os.path.getsize(filepath)
    print(f"DEBUG: File saved at {filepath} size={size} mode={mode}")

    # Enforce tier limits
    if mode == 'visible' and size > 5 * 1024 * 1024:
        return jsonify({"error": "File exceeds 5MB limit"}), 400
    if mode == 'force' and size > 50 * 1024 * 1024:
        return jsonify({"error": "File exceeds 50MB limit"}), 400

    # Strip extension before appending .zip
    base_name = os.path.splitext(filename)[0]
    zip_path = os.path.join(PROCESSED_DIR, f"{base_name}.zip")
    print(f"DEBUG: Preparing to write ZIP at {zip_path}")

    # Extract layers
    if mode == 'visible':
        psd = PSDImage.open(filepath)
        files = save_visible_layers(psd)
        print(f"DEBUG: save_visible_layers returned {len(files)} files")
    else:
        files = extract_layers_force_visible(filepath)
        print(f"DEBUG: extract_layers_force_visible returned {len(files)} files")

    # Write ZIP
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for fname, data in files:
            print(f"DEBUG: Writing {fname} ({len(data)} bytes) into ZIP")
            z.writestr(fname, data)

    print(f"DEBUG: Final ZIP saved at {zip_path} size={os.path.getsize(zip_path)}")
    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
