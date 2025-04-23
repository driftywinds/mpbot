import os
import requests
import base64
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
#ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "-1002645206555"))
#ALLOWED_THREAD_ID = int(os.getenv("ALLOWED_THREAD_ID", "760"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    chat_id = update.effective_chat.id
    message_thread_id = update.effective_message.message_thread_id
    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=message_thread_id,
        text='Hello! Send me an addon UUID to get information about it.'
    )

async def handle_uuid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle received UUID and query the API."""
    uuid = update.message.text.strip()
    chat_id = update.effective_chat.id
    message_thread_id = update.effective_message.message_thread_id
    
    if not uuid:
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            text="Please send a valid UUID."
        )
        return

    try:
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

            await context.bot.send_message(
                chat_id=chat_id,
                message_thread_id=message_thread_id,
                text=f"Addon Information:\n{formatted_message}"
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                message_thread_id=message_thread_id,
                text="No information found for this UUID."
            )
            
    except Exception as e:
        error_text = f"Error: {str(e)}"
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            text=error_text
        )

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_uuid))
    application.run_polling()

if __name__ == '__main__':
    main()