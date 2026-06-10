from flask import Flask, request, send_file, jsonify
from psd_tools import PSDImage
import io, os, zipfile, tempfile
from werkzeug.utils import secure_filename
from psd_layer_extract import save_visible_layers
from psd_layer_force_visible import extract_layers_force_visible
import smtplib
from psd_tools import PSDImage
import requests
from email.mime.text import MIMEText
from PIL import Image 
import struct

app = Flask(__name__)

BASE_DIR = "/home/renderuser"
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

import io
from psd_tools import PSDImage
from PIL import Image

# Canonical header fields with safe defaults
HEADER_FIELDS = [
    ("Signature", 0, 4, b"8BPS", lambda v: v == b"8BPS"),
    ("Version", 4, 6, (1).to_bytes(2, "big"), lambda v: v in (1, 2)),
    ("Reserved", 6, 12, b"\x00" * 6, lambda v: v == 0),
    ("Channels", 12, 14, (3).to_bytes(2, "big"), lambda v: 1 <= v <= 56),
    ("Height", 14, 18, (2048).to_bytes(4, "big"), lambda v: v > 0),
    ("Width", 18, 22, (2048).to_bytes(4, "big"), lambda v: v > 0),
    ("Depth", 22, 24, (8).to_bytes(2, "big"), lambda v: v in (1, 8, 16, 32)),
    ("ColorMode", 24, 26, (3).to_bytes(2, "big"), lambda v: v in (0,1,2,3,4,7,8,9)),
]

def open_psd_raw_salvage(filepath, bad_field=None):
    """Sanitize header, patch bad_field + validate others."""
    with open(filepath, "rb") as f:
        data = bytearray(f.read())

    corrupt_header = {}
    for name, start, end, safe_val, validator in HEADER_FIELDS:
        raw = data[start:end]
        val = raw if name == "Signature" else int.from_bytes(raw, "big")
        corrupt_header[name] = val

        if name == bad_field:
            print(f"DEBUG: {name} flagged, patched regardless ({val})")
            data[start:end] = safe_val
            continue

        if not validator(val):
            print(f"DEBUG: {name} invalid ({val}), patched to default")
            data[start:end] = safe_val

    return data, corrupt_header

def universal_header():
    """Return a 26-byte universal fallback header (2048x2048 RGB)."""
    header = bytearray(26)
    header[0:4] = b"8BPS"
    header[4:6] = (1).to_bytes(2, "big")
    header[6:12] = b"\x00" * 6
    header[12:14] = (3).to_bytes(2, "big")
    header[14:18] = (2048).to_bytes(4, "big")
    header[18:22] = (2048).to_bytes(4, "big")
    header[22:24] = (8).to_bytes(2, "big")
    header[24:26] = (3).to_bytes(2, "big")
    return header
    
def apply_sanitized_header(filepath, sanitized_header):
    with open(filepath, "rb") as f:
        data = f.read()
    new_data = sanitized_header + data[26:]
    tmp_path = filepath + ".sanitized"
    with open(tmp_path, "wb") as f:
        f.write(new_data)
    return tmp_path
    
def parse_field_from_exception(msg):
    """Extract field name directly from exception string."""
    for name, _, _, _, _ in HEADER_FIELDS:
        if name in msg:
            return name
    return None

def raw_salvage(filepath, mode, bad_field=None):
    attempt = 0
    files = None

    while True:
        attempt += 1
        print(f"=== Attempt {attempt}, patching {bad_field} ===")

        sanitized, corrupt_header = open_psd_raw_salvage(filepath, bad_field)
        tmp_path = apply_sanitized_header(filepath, sanitized)

        try:
            psd = PSDImage.open(tmp_path)
            print("SUCCESS: PSD parsed")
            if mode == "visible":
                files = save_visible_layers(psd)
            else:
                files = extract_layers_force_visible(psd)
            return files
        except Exception as e:
            msg = str(e)
            print(f"Wall hit: {msg}")
            bad_field = parse_field_from_exception(msg)
            if not bad_field:
                print("No more salvageable fields, breaking")
                break

    print("Applying universal 2048x2048 header fallback")
    tmp_path = apply_sanitized_header(filepath, universal_header())

    try:
        psd = PSDImage.open(tmp_path)
        if mode == "visible":
            return save_visible_layers(psd)
        else:
            return extract_layers_force_visible(psd)
    except:
        print("Brute-forcing binary fragments...")
        with open(filepath, "rb") as f:
            data = f.read()

        offset = 26
        fragments = []
        idx = 0
        step = 4096

        while offset < len(data):
            chunk = data[offset:offset+step]
            try:
                img = Image.open(io.BytesIO(chunk)).convert("RGBA")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                fragments.append((f"fragment_{idx}.png", buf.getvalue()))
                print(f"DEBUG: salvaged fragment {idx} at offset {offset}")
                idx += 1
            except Exception:
                pass
            offset += step

        return fragments




# --- Flask route ---
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

    files, bad_field = None, None

    # ✅ always-on salvage logic
    if mode == 'visible':
        result = save_visible_layers(filepath)
        if isinstance(result, dict):
            bad_field = result.get("bad_field")
        else:
            files = result
    else:
        result = extract_layers_force_visible(filepath)
        if isinstance(result, dict):
            bad_field = result.get("bad_field")
        else:
            files = result

    # targeted salvage if helpers forwarded bad_field
    if not files:
        files = raw_salvage(filepath, mode, bad_field)

    # failure flag if still empty
    if not files:
        print("DEBUG: All salvage attempts failed, returning error")
        return jsonify({"error": "Unable to salvage PSD"}), 500

    # write ZIP
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for fname, data in files:
            print(f"DEBUG: Writing {fname} ({len(data)} bytes) into ZIP")
            z.writestr(fname, data)

    print(f"DEBUG: Final ZIP saved at {zip_path} size={os.path.getsize(zip_path)}")

    public_link = f"https://novapsdsaver.gt.tc/{mode}/processed/{os.path.basename(zip_path)}"

    # optional email notifications (disabled for now)
    # if client_email:
    #     send_confirmation(client_email, public_link)
    #     notify_sentinel("free", mode, client_email, public_link)
    # else:
    #     print("DEBUG: No client email provided, skipping confirmation")

    return send_file(zip_path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
