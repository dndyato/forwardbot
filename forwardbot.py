import os
import logging
import traceback
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ---------------- CONFIG ---------------- #
BOT_TOKEN = "8428346557:AAFmx-G_AqGkzsvkFsoevilY_AXZnFDvGXg"
AUTHORIZED_USER_ID = 7675369659  # <-- replace with your Telegram user ID
GROUPS_FILE = "id.txt"

# Ensure groups file exists
if not os.path.exists(GROUPS_FILE):
    with open(GROUPS_FILE, "w") as f:
        pass

# ---------------- LOGGING ---------------- #
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- HELPERS ---------------- #
def save_group(group_id):
    with open(GROUPS_FILE, "r") as f:
        groups = [line.strip() for line in f.readlines()]
    if str(group_id) not in groups:
        with open(GROUPS_FILE, "a") as f:
            f.write(f"{group_id}\n")

def load_groups():
    with open(GROUPS_FILE, "r") as f:
        return [int(line.strip()) for line in f.readlines() if line.strip()]

# Decorator to restrict commands to only your user ID
def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != AUTHORIZED_USER_ID:
            await update.message.reply_text("❌ You are not allowed to use this bot.")
            return
        return await func(update, context)
    return wrapper

# ---------------- COMMANDS ---------------- #
@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is active! Use /fw to forward a message to all groups.")

@restricted
async def listgroups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    groups = load_groups()
    if not groups:
        await update.message.reply_text("No groups saved yet.")
        return
    text = "📌 Saved Groups:\n\n" + "\n".join([f"- {g} — Unknown Title" for g in groups])
    await update.message.reply_text(text)

@restricted
async def fw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📤 Forward me the message you want to send to all groups.")
    context.user_data["waiting_forward"] = True

# ---------------- MESSAGE HANDLER ---------------- #
@restricted
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Save group if message is in a group
        if update.effective_chat.type in ["group", "supergroup"]:
            save_group(update.effective_chat.id)

        # Only forward if /fw command was issued
        if context.user_data.get("waiting_forward"):
            groups = load_groups()
            sent_count = 0

            if update.message.media_group_id:
                # Album handling
                album_messages = context.chat_data.get(update.message.media_group_id, [])
                album_messages.append(update.message)
                context.chat_data[update.message.media_group_id] = album_messages

                # Only forward once per album
                if update.message.media_group_id not in context.user_data.get("album_forwarded", []):
                    media = []
                    for msg in album_messages:
                        if msg.photo:
                            media.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=msg.caption or ""))
                        elif msg.video:
                            media.append(InputMediaVideo(media=msg.video.file_id, caption=msg.caption or ""))
                    for group_id in groups:
                        try:
                            await context.bot.send_media_group(chat_id=group_id, media=media)
                            sent_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to send album to {group_id}: {e}")
                    context.user_data.setdefault("album_forwarded", []).append(update.message.media_group_id)
            else:
                # Single message
                for group_id in groups:
                    try:
                        await context.bot.copy_message(
                            chat_id=group_id,
                            from_chat_id=update.effective_chat.id,
                            message_id=update.message.message_id
                        )
                        sent_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to send to {group_id}: {e}")

            await update.message.reply_text(f"Forwarded to {sent_count} groups ✔")
            context.user_data["waiting_forward"] = False

    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        traceback.print_exc()

# ---------------- MAIN ---------------- #
async def main():
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("listgroups", listgroups))
        app.add_handler(CommandHandler("fw", fw))
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

        logger.info("Bot started...")
        await app.run_polling()
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
        traceback.print_exc()

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # fix "event loop already running" on Railway

    import asyncio
    asyncio.get_event_loop().run_until_complete(main())
