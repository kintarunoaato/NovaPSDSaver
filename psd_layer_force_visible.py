import os
import zipfile
import io
from psd_tools import PSDImage

def save_force_visible_layers(psd_path, output_folder):
    """
    Extract all layers from a PSD by forcing visibility.
    Saves them into a ZIP archive in output_folder.
    Returns the path to the ZIP file.
    """
    psd = PSDImage.open(psd_path)
    zip_path = os.path.join(output_folder, "layers.zip")
    os.makedirs(output_folder, exist_ok=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i, layer in enumerate(psd):
            # Force visibility before extraction
            print(f"DEBUG: Layer {i}: {layer.name}, forced visible")
            layer.visible = True
            img = layer.topil()
            if img is None:
                continue
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            z.writestr(f"layer_{i}_{layer.name or 'unnamed'}.png", img_bytes.getvalue())

    buf.seek(0)
    with open(zip_path, "wb") as f:
        f.write(buf.getvalue())

    return zip_path
