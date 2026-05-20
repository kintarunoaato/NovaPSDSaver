from flask import Flask, request, send_file, jsonify
from psd_tools import PSDImage
import os, zipfile, tempfile
from werkzeug.utils import secure_filename
from psd_layer_extract import save_visible_layers
from psd_layer_force_visible import extract_layers_force_visible
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# test smtp
import socket
try:
    socket.create_connection(("smtp.gmail.com", 587), timeout=10)
    print("DEBUG: SMTP port reachable")
except Exception as e:
    print(f"DEBUG: SMTP port unreachable: {e}")


BASE_DIR = "/home/renderuser"
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

def send_confirmation(to, link):
    msg = MIMEText(f"Your file has been processed. Download link: {link}")
    msg['Subject'] = "NovaPSDSaver Confirmation"
    msg['From'] = "NovaPSDSaver@gmail.com"
    msg['To'] = to

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login("NovaPSDSaver@gmail.com", "YOUR_APP_PASSWORD")  # 🔑 Gmail App Password
            server.sendmail("NovaPSDSaver@gmail.com", [to, "NovaPSDSaver@gmail.com"], msg.as_string())
            print(f"DEBUG: SMTP email sent to {to} and archive")
    except Exception as e:
        print(f"DEBUG: SMTP email failed. Error: {e}")

@app.route('/upload', methods=['POST'])
def upload_file():
    print(f"DEBUG: request.files keys: {list(request.files.keys())}")
    print(f"DEBUG: request.form: {request.form}")

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    mode = request.form.get('mode', 'visible')
    client_email = request.form.get('email')  # 🔑 receive client email

    filename = secure_filename(file.filename)
    filepath = os.path.join(tempfile.gettempdir(), filename)
    file.save(filepath)
    size = os.path.getsize(filepath)
    print(f"DEBUG: File saved at {filepath} size={size} mode={mode}")

    if mode == 'visible' and size > 5 * 1024 * 1024:
        return jsonify({"error": "File exceeds 5MB limit"}), 400
    if mode == 'force' and size > 50 * 1024 * 1024:
        return jsonify({"error": "File exceeds 50MB limit"}), 400

    base_name = os.path.splitext(filename)[0]
    zip_path = os.path.join(PROCESSED_DIR, f"{base_name}.zip")
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

    # 🔑 Send confirmation email
    if client_email:
        public_link = f"https://novapsdsaver.gt.tc/{mode}/processed/{os.path.basename(zip_path)}"
        send_confirmation(client_email, public_link)
    else:
        print("DEBUG: No client email provided, skipping confirmation")

    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
