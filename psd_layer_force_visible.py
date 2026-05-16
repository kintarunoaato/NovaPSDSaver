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
            img = layer.topil()
            if img:
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                safe_name = layer.name.replace(" ", "_") or f"layer{index_prefix}"
                output_files.append((f"{index_prefix}{safe_name}.png", img_bytes.getvalue()))
                print(f"DEBUG: Added {layer.name}", flush=True)
    except Exception as e:
        print(f"DEBUG: Skipped {layer.name} due to error: {e}", flush=True)

def extract_layers_force_visible(psd_path):
    psd = PSDImage.open(psd_path)
    output_files = []
    for i, layer in enumerate(psd):
        save_layer(layer, output_files, index_prefix=f"{i}_")
    print(f"DEBUG: extract_layers_force_visible collected {len(output_files)} files")
    return output_files
