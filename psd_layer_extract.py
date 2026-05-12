import os
import zipfile
import io
from psd_tools import PSDImage

def save_visible_layer(layer, z, index_prefix=""):
    """
    Save a single layer into the ZIP if visible.
    Recursively traverses groups.
    """
    try:
        if layer.is_group():
            # Traverse children recursively
            for j, child in enumerate(layer):
                child_prefix = f"{index_prefix}{j}_"
                save_visible_layer(child, z, index_prefix=child_prefix)
        else:
            if layer.is_visible():
                img = layer.topil()
                if img:
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="PNG")
                    safe_name = layer.name.replace(" ", "_") or f"layer{index_prefix}"
                    z.writestr(f"{index_prefix}{safe_name}.png", img_bytes.getvalue())
                    print(f"DEBUG: Added visible {layer.name} to ZIP", flush=True)
            else:
                print(f"DEBUG: Skipped hidden {layer.name}", flush=True)
    except Exception as e:
        print(f"DEBUG: Error on {layer.name}: {e}", flush=True)

def save_visible_layers(psd, output_folder):
    """
    Extract and save only visible layers from a PSD.
    Recursively traverses groups. Streams each layer directly into a ZIP.
    """
    os.makedirs(output_folder, exist_ok=True)
    zip_path = os.path.join(output_folder, "layers.zip")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for i, layer in enumerate(psd):
            save_visible_layer(layer, z, index_prefix=f"{i}_")

    print(f"DEBUG: Final ZIP size={os.path.getsize(zip_path)}", flush=True)
    return zip_path
