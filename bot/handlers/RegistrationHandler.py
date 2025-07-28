# Fixed ConversationHandler configuration

from bot.handlers.RegistrationConversation import *

registration_conversation = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CHOOSING_ROLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, choose_role)
        ],
        ASK_PHONE: [
            MessageHandler(filters.CONTACT, save_phone),
            MessageHandler(filters.Regex("^Пропустить$"), save_phone)  # ✅ Added for "Пропустить"
        ],
        ASK_LOCATION: [
            MessageHandler(filters.LOCATION, save_location),
            MessageHandler(filters.Regex("^Не отправлять$"), save_location)  # ✅ Added for "⏭ Не отправлять"
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CommandHandler("start", start)  # ✅ Allow restart
    ]
)