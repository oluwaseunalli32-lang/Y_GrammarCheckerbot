import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Bot Token from Environment Variables (set on Render)
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "👋 Welcome to **Y_GrammarCheckerbot**!\n\n"
        "Just send or forward me any English text, and I will instantly check it for spelling and grammar mistakes!"
    )

async def check_grammar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check the grammar of the incoming text."""
    text_to_check = update.message.text
    
    # Skip if it's a command
    if text_to_check.startswith('/'):
        return

    await update.message.reply_chat_action(action="typing")

    try:
        # Call the free LanguageTool API
        response = requests.post(
            "https://api.languagetool.org/v2/check",
            data={'text': text_to_check, 'language': 'en-US'}
        )
        response_data = response.json()
        matches = response_data.get('matches', [])

        if not matches:
            await update.message.reply_text("✅ Your grammar looks perfect!")
            return

        # Apply corrections from back to front to avoid shifting indices
        corrected_text = text_to_check
        for match in sorted(matches, key=lambda x: x['offset'], reverse=True):
            offset = match['offset']
            length = match['length']
            replacements = match['replacements']
            
            if replacements:
                # Use the first suggested replacement
                suggestion = replacements[0]['value']
                corrected_text = corrected_text[:offset] + suggestion + corrected_text[offset + length:]

        # Send the corrected text back to the user
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

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_grammar))

    # Run the bot using polling
    application.run_polling()

if __name__ == '__main__':
    main()
