import os
import zipfile
import io
from psd_tools import PSDImage

def save_layer(layer, z, index_prefix=""):
    """
    Save a single layer into the ZIP, forcing visibility.
    Handles both normal layers and groups recursively.
    """
    try:
        layer.visible = True
        if layer.is_group():
            # Traverse children recursively
            for j, child in enumerate(layer):
                child_prefix = f"{index_prefix}{j}_"
                save_layer(child, z, index_prefix=child_prefix)
        else:
            img = layer.topil()
            if img:
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                safe_name = layer.name.replace(" ", "_") or f"layer{index_prefix}"
                z.writestr(f"{index_prefix}{safe_name}.png", img_bytes.getvalue())
                print(f"DEBUG: Added {layer.name} to ZIP", flush=True)
    except Exception as e:
        print(f"DEBUG: Skipped {layer.name} due to error: {e}", flush=True)

def extract_layers_force_visible(psd_path, output_folder):
    """
    Extract and save all layers from a PSD, forcing visibility.
    Recursively traverses groups. Streams each layer directly into a ZIP.
    """
    psd = PSDImage.open(psd_path)
    os.makedirs(output_folder, exist_ok=True)
    zip_path = os.path.join(output_folder, "layers.zip")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for i, layer in enumerate(psd):
            save_layer(layer, z, index_prefix=f"{i}_")

    print(f"DEBUG: Final ZIP size={os.path.getsize(zip_path)}", flush=True)
    return zip_path
