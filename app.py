from flask import Flask, request, send_file, jsonify
from psd_tools import PSDImage
import os, zipfile
from psd_layer_extract import save_visible_layers
from psd_layer_force_visible import extract_layers_force_visible

app = Flask(__name__)

BASE_DIR = "/home/renderuser"
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.route('/upload', methods=['POST'])
print(f"DEBUG: request.files keys: {list(request.files.keys())}")
print(f"DEBUG: request.form: {request.form}")

def upload_file():
    file = request.files['file']
    mode = request.form.get('mode', 'visible')
    filename = file.filename
    filepath = os.path.join('/tmp', filename)
    file.save(filepath)
    size = os.path.getsize(filepath)
    print(f"DEBUG: File saved at {filepath} size={size} mode={mode}")

    if mode == 'visible' and size > 5 * 1024 * 1024:
        return jsonify({"error": "File exceeds 5MB limit"}), 400
    if mode == 'force' and size > 50 * 1024 * 1024:
        return jsonify({"error": "File exceeds 50MB limit"}), 400

    zip_path = os.path.join(PROCESSED_DIR, f"{os.path.splitext(filename)[0]}.zip")
    print(f"DEBUG: Preparing to write ZIP at {zip_path}")

    if mode == 'visible':
        psd = PSDImage.open(filepath)
        files = save_visible_layers(psd)
        print(f"DEBUG: save_visible_layers returned {len(files)} files")
    else:
        files = extract_layers_force_visible(filepath)
        print(f"DEBUG: extract_layers_force_visible returned {len(files)} files")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for fname, data in files:
            print(f"DEBUG: Writing {fname} ({len(data)} bytes) into ZIP")
            z.writestr(fname, data)

    print(f"DEBUG: Final ZIP saved at {zip_path} size={os.path.getsize(zip_path)}")
    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
