from flask import Flask, request, send_file, jsonify
import os
from psd_layer_extract import extract_layers
from psd_layer_force_visible import extract_layers_force_visible

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 35 * 1024 * 1024  # 35 MB cap

@app.route('/upload', methods=['POST'])
def upload_psd():
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({"error": "No file uploaded"}), 400

    filepath = os.path.join("/tmp", file.filename)
    file.save(filepath)
    size = os.path.getsize(filepath)

    output_folder = os.path.join("/tmp", file.filename.split('.')[0])

    if size < 5 * 1024 * 1024:
        zip_path = extract_layers(filepath, output_folder)
        return send_file(zip_path, as_attachment=True)
    elif size <= 35 * 1024 * 1024:
        zip_path = extract_layers_force_visible(filepath, output_folder)
        return send_file(zip_path, as_attachment=True)
    else:
        return jsonify({"error": "Premium tier (>35 MB) coming soon"}), 403
from flask import Flask

app = Flask(__name__)

# --- your existing routes here ---

# Now add the upload logic below:
from flask import request, send_file, abort
import psd_tools, zipfile, io

MAX_SIZE = 35 * 1024 * 1024  # 35 MB

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    data = file.read()
    if len(data) > MAX_SIZE:
        abort(413, "File too large (>35MB)")
    file.seek(0)
    psd = psd_tools.PSDImage.open(file)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i, layer in enumerate(psd):
            z.writestr(f"layer_{i}.png", layer.topil().tobytes())
    buf.seek(0)

    return send_file(buf, mimetype="application/zip",
                     as_attachment=True, download_name="layers.zip")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
