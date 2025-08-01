from bot.handlers.ShowResultsConversation import *

search_handler = ConversationHandler(
    entry_points=[CommandHandler("start_search", start_search)],
    states={
        ASK_CHECKIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_checkin)],
        ASK_CHECKOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_checkout)],
        APPLY_FILTERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_filters)],
        SHOW_RESULTS: [CallbackQueryHandler(show_details)],
        SHOW_DETAILS: [CallbackQueryHandler(confirm_booking)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)