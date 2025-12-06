import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

BOT_TOKEN = "8277893901:AAFrdqwPU1e2FPeU4WhyMVZUC9nkBCq2uko"
AUTHORIZED_USER_ID = 7675369659
GROUPS_FILE = "id.txt"

# Ensure groups file exists
if not os.path.exists(GROUPS_FILE):
    with open(GROUPS_FILE, "w") as f:
        pass

# -----------------------------
# Helper functions
# -----------------------------
def save_group(group_id):
    with open(GROUPS_FILE, "r") as f:
        groups = [line.strip() for line in f.readlines()]
    if str(group_id) not in groups:
        with open(GROUPS_FILE, "a") as f:
            f.write(f"{group_id}\n")

def load_groups():
    with open(GROUPS_FILE, "r") as f:
        return [int(line.strip()) for line in f.readlines() if line.strip()]

# -----------------------------
# Restrict access
# -----------------------------
def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != AUTHORIZED_USER_ID:
            await update.message.reply_text("❌ You are not allowed to use this bot.")
            return
        return await func(update, context)
    return wrapper

# -----------------------------
# Commands
# -----------------------------
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

# -----------------------------
# Handle forwarded messages
# -----------------------------
@restricted
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group(update.effective_chat.id)

    if context.user_data.get("waiting_forward"):
        groups = load_groups()
        sent_count = 0
        for group_id in groups:
            try:
                await context.bot.copy_message(
                    chat_id=group_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                sent_count += 1
            except Exception as e:
                print(f"Failed to send to {group_id}: {e}")
        await update.message.reply_text(f"Forwarded to {sent_count} groups ✔")
        context.user_data["waiting_forward"] = False

# -----------------------------
# Main
# -----------------------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("listgroups", listgroups))
    app.add_handler(CommandHandler("fw", fw))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    print("Bot started...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
