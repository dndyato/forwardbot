import os
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

ID_FILE = "id.txt"
OWNER_ID = 7675369659          # <-- PUT YOUR TELEGRAM ID HERE
ASK_MESSAGE = 1


# -----------------------------
# GROUP ID MANAGEMENT
# -----------------------------
def load_groups():
    if not os.path.exists(ID_FILE):
        open(ID_FILE, "w").close()
        return []

    with open(ID_FILE, "r") as f:
        return [int(line.strip()) for line in f.readlines() if line.strip().isdigit()]


def save_group(group_id):
    groups = load_groups()
    if group_id not in groups:
        with open(ID_FILE, "a") as f:
            f.write(str(group_id) + "\n")
        return True
    return False


# -----------------------------
# AUTO SAVE GROUPS
# -----------------------------
async def catch_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type in ["group", "supergroup"]:
        added = save_group(chat.id)
        if added:
            await update.message.reply_text("Group registered ✔")


# -----------------------------
# /fw START
# -----------------------------
async def fw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return ConversationHandler.END

    await update.message.reply_text("Send the message you want me to forward to all groups.")
    return ASK_MESSAGE


# -----------------------------
# RECEIVE MESSAGE AND FORWARD
# -----------------------------
async def fw_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    groups = load_groups()

    sent = 0

    for gid in groups:
        try:
            await context.bot.copy_message(
                chat_id=gid,
                from_chat_id=msg.chat_id,
                message_id=msg.message_id
            )
            sent += 1
        except Exception:
            pass

    await msg.reply_text(f"Forwarded to {sent} groups ✔")
    return ConversationHandler.END


# -----------------------------
# /listgroups
# -----------------------------
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return

    groups = load_groups()

    if not groups:
        await update.message.reply_text("No groups saved yet.")
        return

    text = "📌 *Saved Groups:*\n\n"

    for gid in groups:
        try:
            chat = await context.bot.get_chat(gid)
            name = chat.title or "Unknown Title"
        except Exception:
            name = "Unknown Title"

        text += f"- `{gid}` — {name}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# -----------------------------
# MAIN LOOP (PTB v21 STANDARD)
# -----------------------------
async def main():
    app = Application.builder().token("8277893901:AAGfMTrjo7N3OHWpm62g9_SBTjRTR6oHVfM").build()

    # Conversation handler for /fw
    fw_handler = ConversationHandler(
        entry_points=[CommandHandler("fw", fw_start)],
        states={ASK_MESSAGE: [MessageHandler(filters.ALL, fw_receive)]},
        fallbacks=[]
    )

    app.add_handler(fw_handler)
    app.add_handler(CommandHandler("listgroups", list_groups))
    app.add_handler(MessageHandler(filters.ALL, catch_groups))

    async with app:
        await app.start()
        await app.updater.start_polling()

        # Keeps bot running on Railway
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
