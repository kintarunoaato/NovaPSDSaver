import io
from psd_tools import PSDImage

def save_layer(layer, output_files, index_prefix=""):
    try:
        layer.visible = True
        if layer.is_group():
            for j, child in enumerate(layer):
                child_prefix = f"{index_prefix}{j}_"
                save_layer(child, output_files, index_prefix=child_prefix)
        else:
            img = getattr(layer, "topil", lambda: None)()
            if img:
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                safe_name = (layer.name or f"layer{index_prefix}").replace(" ", "_")
                output_files.append((f"{index_prefix}{safe_name}.png", img_bytes.getvalue()))
                print(f"DEBUG: Added {layer.name}", flush=True)
    except Exception as e:
        print(f"DEBUG: Skipped {getattr(layer, 'name', 'unknown')} due to error: {e}", flush=True)

def extract_layers_force_visible(filepath):
    output_files = []
    try:
        # First attempt strict parse
        psd = PSDImage.open(filepath)
        for i, layer in enumerate(psd):
            save_layer(layer, output_files, index_prefix=f"{i}_")
        print(f"DEBUG: force-visible collected {len(output_files)} files")
    except Exception as e:
        print(f"DEBUG: PSD parse failed in force mode: {e}, retrying with salvage-force mode")
        try:
            # Retry with strict=False to tolerate corruption
            psd = PSDImage.open(filepath, strict=False)
            for i, layer in enumerate(psd):
                save_layer(layer, output_files, index_prefix=f"{i}_")
            print(f"DEBUG: salvage-force collected {len(output_files)} files")
        except Exception as e2:
            print(f"DEBUG: salvage-force also failed: {e2}")
            raise  # let caller catch and run raw_salvage
    return output_files
