from flask import Flask, request, send_file, jsonify
from psd_tools import PSDImage
import os, zipfile, tempfile
from werkzeug.utils import secure_filename
from psd_layer_extract import save_visible_layers
from psd_layer_force_visible import extract_layers_force_visible
import smtplib
import requests
from email.mime.text import MIMEText
from PIL import Image 
import struct

app = Flask(__name__)

BASE_DIR = "/home/renderuser"
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

from PIL import Image
import io

import io
from psd_tools import PSDImage

def open_psd_raw_salvage(filepath):
    with open(filepath, "rb") as f:
        data = bytearray(f.read())

    # --- Sanitize the 26-byte header ---
    data[0:4] = b'8BPS'              # Signature
    data[4:6] = (1).to_bytes(2, "big")  # Version
    data[6:12] = b'\x00' * 6         # Reserved
    data[12:14] = (3).to_bytes(2, "big") # Channels
    data[14:18] = (1024).to_bytes(4, "big") # Height default
    data[18:22] = (1024).to_bytes(4, "big") # Width default
    data[22:24] = (8).to_bytes(2, "big")    # Depth
    data[24:26] = (3).to_bytes(2, "big")    # Color mode RGB

    return PSDImage.open(io.BytesIO(data))

def raw_salvage(filepath, mode="visible"):
    try:
        psd = open_psd_raw_salvage(filepath)
        files = []
        for i, layer in enumerate(psd):
            try:
                # Free tier: only visible layers
                if mode == "visible" and not layer.visible:
                    continue
                # Paid/force tier: salvage everything
                layer.visible = True
                img = layer.topil()
                if img:
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    safe_name = layer.name.replace(" ", "_") or f"layer{i}"
                    files.append((f"{i}_{safe_name}.png", buf.getvalue()))
            except Exception as e:
                print(f"DEBUG: Skipped layer due to error: {e}", flush=True)
        if files:
            return files
    except Exception as e:
        print(f"DEBUG: Sanitized header salvage failed: {e}", flush=True)

    # Binary brute-force fallback
    with open(filepath, "rb") as f:
        data = f.read()
    offset = 26
    raw_bytes = data[offset:]
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
    except Exception:
        img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return [("salvage.png", buf.getvalue())]

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    mode = request.form.get('mode', 'visible')
    client_email = request.form.get('email')

    filename = secure_filename(file.filename)
    filepath = os.path.join(tempfile.gettempdir(), filename)
    file.save(filepath)
    size = os.path.getsize(filepath)
    print(f"DEBUG: File saved at {filepath} size={size} mode={mode}")

    # enforce tier limits
    if mode == 'visible' and size > 5 * 1024 * 1024:
        return jsonify({"error": "File exceeds 5MB limit"}), 400
    if mode == 'force' and size > 50 * 1024 * 1024:
        return jsonify({"error": "File exceeds 50MB limit"}), 400

    base_name = os.path.splitext(filename)[0]
    zip_path = os.path.join(PROCESSED_DIR, f"{base_name}.zip")

    # ✅ always-on salvage logic
    if mode == 'visible':
        files = save_visible_layers(filepath)
        if not files:
            print("DEBUG: visible mode produced no files, running raw salvage")
            files = raw_salvage(filepath, "visible")
    else:
        files = extract_layers_force_visible(filepath)
        if not files:
            print("DEBUG: force mode produced no files, running raw salvage")
            files = raw_salvage(filepath, "force")

    # failure flag if still empty
    if not files:
        print("DEBUG: All salvage attempts failed, returning error")
        return jsonify({"error": "Unable to salvage PSD"}), 500

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for fname, data in files:
            print(f"DEBUG: Writing {fname} ({len(data)} bytes) into ZIP")
            z.writestr(fname, data)

    print(f"DEBUG: Final ZIP saved at {zip_path} size={os.path.getsize(zip_path)}")

    public_link = f"https://novapsdsaver.gt.tc/{mode}/processed/{os.path.basename(zip_path)}"

    #if client_email:
        #send_confirmation(client_email, public_link)
        #notify_sentinel("free", mode, client_email, public_link)
    #else:
        #print("DEBUG: No client email provided, skipping confirmation")

    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
