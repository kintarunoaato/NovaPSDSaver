import io
from psd_tools import PSDImage

def save_visible_layer(layer, output_files, index_prefix=""):
    try:
        if layer.is_group():
            for j, child in enumerate(layer):
                child_prefix = f"{index_prefix}{j}_"
                save_visible_layer(child, output_files, index_prefix=child_prefix)
        else:
            if getattr(layer, "is_visible", lambda: False)():
                img = getattr(layer, "topil", lambda: None)()
                if img:
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="PNG")
                    safe_name = (layer.name or f"layer{index_prefix}").replace(" ", "_")
                    output_files.append((f"{index_prefix}{safe_name}.png", img_bytes.getvalue()))
                    print(f"DEBUG: Added visible {layer.name}", flush=True)
            else:
                print(f"DEBUG: Skipped hidden {getattr(layer, 'name', 'unknown')}", flush=True)
    except Exception as e:
        print(f"DEBUG: Error on {getattr(layer, 'name', 'unknown')}: {e}", flush=True)

def save_visible_layers(filepath):
    output_files = []
    try:
        # Try strict parse first
        psd = PSDImage.open(filepath)
        for i, layer in enumerate(psd):
            save_visible_layer(layer, output_files, index_prefix=f"{i}_")
        print(f"DEBUG: save_visible_layers collected {len(output_files)} files")
    except Exception as e:
        print(f"DEBUG: PSD parse failed: {e}, retrying with salvage-visible mode")
        try:
            # Retry with strict=False to tolerate corruption
            psd = PSDImage.open(filepath, strict=False)
            for i, layer in enumerate(psd):
                save_visible_layer(layer, output_files, index_prefix=f"{i}_")
            print(f"DEBUG: salvage-visible collected {len(output_files)} files")
        except Exception as e2:
            print(f"DEBUG: salvage-visible also failed: {e2}")
    return output_files
