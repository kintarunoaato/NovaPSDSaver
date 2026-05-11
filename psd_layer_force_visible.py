def extract_layers_force_visible(input_path, output_folder):
    psd = PSDImage.open(input_path)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for i, layer in enumerate(psd.descendants()):
        if layer.is_group():
            continue
        original_visibility = layer.visible
        layer.visible = True
        try:
            image = layer.composite()
            if image:
                safe_name = layer.name.replace(" ", "_") or f"unnamed_{i}"
                filename = os.path.join(output_folder, f"layer_{i}_{safe_name}.png")
                image.save(filename)
        finally:
            layer.visible = original_visibility

    # Zip the folder
    zip_path = f"{output_folder}.zip"
    import shutil
    shutil.make_archive(output_folder, 'zip', output_folder)
    return zip_path
