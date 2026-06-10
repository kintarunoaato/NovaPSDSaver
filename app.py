from flask import Flask, request, send_file, jsonify
from psd_tools import PSDImage
import os, zipfile, tempfile
from werkzeug.utils import secure_filename
from psd_layer_extract import save_visible_layers
from psd_layer_force_visible import extract_layers_force_visible
import smtplib
import requests
from email.mime.text import MIMEText

app = Flask(__name__)

BASE_DIR = "/home/renderuser"
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

def raw_salvage(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    # parse header offsets manually
    layers = parse_layers(data)  # custom function
    files = []
    for i, layer in enumerate(layers):
        img = decode_layer(layer)  # decompress + convert to RGBA
        filename = f"layer_{i+1}.png"
        img.save(filename)
        files.append(filename)
    return files


def send_confirmation(to, link):
    msg = MIMEText(f"Your file has been processed. Download link: {link}")
    msg['Subject'] = "NovaPSDSaver Confirmation"
    msg['From'] = "NovaPSDSaver@gmail.com"
    msg['To'] = to

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login("NovaPSDSaver@gmail.com", os.environ.get("GMAIL_APP_PASSWORD"))
            server.sendmail("NovaPSDSaver@gmail.com", [to, "NovaPSDSaver@gmail.com"], msg.as_string())
            print(f"DEBUG: SMTP email sent to {to} and archive")
    except Exception as e:
        print(f"DEBUG: SMTP email failed. Error: {e}")

def notify_sentinel(tier, mode, client_email, file_link):
    payload = {
        "tier": tier,
        "mode": mode,
        "email": client_email,
        "link": file_link
    }
    try:
        r = requests.post("http://154.244.111.86:5000/wakeup", json=payload, timeout=10)
        print("DEBUG: Wakeup call sent to sentinel", r.status_code)
    except Exception as e:
        print("DEBUG: Failed to contact sentinel:", e)

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

    if client_email:
        send_confirmation(client_email, public_link)
        notify_sentinel("free", mode, client_email, public_link)
    else:
        print("DEBUG: No client email provided, skipping confirmation")

    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
