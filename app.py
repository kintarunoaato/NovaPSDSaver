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

# Full PSD header map: field name → (start, end, safe default)
HEADER_FIELDS = {
    "Signature":  (0, 4, b"8BPS"),
    "Version":    (4, 6, (1).to_bytes(2, "big")),
    "Reserved":   (6, 12, b"\x00" * 6),
    "Channels":   (12, 14, (3).to_bytes(2, "big")),
    "Height":     (14, 18, (1024).to_bytes(4, "big")),
    "Width":      (18, 22, (1024).to_bytes(4, "big")),
    "Depth":      (22, 24, (8).to_bytes(2, "big")),
    "ColorMode":  (24, 26, (3).to_bytes(2, "big")),  # RGB
}

def open_psd_raw_salvage(filepath, bad_field=None):
    with open(filepath, "rb") as f:
        data = bytearray(f.read())

    # Patch only the failing field
    if bad_field and bad_field in HEADER_FIELDS:
        start, end, safe_val = HEADER_FIELDS[bad_field]
        data[start:end] = safe_val
        print(f"DEBUG: Patched {bad_field} field in header")

    return PSDImage.open(io.BytesIO(data))

def raw_salvage(filepath, mode="visible", bad_field=None):
    try:
        psd = None
        patched = set()

        while True:
            try:
                if bad_field:
                    psd = open_psd_raw_salvage(filepath, bad_field)
                else:
                    psd = PSDImage.open(filepath)
                break  # success
            except Exception as e:
                msg = str(e)
                print(f"DEBUG: Parse failed: {msg}")
                new_bad = None
                if "ColorMode" in msg:
                    new_bad = "ColorMode"
                elif "Depth" in msg:
                    new_bad = "Depth"
                elif "Channels" in msg:
                    new_bad = "Channels"
                elif "Signature" in msg:
                    new_bad = "Signature"
                elif "Version" in msg:
                    new_bad = "Version"
                elif "Height" in msg:
                    new_bad = "Height"
                elif "Width" in msg:
                    new_bad = "Width"
                elif "Reserved" in msg:
                    new_bad = "Reserved"

                if new_bad and new_bad not in patched:
                    patched.add(new_bad)
                    bad_field = new_bad
                    continue  # retry with new patch
                else:
                    print("DEBUG: No more salvageable header fields")
                    psd = None
                    break

        if psd:
            files = []
            for i, layer in enumerate(psd):
                try:
                    if mode == "visible" and not layer.visible:
                        continue
                    layer.visible = True
                    img = layer.topil()
                    if img:
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        safe_name = (layer.name or f"layer{i}").replace(" ", "_")
                        files.append((f"{i}_{safe_name}.png", buf.getvalue()))
                except Exception as e:
                    print(f"DEBUG: Skipped layer due to error: {e}", flush=True)

            if files:
                return files
    except Exception as e:
        print(f"DEBUG: Targeted header salvage failed: {e}", flush=True)

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
