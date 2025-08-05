from bot.handlers.CommitBookingConversation import *

conv_commit = ConversationHandler(
    entry_points=[CallbackQueryHandler(booking_confirm_callback, pattern=r"^booking_confirm:\d+$")],
    states={
        GO_TO_CHAT: [CallbackQueryHandler(open_booking_chat, pattern=r"^chat_booking_\d+$")],
        BOOKING_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_booking_chat_message)]
    },
    fallbacks=[],
)