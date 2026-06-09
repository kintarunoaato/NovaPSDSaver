import io
from psd_tools import PSDImage
from psd_layer_force_visible import extract_layers_force_visible

def save_visible_layer(layer, output_files, index_prefix=""):
    try:
        if layer.is_group():
            for j, child in enumerate(layer):
                child_prefix = f"{index_prefix}{j}_"
                save_visible_layer(child, output_files, index_prefix=child_prefix)
        else:
            if layer.is_visible():
                img = layer.topil()
                if img:
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="PNG")
                    safe_name = layer.name.replace(" ", "_") or f"layer{index_prefix}"
                    output_files.append((f"{index_prefix}{safe_name}.png", img_bytes.getvalue()))
                    print(f"DEBUG: Added visible {layer.name}", flush=True)
            else:
                print(f"DEBUG: Skipped hidden {layer.name}", flush=True)
    except Exception as e:
        print(f"DEBUG: Error on {getattr(layer, 'name', 'unknown')}: {e}", flush=True)

def save_visible_layers(filepath):
    output_files = []
    try:
        psd = PSDImage.open(filepath)
        for i, layer in enumerate(psd):
            save_visible_layer(layer, output_files, index_prefix=f"{i}_")
        print(f"DEBUG: save_visible_layers collected {len(output_files)} files")
    except Exception as e:
        print(f"DEBUG: PSD parse failed: {e}, switching to force salvage")
        # Fallback: force salvage mode
        output_files = extract_layers_force_visible(filepath)
        print(f"DEBUG: force salvage returned {len(output_files)} files")
    return output_files
