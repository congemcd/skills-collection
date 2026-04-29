---
name: batch-image-compressor
description: Compress JPEG and PNG images in a directory without changing resolution or format using jpegoptim and pngquant. Use when the user wants to reduce image file sizes in a directory.
---

# Batch Image Compressor

This skill compresses JPEG and PNG images in a directory without changing their resolution or format. It uses `jpegoptim` and `pngquant` CLI tools to achieve high compression with excellent quality preservation. `pngquant` provides massive file size reductions for PNGs by intelligently reducing the number of colors while keeping visual differences nearly imperceptible.

## Workflow

1.  **Check Dependencies:** Before doing anything else, check if `jpegoptim` and `pngquant` are installed by running `which jpegoptim` and `which pngquant`. If either tool is missing, explicitly explain to the user *why* they are needed (to perform the high-quality, resolution-preserving compression) and directly execute the command to install them via Homebrew (`brew install jpegoptim pngquant`). Do not wait for the user to do it manually.
2.  **Analyze Directory:** Locate all `.jpg`, `.jpeg`, and `.png` files in the target directory (defaulting to the current working directory). Calculate the total size of these images before compression. Inform the user how many images were found and the total starting size.
3.  **Determine Naming/Overwrite Rules:** Do NOT directly compress and overwrite original images unless the user explicitly states to do so. If the user does not specify a naming rule, create new images and add a "compressed-" prefix to their filenames (e.g., `compressed-image.jpg`). If the user does not specify an output directory, output the new compressed images in the same directory as the original images.
4.  **Compress JPEGs:** For each `.jpg` and `.jpeg` file found:
    * If preserving originals, copy the file first (e.g., `cp "img.jpg" "compressed-img.jpg"`) and then execute `jpegoptim -m80 --strip-all "compressed-img.jpg"`.
    * If overwriting, execute `jpegoptim -m80 --strip-all "<file>"`.
5.  **Compress PNGs:** For each `.png` file found:
    * If preserving originals, execute `pngquant --output "compressed-img.png" "img.png"`.
    * If overwriting, execute `pngquant --ext .png --force "<file>"`.
6.  **Summary Report:** After all images are processed, calculate the new total size of the compressed images. Report the original total size, the new total size, and the total space saved in a concise summary.