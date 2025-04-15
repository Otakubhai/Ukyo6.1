#!/usr/bin/env python3
"""
Anime & Multporn Telegram Bot
A multipurpose bot that handles anime information and multporn image downloads.
"""

import os
import re
import asyncio
import logging
from dotenv import load_dotenv

# Import custom modules
from utils.anime_fetcher import fetch_anime_info
from utils.image_handler import scrape_images, download_images
from utils.pdf_generator import create_pdf_from_images
from utils.helpers import cleanup_temp_folder

# Pyrogram imports
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Allowed Users - Add your user IDs here
ALLOWED_USERS = set(os.getenv("ALLOWED_USERS", "").split(","))

# Initialize the bot
bot = Client("anime_multporn_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# User session storage
USER_SELECTION = {}

# ========== BOT COMMANDS ==========
@bot.on_message(filters.command("start"))
async def start(client, message):
    """Handles the /start command."""
    if str(message.from_user.id) not in ALLOWED_USERS:
        await message.reply_text("🚫 You are not authorized to use this bot.")
        return
    
    await message.reply_text(
        "Welcome! Here's what I can do:\n\n"
        "• Use /anime to search for anime info\n"
        "• Send a multporn.net link to get images and PDF\n"
        "• Use /setparams to set anime name format\n"
        "• Use /split for Telegram links with episode numbering"
    )

@bot.on_message(filters.command("anime"))
async def anime_command(client, message):
    """Handles the /anime command."""
    if str(message.from_user.id) not in ALLOWED_USERS:
        await message.reply_text("🚫 You are not authorized to use this bot.")
        return
    
    await message.reply_text("📩 Send me the anime name:")
    USER_SELECTION[message.chat.id] = {"state": "waiting_anime_name"}

@bot.on_message(filters.command("setparams"))
async def set_params(client, message):
    """
    Sets the anime name parameter.
    Usage: /setparams <anime_name with {episode}>
    """
    if str(message.from_user.id) not in ALLOWED_USERS:
        await message.reply_text("🚫 You are not authorized to use this command.")
        return
    
    try:
        _, args = message.text.split(" ", 1)
        
        if "{episode}" not in args:
            await message.reply_text("❌ Format must include {episode} placeholder.")
            return
            
        USER_SELECTION[message.chat.id] = USER_SELECTION.get(message.chat.id, {})
        USER_SELECTION[message.chat.id]['anime_name'] = args.strip()
        await message.reply_text(f"✅ Anime name set to: {args.strip()}")
    except ValueError:
        await message.reply_text("❌ Invalid usage. Use /setparams <anime_name with {episode}>\n"
                               "Example: /setparams [AW] S01-E{episode} Anime Name [1080p] [Dual]")

@bot.on_message(filters.command("split"))
async def split_command(client, message):
    """Initiates the link splitting process."""
    if str(message.from_user.id) not in ALLOWED_USERS:
        await message.reply_text("🚫 You are not authorized to use this command.")
        return
        
    if message.chat.id not in USER_SELECTION or 'anime_name' not in USER_SELECTION[message.chat.id]:
        await message.reply_text("❌ Please use /setparams first to set the anime name format.")
        return
        
    USER_SELECTION[message.chat.id]['state'] = 'split_start'
    await message.reply_text("Send the start link (format: https://t.me/channel/message_id)")

@bot.on_callback_query()
async def button_callback(client, callback_query):
    """Handles button callbacks from inline keyboards."""
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    user_id = str(callback_query.from_user.id)

    if user_id not in ALLOWED_USERS:
        await callback_query.answer("🚫 You are not authorized to use this bot.")
        return

    if chat_id not in USER_SELECTION:
        await callback_query.answer("❌ No active selection found.")
        return

    # Handle quality selection
    if data in ["480p", "720p", "1080p", "720p_1080p", "480p_720p_1080p"]:
        USER_SELECTION[chat_id]["quality"] = data.replace("_", ", ")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Otaku", callback_data="otaku")],
            [InlineKeyboardButton("Hanime", callback_data="hanime")],
            [InlineKeyboardButton("Ongoing", callback_data="ongoing")]
        ])
        
        await callback_query.edit_message_text("📁 Choose format:", reply_markup=keyboard)
        return

    # Handle format selection (otaku, hanime, ongoing)
    elif data in ["otaku", "hanime", "ongoing"]:
        anime_name = USER_SELECTION[chat_id]["anime_name"]
        quality = USER_SELECTION[chat_id]["quality"]
        format_type = data
        
        # Get anime info from AniList
        anime = await fetch_anime_info(anime_name)
        if not anime:
            await callback_query.message.reply_text("❌ Anime not found.")
            return

        # Format the response based on template selected
        await send_formatted_anime_response(
            client, 
            callback_query.message, 
            anime, 
            format_type, 
            quality
        )
        
        # Clear user selection
        USER_SELECTION.pop(chat_id, None)
        await callback_query.answer("✅ Anime info sent!")

@bot.on_message(filters.text & (filters.private | filters.group))
async def handle_text(client, message):
    """Handles text messages in private chats and groups."""
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    
    if user_id not in ALLOWED_USERS:
        await message.reply_text("🚫 You are not authorized to use this bot.")
        return

    text = message.text.strip()
    current_state = USER_SELECTION.get(chat_id, {}).get("state")

    # Handle SPLIT FEATURE states
    if current_state == "split_start":
        if not re.match(r'https://t\.me/[a-zA-Z0-9_]+/\d+', text):
            await message.reply_text("❌ Invalid link format. Should be https://t.me/channel/message_id")
            return
            
        USER_SELECTION[chat_id]["start_link"] = text
        USER_SELECTION[chat_id]["state"] = "split_end"
        await message.reply_text("Now send the end link")
        return
        
    elif current_state == "split_end":
        if not re.match(r'https://t\.me/[a-zA-Z0-9_]+/\d+', text):
            await message.reply_text("❌ Invalid link format. Should be https://t.me/channel/message_id")
            return
            
        start_link = USER_SELECTION[chat_id].get("start_link")
        anime_name = USER_SELECTION[chat_id].get("anime_name", "")
        
        # Process the split links
        try:
            await process_split_links(client, message, start_link, text, anime_name)
        except Exception as e:
            logger.error(f"Error in split process: {e}")
            await message.reply_text(f"❌ Error: {str(e)}")
        
        # Reset state
        USER_SELECTION[chat_id]['state'] = None
        return
        
    # Handle ANIME NAME input
    elif current_state == "waiting_anime_name":
        anime_name = text
        USER_SELECTION[chat_id]["anime_name"] = anime_name
        USER_SELECTION[chat_id]["state"] = None
        
        # Show quality selection keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("480p", callback_data="480p")],
            [InlineKeyboardButton("720p", callback_data="720p")],
            [InlineKeyboardButton("1080p", callback_data="1080p")],
            [InlineKeyboardButton("720p & 1080p", callback_data="720p_1080p")],
            [InlineKeyboardButton("480p, 720p & 1080p", callback_data="480p_720p_1080p")]
        ])
        
        await message.reply_text("📊 Choose quality:", reply_markup=keyboard)
        return

    # Handle MULTPORN link
    if text.startswith("https://multporn.net/"):
        USER_SELECTION[chat_id] = {"url": text, "state": "waiting_image_limit"}
        await message.reply_text("How many images would you like to download?")
        return
        
    # Handle IMAGE LIMIT for multporn
    if chat_id in USER_SELECTION and USER_SELECTION[chat_id].get("state") == "waiting_image_limit":
        try:
            limit = int(text)
            if limit < 1:
                raise ValueError
        except ValueError:
            await message.reply_text("❌ Please send a valid number.")
            return
            
        # Process multporn download
        await process_multporn_download(client, message, limit)
        return

async def process_split_links(client, message, start_link, end_link, anime_name):
    """Process and generate split links with episode numbers."""
    # Extract channel and message IDs
    match_start = re.match(r'https://t.me/([a-zA-Z0-9_]+)/(\d+)', start_link)
    match_end = re.match(r'https://t.me/([a-zA-Z0-9_]+)/(\d+)', end_link)
    
    if not match_start or not match_end:
        await message.reply_text("❌ Invalid link format.")
        return
        
    chat_username, start_id = match_start.groups()
    _, end_id = match_end.groups()
    
    start_id, end_id = int(start_id), int(end_id)
    
    if start_id > end_id:
        await message.reply_text("❌ Start ID cannot be greater than End ID.")
        return
        
    # Generate links with episode numbering
    links = []
    for i, msg_id in enumerate(range(start_id, end_id + 1)):
        episode_num = f"{i+1:02d}"  # Format as 01, 02, etc.
        name = anime_name.replace("{episode}", episode_num)
        links.append(f"https://t.me/{chat_username}/{msg_id} -n {name}")
    
    # Send links in chunks to avoid message length limits
    for i in range(0, len(links), 30):
        chunk = links[i:i + 30]
        await message.reply_text("\n".join(chunk))

async def process_multporn_download(client, message, limit):
    """Process multporn link and download images."""
    chat_id = message.chat.id
    url = USER_SELECTION[chat_id]["url"]
    
    await message.reply_text("🔍 Fetching images, please wait...")
    
    # Scrape images from the URL
    image_urls, error = scrape_images(url)
    if error:
        await message.reply_text(f"❌ Error: {error}")
        USER_SELECTION.pop(chat_id, None)
        return
        
    # Select limited number of images
    selected_images = image_urls[:limit]
    if not selected_images:
        await message.reply_text("❌ No images found.")
        USER_SELECTION.pop(chat_id, None)
        return
        
    # Create temp folder for downloading
    temp_folder = f"temp_downloads_{chat_id}"
    os.makedirs(temp_folder, exist_ok=True)
    
    # Download images
    await message.reply_text(f"⬇️ Downloading {len(selected_images)} images...")
    downloaded_paths = await download_images(selected_images, temp_folder)
    
    # Send images to user
    for path in downloaded_paths:
        try:
            await client.send_document(chat_id, path)
        except Exception as e:
            logger.error(f"Error sending document: {e}")
    
    # Create and send PDF
    await message.reply_text("📄 Generating PDF...")
    try:
        pdf_path = os.path.join(temp_folder, "output.pdf")
        create_pdf_from_images(temp_folder, pdf_path)
        await client.send_document(chat_id, pdf_path, file_name="multporn_images.pdf")
        await message.reply_text("✅ All images and PDF have been sent!")
    except Exception as e:
        logger.error(f"Error creating PDF: {e}")
        await message.reply_text(f"❌ Error creating PDF: {str(e)}")
    
    # Clean up
    USER_SELECTION.pop(chat_id, None)
    cleanup_temp_folder(temp_folder)

async def send_formatted_anime_response(client, message, anime, format_type, quality):
    """Send formatted anime response based on template."""
    if not anime:
        await message.reply_text("❌ Anime not found.")
        return
        
    anime_id = anime["id"]
    image_url = f"https://img.anili.st/media/{anime_id}"
    title = anime["title"]["english"] or anime["title"]["romaji"]
    genres_text = ", ".join(anime["genres"])
    genre_tags = " ".join([f"#{g}" for g in anime["genres"]])
    
    if format_type == "hanime":
        message_text = f"""<b>💦 {title}
╭──────────────────────
├ 📺 Episode : {anime['episodes'] or 'N/A'}
├ 💾 Quality : {quality}
├ 🎭 Genres: {genres_text}
├ 🔊 Audio track : Sub
├ #Censored
├ #Recommendation +++++++
╰──────────────────────</b>"""
    
    elif format_type == "otaku":
        message_text = f"""<b>💙 {title}</b>

<b>🎭 Genres :</b> {genres_text}
<b>🔊 Audio :</b> Dual Audio
<b>📡 Status :</b> Completed
<b>🗓 Episodes :</b> {anime['episodes'] or 'N/A'}
<b>💾 Quality :</b> {quality}
<b>✂️ Sizes :</b> 50MB, 120MB & 300MB
<b>🔞 Rating :</b> PG-13

<blockquote>📌 : {genre_tags}</blockquote>"""
    
    else:  # ongoing
        message_text = f"""❤️  {title}
╭───────────────────
├ 📺 Episodes : {anime['episodes'] or 'N/A'}
├ 💾 Quality : {quality}
├ 🎭 Genres: {genres_text}
├ 🔊 Audio track : Dual [English+Japanese]
╰───────────────────
Report Missing Episodes: @Otaku_Library_Support_Bot"""
    
    # Send message with photo
    try:
        await client.send_photo(
            message.chat.id,
            photo=image_url,
            caption=message_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error sending photo: {e}")
        # Fallback to text-only if image fails
        await message.reply_text(
            f"⚠️ Could not load image, but here's the info:\n\n{message_text}", 
            parse_mode=ParseMode.HTML
        )

# Main execution
if __name__ == "__main__":
    print("✅ Bot is running...")
    bot.run()
