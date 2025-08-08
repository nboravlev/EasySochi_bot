from bot.handlers.SearchParamsCollectionConv import *

search_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & filters.Regex("^🌍 Начать поиск$"), start_search),
                  CommandHandler("start_search", start_search)],
    states={
        SELECTING_CHECKIN: [CallbackQueryHandler(calendar_callback)],
        SELECTING_CHECKOUT: [CallbackQueryHandler(calendar_callback)],
        APTS_TYPES_SELECTION: [CallbackQueryHandler(handle_apartment_type_multiselection)],
        PRICE_FILTER_SELECTION: [CallbackQueryHandler(handle_price_filter_type_selection)],
        GUESTS_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guests_number)],
        BOOKING_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bookings_notion)]
                },
    fallbacks=[CommandHandler("cancel", cancel)],
)