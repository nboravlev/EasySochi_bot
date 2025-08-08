# Fixed ConversationHandler configuration

from bot.handlers.RegistrationConversation import *

registration_conversation = ConversationHandler(
    entry_points=[CommandHandler("start", start),
                  CallbackQueryHandler(start, pattern="back_menu")],
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
        ],
        VIEW_BOOKINGS: [CallbackQueryHandler(show_renter_bookings, pattern=r"^book_(next|prev|message)_\d+$"),
                        CallbackQueryHandler(start, pattern="^back_menu$")],
        VIEW_OBJECTS: [CallbackQueryHandler(show_owner_objects, pattern=r"^apt_(next|prev|delete)_\d+$"),
                           CallbackQueryHandler(start, pattern="back_menu")],
        REPORT_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_problem)],
        BOOKING_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_chat_message)],
        SHOW_HELP: [CallbackQueryHandler(help_callback_handler, pattern="^help_(booking|object)"),
                    CallbackQueryHandler(start, pattern="back_menu")]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CommandHandler("start", start)  # ✅ Allow restart
    ]
)