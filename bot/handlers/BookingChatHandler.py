from bot.handlers.BookingChatConversation import *

booking_chat = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(enter_booking_chat, pattern=r"^chat_booking_enter_\d+$"),
        CallbackQueryHandler(open_booking_chat_from_menu, pattern=r"^chat_booking_\d+$")
    ],
    states={
        BOOKING_CHAT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, booking_chat_message),
            CommandHandler("exit_chat", exit_booking_chat)
        ]
    },
    fallbacks=[CommandHandler("exit_chat", exit_booking_chat)],
)
