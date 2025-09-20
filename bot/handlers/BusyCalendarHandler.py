from handlers.BusyCalendarConversation import *

busy_calendar = ConversationHandler(
    entry_points=[CallbackQueryHandler(placeholder_request_handler, pattern="^placeholder_\d+$")],
        states={
        HANDLE_PLACEHOLDER_BEGIN: [CallbackQueryHandler(calendar_callback)],
        HANDLE_PLACEHOLDER_END: [CallbackQueryHandler(calendar_callback)],
        COMMIT_PLACEHOLDER: [CallbackQueryHandler(handle_placeholder_commit,pattern=r"^commit_placeholder$"),
                             CallbackQueryHandler(placeholder_request_handler, pattern="^placeholder_\d+$")]
    },
    fallbacks=[
        CommandHandler("cancel", cancel)
    ]
)