#!/usr/bin/env python3
"""
Anime information fetcher module.
Fetches anime information from AniList GraphQL API.
"""

import logging
import aiohttp

logger = logging.getLogger(__name__)

async def fetch_anime_info(anime_name):
    """
    Fetches anime details from AniList API.

    Args:
        anime_name (str): The name of the anime to search for.

    Returns:
        dict: Anime details from AniList API or None if not found.
    """
    url = "https://graphql.anilist.co/"
    query = """
    query ($search: String) {
        Media(search: $search, type: ANIME) {
            id
            title {
                romaji
                english
            }
            episodes
            genres
            coverImage {
                extraLarge
            }
        }
    }
    """
    variables = {"search": anime_name}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"query": query, "variables": variables}) as response:
                if response.status != 200:
                    logger.error(f"AniList API returned status {response.status}")
                    return None
                    
                data = await response.json()
                
                # Check for errors in the response
                if "errors" in data:
                    error_message = data["errors"][0]["message"]
                    logger.error(f"AniList API error: {error_message}")
                    return None
                    
                return data.get("data", {}).get("Media")
    except aiohttp.ClientError as e:
        logger.error(f"Network error when fetching anime info: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in fetch_anime_info: {e}")
        return None
