import os
import zipfile
import io
from psd_tools import PSDImage

def extract_layers_force_visible(psd_path, output_folder):
    """
    Extract and save all layers from a PSD, forcing visibility.
    Stream each layer directly into a ZIP to avoid memory spikes.
    Returns the path to the ZIP file.
    """
    psd = PSDImage.open(psd_path)
    os.makedirs(output_folder, exist_ok=True)
    zip_path = os.path.join(output_folder, "layers.zip")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for i, layer in enumerate(psd):
            try:
                layer.visible = True
                img = layer.topil()
                if img:
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="PNG")
                    safe_name = layer.name.replace(" ", "_") or f"layer_{i}"
                    z.writestr(f"layer_{i}_{safe_name}.png", img_bytes.getvalue())
                    print(f"DEBUG: Added {layer.name} to ZIP", flush=True)
            except Exception as e:
                print(f"DEBUG: Skipped layer {i} ({layer.name}) due to error: {e}", flush=True)

    print(f"DEBUG: Final ZIP size={os.path.getsize(zip_path)}", flush=True)
    return zip_path
