# Fixed ConversationHandler configuration

from handlers.RegistrationConversation import *

registration_conversation = ConversationHandler(
    entry_points=[CommandHandler("start", start),
                  CallbackQueryHandler(start, pattern="back_menu")],
    states={
        NAME_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_request)],
        ASK_PHONE: [MessageHandler(filters.TEXT | filters.CONTACT, handle_phone_registration)],
        MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice)],
        VIEW_BOOKINGS: [CallbackQueryHandler(show_renter_bookings, pattern=r"^book_(next|prev)_\d+$"),
                        CallbackQueryHandler(start, pattern="^back_menu$")],
        VIEW_OBJECTS: [CallbackQueryHandler(show_owner_objects, pattern=r"^apt_(next|prev|delete)_\d+$"),
                       CallbackQueryHandler(select_owner_orders, pattern=r"^goto_\d+$"),
                           CallbackQueryHandler(start, pattern="back_menu")],
        VIEW_ORDERS: [CallbackQueryHandler(show_owner_orders, pattern=r"^owner_book_(next|prev)_\d+$"),
                           CallbackQueryHandler(show_owner_objects, pattern="back_to_objects")]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CommandHandler("start", start)
    ]
)