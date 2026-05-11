from psd_tools import PSDImage
import os, zipfile, io

def extract_layers_force_visible(psd_path, output_folder):
    psd = PSDImage.open(psd_path)
    zip_path = os.path.join(output_folder, "layers.zip")
    os.makedirs(output_folder, exist_ok=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i, layer in enumerate(psd):
            # Force visibility before extraction
            layer.visible = True
            img = layer.topil()
            if img is None:
                continue
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            z.writestr(f"layer_{i}.png", img_bytes.getvalue())

    buf.seek(0)
    with open(zip_path, "wb") as f:
        f.write(buf.getvalue())
    return zip_path
