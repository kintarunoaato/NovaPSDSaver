def extract_layers(input_path, output_folder):
    psd = PSDImage.open(input_path)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for i, layer in enumerate(psd.descendants()):
        if layer.is_group():
            continue
        if layer.visible:
            image = layer.composite()
            if image:
                filename = os.path.join(output_folder, f"layer_{i}_{layer.name}.png")
                image.save(filename)

    # Zip the folder
    zip_path = f"{output_folder}.zip"
    import shutil
    shutil.make_archive(output_folder, 'zip', output_folder)
    return zip_path
