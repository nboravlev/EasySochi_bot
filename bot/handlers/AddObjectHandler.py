from bot.handlers.AddObjectConversation import *


add_object_conv = ConversationHandler(
    entry_points=[CommandHandler("add_object", start_add_object)],
    states={
        ADDRESS_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_address_text)],
        ADDRESS_SELECT: [CallbackQueryHandler(handle_address_selection)],
        APARTMENT_TYPE_SELECTION: [CallbackQueryHandler(handle_apartment_type_selection)],
        FLOOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_floor)],
        MAX_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_maxguests)],
        ELEVATOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_elevator)],
        PETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pets)],
        BALCONY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_balcony)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description)],
        PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price)],
        PHOTOS: [
            MessageHandler(filters.PHOTO, handle_photo),
            MessageHandler(filters.Regex("^(Готово|готово)$"), handle_photos_done),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel)
    ]
)


