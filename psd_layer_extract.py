import os

def save_visible_layers(psd, output_folder):
    """
    Extract and save only visible layers from a PSD.
    Returns list of saved file paths.
    """
    saved_files = []
    for i, layer in enumerate(psd):
        if not layer.is_visible():
            continue
        image = layer.topil()
        if image:
            safe_name = layer.name.replace(" ", "_") or f"layer_{i}"
            filename = os.path.join(output_folder, f"{safe_name}.png")
            image.save(filename)
            saved_files.append(filename)
            print(f"DEBUG: Saved visible layer {layer.name} -> {filename}", flush=True)
    return saved_files
