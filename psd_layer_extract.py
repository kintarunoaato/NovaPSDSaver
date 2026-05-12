import os
import zipfile
import io
from psd_tools import PSDImage

def save_visible_layers(psd, output_folder):
    """
    Extract and save only visible layers from a PSD.
    Stream each layer directly into a ZIP to avoid memory spikes.
    Returns the path to the ZIP file.
    """
    os.makedirs(output_folder, exist_ok=True)
    zip_path = os.path.join(output_folder, "layers.zip")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for i, layer in enumerate(psd):
            if not layer.is_visible():
                print(f"DEBUG: Skipped hidden layer {i}: {layer.name}", flush=True)
                continue
            try:
                img = layer.topil()
                if img:
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="PNG")
                    safe_name = layer.name.replace(" ", "_") or f"layer_{i}"
                    z.writestr(f"{safe_name}.png", img_bytes.getvalue())
                    print(f"DEBUG: Added visible {layer.name} to ZIP", flush=True)
            except Exception as e:
                print(f"DEBUG: Error on layer {i} ({layer.name}): {e}", flush=True)

    print(f"DEBUG: Final ZIP size={os.path.getsize(zip_path)}", flush=True)
    return zip_path
