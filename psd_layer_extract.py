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

def detect_bad_field(msg: str):
    if "ColorMode" in msg:
        return "ColorMode"
    elif "Depth" in msg:
        return "Depth"
    elif "Channels" in msg:
        return "Channels"
    elif "Signature" in msg:
        return "Signature"
    elif "Version" in msg:
        return "Version"
    elif "Height" in msg:
        return "Height"
    elif "Width" in msg:
        return "Width"
    elif "Reserved" in msg:
        return "Reserved"
    return None

def save_visible_layers(filepath):
    output_files = []
    try:
        # Try strict parse first
        psd = PSDImage.open(filepath)
        for i, layer in enumerate(psd):
            save_visible_layer(layer, output_files, index_prefix=f"{i}_")
        print(f"DEBUG: save_visible_layers collected {len(output_files)} files")
        return output_files
    except Exception as e:
        msg = str(e)
        print(f"DEBUG: PSD parse failed: {msg}, retrying with salvage-visible mode")
        bad_field = detect_bad_field(msg)
        try:
            # Retry with strict=False to tolerate corruption
            psd = PSDImage.open(filepath, strict=False)
            for i, layer in enumerate(psd):
                save_visible_layer(layer, output_files, index_prefix=f"{i}_")
            print(f"DEBUG: salvage-visible collected {len(output_files)} files")
            return output_files
        except Exception as e2:
            msg2 = str(e2)
            print(f"DEBUG: salvage-visible also failed: {msg2}")
            bad_field2 = detect_bad_field(msg2)
            # Forward the bad_field info if we detected it
            if bad_field or bad_field2:
                return {"bad_field": bad_field or bad_field2}
    return output_files if output_files else None
