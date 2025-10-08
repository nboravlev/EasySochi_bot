from handlers.RegistrationConversation import *

registration_conversation = ConversationHandler(
    entry_points=[CommandHandler("start", start),
                  CallbackQueryHandler(show_main_menu, pattern="^back_menu$")],
    states={
        NAME_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_request)],
        ASK_PHONE: [MessageHandler(filters.TEXT | filters.CONTACT, handle_phone_registration)],
        MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice)],
        VIEW_BOOKINGS: [CallbackQueryHandler(show_renter_bookings, pattern=r"^book_(next|prev)_\d+$"),
                        CallbackQueryHandler(handle_show_map, pattern="^renter_show_map_\d+$"),
                        CallbackQueryHandler(show_main_menu, pattern="^back_menu$")],
        VIEW_OBJECTS: [
            CallbackQueryHandler(show_owner_objects, pattern=r"^apt_(next|prev)_\d+$"),
            CallbackQueryHandler(handle_apartment_upgrade, pattern=r"^apt_upgrade_\d+$"),
            CallbackQueryHandler(confirm_delete_apartment, pattern=r"^apt_delete_\d+$"),
            CallbackQueryHandler(delete_apartment_confirmed, pattern=r"^delete_confirm_\d+$"),
            CallbackQueryHandler(cancel_delete_apartment, pattern=r"^delete_cancel$"),
            CallbackQueryHandler(select_owner_orders, pattern=r"^goto_\d+$"),
            CallbackQueryHandler(handle_show_map, pattern=r"^owner_show_map_\d+$"),
            CallbackQueryHandler(show_main_menu, pattern=r"^back_menu$")
        ],
        EDIT_OBJECT_PROMPT: [
            CallbackQueryHandler(handle_edit_price_start, pattern="^edit_price_start$"),
            CallbackQueryHandler(select_owner_objects, pattern="^back_to_objects$")
        ],
        EDIT_OBJECT_WAIT_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_price_input)
        ],
            VIEW_ORDERS: [CallbackQueryHandler(show_owner_orders, pattern=r"^owner_book_(next|prev)_\d+$"),
                            CallbackQueryHandler(select_owner_objects, pattern="^back_to_objects$")]
        },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CommandHandler("start", start),
        CommandHandler("info", info_and_end),
        CommandHandler("invite", invite_and_end)
    ],
    per_message = False
)