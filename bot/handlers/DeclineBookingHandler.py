from bot.handlers.DeclineBookingConversation import *

conv_decline = ConversationHandler(
    entry_points=[CallbackQueryHandler(booking_decline_callback, pattern=r"^booking_decline:\d+$")],
    states={
        DECLINE_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_decline_reason)]
    },
    fallbacks=[],
)
