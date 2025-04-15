#!/usr/bin/env python3
"""
PDF Generator module.
Creates PDFs from a collection of images.
"""

import os
import logging
from PIL import Image

logger = logging.getLogger(__name__)

def create_pdf_from_images(folder_path, output_pdf_path):
    """
    Creates a PDF from images in a folder.

    Args:
        folder_path (str): Path to the folder containing images.
        output_pdf_path (str): Path to save the generated PDF.

    Returns:
        str: Path to the generated PDF.

    Raises:
        Exception: If no valid images are found in the folder.
    """
    try:
        # Get all image files in the folder and sort them numerically
        image_files = []
        for filename in os.listdir(folder_path):
            if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                try:
                    # Extract the numeric part of the filename (assuming filenames like 1.jpg, 2.png, etc.)
                    name_without_ext = os.path.splitext(filename)[0]
                    if name_without_ext.isdigit():
                        image_files.append((int(name_without_ext), filename))
                    else:
                        # If filename is not a plain number, just add it with a high index
                        image_files.append((999999, filename))
                except Exception:
                    # Fallback for any unexpected filename format
                    image_files.append((999999, filename))
        
        # Sort by the numeric part
        image_files.sort()
        
        # Extract just the filenames after sorting
        image_files = [file[1] for file in image_files]
        
        if not image_files:
            raise Exception("No valid images found in folder.")
        
        logger.info(f"Creating PDF from {len(image_files)} images")
        
        # Open all images and convert to RGB mode for PDF compatibility
        image_list = []
        for filename in image_files:
            image_path = os.path.join(folder_path, filename)
            try:
                img = Image.open(image_path)
                
                # Convert to RGB mode (required for PDF)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                image_list.append(img)
            except Exception as e:
                logger.error(f"Error processing image {filename}: {e}")
        
        if not image_list:
            raise Exception("None of the images could be processed.")
        
        # Save the images as a PDF
        image_list[0].save(
            output_pdf_path,
            save_all=True,
            append_images=image_list[1:],
            optimize=True,
            quality=85  # Balance between quality and file size
        )
        
        logger.info(f"PDF created successfully at {output_pdf_path}")
        return output_pdf_path
        
    except Exception as e:
        logger.error(f"Error creating PDF: {e}")
        raise
