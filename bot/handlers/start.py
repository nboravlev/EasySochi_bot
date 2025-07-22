from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from bot.handlers.role_request import ask_user_role  # ⬅️ Показывает кнопки "Арендовать" / "Предложить"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start.

    ✅ Показывает пользователю кнопки с выбором роли:
        - "Хочу арендовать квартиру" → роль пользователя (role_id = 1)
        - "Хочу предложить квартиру" → роль владельца (role_id = 2)

    ❗ Регистрация пользователя и сессии происходит только после выбора роли
       — логика реализована в `role_handler.py`.
    """

    await ask_user_role(update, context)  # ⬅️ Первая точка взаимодействия
    print(f"Пользователь {update.effective_user.id} нажал /start")

# Экспортируем хендлер
start_handler = CommandHandler("start", start_command)

