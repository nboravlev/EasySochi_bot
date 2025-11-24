from handlers.SearchParamsCollectionConv import *

# === CONVERSATION HANDLER ===
search_conv = ConversationHandler(
    entry_points=[
        CommandHandler("start_search", start_search),
        CallbackQueryHandler(start_search, pattern="^start_search$")
    ],
    states={
        SELECTING_CHECKIN: [
            CallbackQueryHandler(calendar_callback)
        ],
        SELECTING_CHECKOUT: [
            CallbackQueryHandler(calendar_callback)
        ],
        SELECTING_TYPES: [
            CallbackQueryHandler(handle_apartment_type_multiselection)
        ],
        SELECTING_PRICE: [
            CallbackQueryHandler(handle_price_filter_selection, pattern="^price_")
        ],
        VIEWING_APARTMENTS: [
            CallbackQueryHandler(navigate_apartments, pattern="^apt_(prev|next)_\d+$"),
            CallbackQueryHandler(handle_show_map, pattern="^show_map_\d+$"),
            CallbackQueryHandler(start_booking, pattern="^book_\d+_\d+(\.\d+)?$"),
            CallbackQueryHandler(start_search, pattern="^start_search$")
        ],
        ENTERING_GUESTS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_entering_guest_number)
        ],
        BOOKING_COMMENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, finalize_booking)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="apartment_search",
    persistent=False
)