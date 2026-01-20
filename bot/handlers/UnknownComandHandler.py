from telegram.ext import MessageHandler, filters
from telegram.ext import ContextTypes
from telegram import Update

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = await context.bot.get_my_commands()
    commands_list = "\n".join([f"/{cmd.command} - {cmd.description}" for cmd in commands])
    await update.message.reply_text(
        f"Неизвестная команда.\nВот доступные команды:\n{commands_list}"
    )

# ...
unknown_command_handler = (MessageHandler(filters.COMMAND, unknown_command))
