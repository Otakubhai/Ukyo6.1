#!/usr/bin/env python3
"""
Helper functions for the bot.
Includes utility functions used across the application.
"""

import os
import shutil
import logging

logger = logging.getLogger(__name__)

def cleanup_temp_folder(folder_path):
    """
    Removes a temporary folder and its contents.

    Args:
        folder_path (str): Path to the folder to remove.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"Cleaned up temporary folder: {folder_path}")
            return True
    except Exception as e:
        logger.error(f"Error cleaning up folder {folder_path}: {e}")
        return False
