from flask import Flask, request, send_file, jsonify
from psd_tools import PSDImage
import os, zipfile, tempfile
from werkzeug.utils import secure_filename
from psd_layer_extract import save_visible_layers
from psd_layer_force_visible import extract_layers_force_visible
import smtplib
import requests
from email.mime.text import MIMEText
from PIL import Image import struct

app = Flask(__name__)

BASE_DIR = "/home/renderuser"
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

def parse_layers(data):
    """
    Minimal PSD layer parser.
    Reads header and returns a fake single-layer entry.
    Later you can expand this to walk the layer/mask info section.
    """
    # PSD header is 26 bytes: signature, version, channels, height, width, depth, color mode
    header = struct.unpack(">4sH6I", data[:26])
    signature = header[0]
    if signature != b'8BPS':
        raise ValueError("Not a valid PSD file")

    channels = header[2]
    height   = header[3]
    width    = header[4]
    depth    = header[5]
    color    = header[6]

    # For now, just return one "layer" with metadata
    return [{
        "width": width,
        "height": height,
        "channels": channels,
        "depth": depth,
        "color_mode": color,
        "raw": data
    }]

def decode_layer(layer):
    """
    Minimal decode: create a blank RGBA image sized to PSD header.
    Replace with actual channel decompression logic later.
    """
    w = layer["width"]
    h = layer["height"]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))  # transparent placeholder
    return img

def raw_salvage(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    layers = parse_layers(data)
    files = []
    for i, layer in enumerate(layers):
        img = decode_layer(layer)
        filename = f"layer_{i+1}.png"
        img.save(filename)
        files.append(filename)
    return files




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
            files = raw_salvage(filepath)
    else:
        files = extract_layers_force_visible(filepath)
        if not files:
            print("DEBUG: force mode produced no files, running raw salvage")
            files = raw_salvage(filepath)

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
