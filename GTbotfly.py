import os
import requests
import base64
import re
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "-1002645206555"))  # Convert to integer
ALLOWED_THREAD_ID = int(os.getenv("ALLOWED_THREAD_ID", "760"))         # Convert to integer

# UUID validation pattern
UUID_PATTERN = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')

def log_activity(message: str) -> None:
    """Log messages with timestamp to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def validate_topic(update: Update) -> bool:
    """Check if message is in the allowed topic"""
    return (update.effective_chat.id == ALLOWED_CHAT_ID and 
            update.effective_message.message_thread_id == ALLOWED_THREAD_ID)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if validate_topic(update):
        await send_response(update, context, 'Hello! Send me an addon UUID to get information about it.')

async def handle_uuid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Log incoming message
    user_info = f"@{update.effective_user.username}" if update.effective_user.username else "Unknown User"
    log_activity(f"Received message from {user_info} (Chat: {update.effective_chat.id}, Thread: {update.effective_message.message_thread_id}): '{update.message.text}'")

    if not validate_topic(update):
        log_activity("Message ignored - not in allowed topic")
        return

    uuid = update.message.text.strip()
    
    # Validate UUID format
    if not UUID_PATTERN.match(uuid):
        await send_response(update, context, "❌ That is not a valid UUID format. Please send a properly formatted UUID.")
        log_activity(f"Invalid UUID format received: {uuid}")
        return

    try:
        log_activity(f"Processing UUID: {uuid}")
        headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
        response = requests.get(f"{API_BASE_URL}{uuid}", headers=headers)
        response.raise_for_status()
        
        data = response.json().get('data', {})
        
        if data:
            download_hashes = data.get('download_hash', '')
            decoded_urls = []
            
            if download_hashes:
                for i, hash_part in enumerate(download_hashes.split(','), 1):
                    hash_part = hash_part.strip()
                    if hash_part:
                        try:
                            decoded = base64.b64decode(hash_part).decode('utf-8')
                            decoded_urls.append(f"{i}. {decoded}")
                        except:
                            decoded_urls.append(f"{i}. Invalid hash: {hash_part}")

            formatted_message = (
                f"UUID: {data.get('uuid', 'N/A')}\n"
                f"Name: {data.get('name', 'N/A')}\n"
                f"Creator: {data.get('creator', 'N/A')}\n"
                f"Version: {data.get('version', 'N/A')}\n"
            )
            
            if decoded_urls:
                formatted_message += "Download URLs:\n" + "\n".join(decoded_urls)
            else:
                formatted_message += "No download URLs found"

            await send_response(update, context, f"Addon Information:\n{formatted_message}")
            log_activity(f"Successfully responded to UUID: {uuid}")
        else:
            await send_response(update, context, "No information found for this UUID.")
            log_activity(f"No data found for UUID: {uuid}")
            
    except requests.exceptions.HTTPError as e:
        log_activity(f"API Error for {uuid}: {str(e)}")
        if e.response.status_code == 403:
            await send_response(update, context, "⛔ Access denied for this UUID")
        else:
            await send_response(update, context, f"🔧 API Error: {e.response.status_code} - Please try again later")
    except requests.exceptions.RequestException as e:
        log_activity(f"Connection error for {uuid}: {str(e)}")
        await send_response(update, context, "🔌 Connection error - Please try again later")
    except Exception as e:
        log_activity(f"Unexpected error processing {uuid}: {str(e)}")
        await send_response(update, context, "⚠️ An unexpected error occurred - Please try again later")

async def send_response(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Send response and log it to console"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.effective_message.message_thread_id,
        text=text
    )
    log_activity(f"Sent response: '{text}'")

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_uuid))
    application.run_polling()

if __name__ == '__main__':
    main()