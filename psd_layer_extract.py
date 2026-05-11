# helpers.py
import os

def extract_active_layers(psd, output_folder):
    """
    Extract only active (visible) layers from a PSD.
    Saves them as PNGs in output_folder.
    Returns list of saved file paths.
    """
    saved_files = []
    for i, layer in enumerate(psd):
        if not layer.is_visible():
            continue
        image = layer.topil()
        if image:
            filename = os.path.join(output_folder, f"layer_{i}_{layer.name}.png")
            image.save(filename)
            saved_files.append(filename)
            print(f"Saved active layer: {filename}", flush=True)
    return saved_files
