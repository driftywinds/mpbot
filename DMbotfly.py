import os
import requests
import base64
import re
import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# UUID validation pattern
UUID_PATTERN = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')

def log_activity(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Hello! I can help you find addons.\n\n"
        "🔍 Search by name/creator: Type any search term\n"
        "🔎 Get by UUID: Paste a valid UUID\n"
        "❌ Cancel ongoing search: Type /cancel or 'cancel'"
    )
    await send_response(update, context, help_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('awaiting_index'):
        context.user_data.clear()
        await send_response(update, context, "❌ Search cancelled. You can start a new search.")
        log_activity("Search cancelled by user")
    else:
        await send_response(update, context, "⚠️ No active operation to cancel")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_info = f"@{update.effective_user.username}" if update.effective_user.username else "Unknown User"
    log_activity(f"Received message from {user_info}: '{update.message.text}'")

    user_input = update.message.text.strip().lower()

    # Handle cancellation first
    if user_input in ['cancel', 'abort']:
        await cancel(update, context)
        return

    # Check if expecting index selection
    if context.user_data.get('awaiting_index'):
        try:
            index = int(user_input) - 1
            search_results = context.user_data.get('search_results', [])
            if 0 <= index < len(search_results):
                selected_uuid = search_results[index]['uuid']
                context.user_data.clear()
                await process_uuid(update, context, selected_uuid)
            else:
                await send_response(update, context, "❌ Invalid index. Type /cancel to abort.")
        except ValueError:
            await send_response(update, context, "❌ Please enter a valid number or type /cancel to abort")
        return

    # Check if input is UUID
    if UUID_PATTERN.match(user_input):
        await process_uuid(update, context, user_input)
    else:
        await perform_search(update, context, user_input)

async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    try:
        log_activity(f"Searching for: {query}")
        headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
        
        # Directus filter parameters
        search_params = {
            "filter": json.dumps({
                "_or": [
                    {"name": {"_icontains": query}},
                    {"creator": {"_icontains": query}}
                ]
            }),
            "fields": "uuid,name,creator,version,download_hash",
            "limit": "10"
        }

        response = requests.get(
            url=f"{API_BASE_URL}",
            headers=headers,
            params=search_params
        )
        response.raise_for_status()
        
        search_data = response.json().get('data', [])
        
        if not search_data:
            await send_response(update, context, "🔍 No results found for your query.")
            return

        context.user_data['search_results'] = search_data
        context.user_data['awaiting_index'] = True

        results_list = [
            f"{idx}. {item.get('name', 'N/A')} by {item.get('creator', 'N/A')}"
            for idx, item in enumerate(search_data, 1)
        ]
        
        response_message = "🔍 Search Results:\n" + "\n".join(results_list) + "\n\nReply with the number to view details:"
        await send_response(update, context, response_message)

    except requests.exceptions.HTTPError as e:
        error_msg = f"🔧 API Error: {e.response.status_code}"
        await send_response(update, context, error_msg)
        log_activity(f"Search API Error: {str(e)}")
    except Exception as e:
        log_activity(f"Search error: {str(e)}")
        await send_response(update, context, "⚠️ Error processing search")

async def process_uuid(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid: str) -> None:
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
                    try:
                        decoded = base64.b64decode(hash_part.strip()).decode('utf-8')
                        decoded_urls.append(f"{i}. {decoded}")
                    except:
                        decoded_urls.append(f"{i}. Invalid hash")

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

            await send_response(update, context, f"📦 Addon Information:\n{formatted_message}")
        else:
            await send_response(update, context, "❌ No information found for this UUID.")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            await send_response(update, context, "⛔ Access denied for this UUID")
        else:
            await send_response(update, context, f"🔧 API Error: {e.response.status_code}")
    except Exception as e:
        log_activity(f"UUID processing error: {str(e)}")
        await send_response(update, context, "⚠️ Error fetching UUID details")

async def send_response(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text
    )
    log_activity(f"Sent response: '{text}'")

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Modified message handler configuration
    application.add_handler(MessageHandler(
        filters.TEXT & 
        ~filters.COMMAND &
        filters.ChatType.PRIVATE,
        handle_text
    ))
    
    application.run_polling()

if __name__ == '__main__':
    main()
