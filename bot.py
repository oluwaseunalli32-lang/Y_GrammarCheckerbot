import os
import logging
import requests
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Bot Token from Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Dummy Web Server to satisfy Render Web Service port requirements
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    logger.info(f"Dummy web server started on port {port}")
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "👋 Welcome to **Y_GrammarCheckerbot**!\n\n"
        "Just send or forward me any English text, and I will instantly check it for spelling and grammar mistakes!"
    )

async def check_grammar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check the grammar of the incoming text."""
    text_to_check = update.message.text
    
    if text_to_check.startswith('/'):
        return

    await update.message.reply_chat_action(action="typing")

    try:
        response = requests.post(
            "https://api.languagetool.org/v2/check",
            data={'text': text_to_check, 'language': 'en-US'}
        )
        response_data = response.json()
        matches = response_data.get('matches', [])

        if not matches:
            await update.message.reply_text("✅ Your grammar looks perfect!")
            return

        corrected_text = text_to_check
        for match in sorted(matches, key=lambda x: x['offset'], reverse=True):
            offset = match['offset']
            length = match['length']
            replacements = match['replacements']
            
            if replacements:
                suggestion = replacements[0]['value']
                corrected_text = corrected_text[:offset] + suggestion + corrected_text[offset + length:]

        response_message = f"✍️ **Corrected Version:**\n\n{corrected_text}"
        await update.message.reply_text(response_message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error processing grammar check: {e}")
        await update.message.reply_text("❌ Sorry, I encountered an error checking your text. Please try again later.")

def main() -> None:
    """Start the bot."""
    if not TOKEN:
        logger.error("No TELEGRAM_TOKEN found in environment variables!")
        return

    # FIX FOR PYTHON 3.14+: Explicitly set up the asyncio event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Start the dummy web server in a separate thread so Render is happy
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Create the Application and run polling
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_grammar))

    logger.info("Starting bot polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
