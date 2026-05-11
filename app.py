import logging, sys
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(sys.stdout)]
)

from flask import Flask, request, send_file, jsonify
import os

# your custom helpers
from psd_layer_extract import extract_layers
from psd_layer_force_visible import extract_layers_force_visible

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 35 * 1024 * 1024  # 35 MB cap

@app.route("/")
def index():
    return "NovaPSDSaver backend is alive!"

@app.route("/upload", methods=["POST"])
def upload_psd():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    filepath = os.path.join("/tmp", file.filename)
    file.save(filepath)
    size = os.path.getsize(filepath)

    output_folder = os.path.join("/tmp", file.filename.split('.')[0])

    if size < 5 * 1024 * 1024:
        # Free tier: only visible layers
        zip_path = extract_layers(filepath, output_folder)
        return send_file(zip_path, as_attachment=True)
    elif size <= 35 * 1024 * 1024:
        # Standard tier: all layers (force visible)
        zip_path = extract_layers_force_visible(filepath, output_folder)
        return send_file(zip_path, as_attachment=True)
    else:
        return jsonify({"error": "Premium tier (>35 MB) coming soon"}), 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
