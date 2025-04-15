#!/usr/bin/env python3
"""
Image handler module.
Handles image scraping and downloading from multporn.net.
"""

import os
import logging
import requests
import tempfile
import asyncio
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def scrape_images(url):
    """
    Scrapes image URLs from a given URL.

    Args:
        url (str): The URL to scrape images from.

    Returns:
        tuple: A tuple containing a list of image URLs and an error message (if any).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return None, f"Failed to fetch the page. Status code: {response.status_code}"

        soup = BeautifulSoup(response.text, "html.parser")
        
        # First look for comic images specifically
        comic_images = soup.select(".comic-content img")
        if comic_images:
            image_urls = []
            for img in comic_images:
                src = img.get("src") or img.get("data-src")
                if src:
                    image_urls.append(src if src.startswith("http") else f"https://multporn.net{src}")
            return image_urls, None
        
        # If no comic images found, try general image search
        image_tags = soup.find_all("img")
        image_urls = []
        for img in image_tags:
            src = img.get("src") or img.get("data-src")
            if src and any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".gif"]):
                # Skip tiny images and icons
                if "icon" not in src.lower() and "logo" not in src.lower():
                    image_urls.append(src if src.startswith("http") else f"https://multporn.net{src}")
        
        if not image_urls:
            return None, "No images found."
            
        return image_urls, None
        
    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        return None, f"Network error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in scrape_images: {e}")
        return None, f"Error: {str(e)}"

def download_image(url, folder, index):
    """
    Downloads an image from a URL and saves it to the specified folder.

    Args:
        url (str): The URL of the image to download.
        folder (str): The folder to save the image to.
        index (int): The index number for the filename.

    Returns:
        str: The path to the downloaded image file or None if failed.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        if response.status_code != 200:
            logger.error(f"Failed to download image {url}. Status code: {response.status_code}")
            return None
            
        # Determine the file extension
        content_type = response.headers.get('Content-Type', '')
        if 'image/jpeg' in content_type or 'image/jpg' in content_type:
            ext = '.jpg'
        elif 'image/png' in content_type:
            ext = '.png'
        elif 'image/gif' in content_type:
            ext = '.gif'
        else:
            # Try to get extension from URL if content-type is not helpful
            if '.png' in url.lower():
                ext = '.png'
            elif '.gif' in url.lower():
                ext = '.gif'
            else:
                ext = '.jpg'  # Default to jpg
                
        # Create the output filename
        filename = os.path.join(folder, f"{index}{ext}")
        
        # Save the image
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    
        return filename
        
    except requests.RequestException as e:
        logger.error(f"Request error downloading {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}")
        return None

async def download_images(image_urls, folder):
    """
    Downloads a list of images asynchronously.
    
    Args:
        image_urls (list): List of image URLs to download.
        folder (str): Folder to save the images to.
        
    Returns:
        list: List of paths to the downloaded images.
    """
    os.makedirs(folder, exist_ok=True)
    
    downloaded_paths = []
    for idx, url in enumerate(image_urls, start=1):
        # We're using a synchronous download function but handling them 
        # concurrently would require more complex setup
        path = download_image(url, folder, idx)
        if path:
            downloaded_paths.append(path)
        
        # Small delay to avoid overloading the server
        await asyncio.sleep(0.5)
        
    return downloaded_paths
