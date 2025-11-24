from handlers.CommitDeclineCancelBookingConversation import *

conv_commit_decline_cancel = ConversationHandler(
    entry_points=[CallbackQueryHandler(booking_decline_callback, pattern=r"^booking_decline_\d+_\d+$"),
                  CallbackQueryHandler(booking_confirm_callback, pattern=r"^booking_confirm_\d+$")],
    states={
        DECLINE_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_decline_reason)]
    },
    fallbacks=[],
)
