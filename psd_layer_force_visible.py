import os
import zipfile
import io
from psd_tools import PSDImage

def extract_layers_force_visible(psd_path, output_folder):
    psd = PSDImage.open(psd_path)
    os.makedirs(output_folder, exist_ok=True)
    zip_path = os.path.join(output_folder, "layers.zip")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i, layer in enumerate(psd):
            try:
                layer.visible = True
                img = layer.topil()
                if img:
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="PNG")
                    z.writestr(f"layer_{i}_{layer.name or 'unnamed'}.png", img_bytes.getvalue())
                    print(f"DEBUG: Added {layer.name} to ZIP")
            except Exception as e:
                print(f"DEBUG: Skipped layer {i} ({layer.name}) due to error: {e}")

    buf.seek(0)
    with open(zip_path, "wb") as f:
        f.write(buf.getvalue())

    print(f"DEBUG: Final ZIP size={os.path.getsize(zip_path)}")
    return zip_path

