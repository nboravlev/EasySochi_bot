from handlers.ShowInfoConversation import *

info_conversation = ConversationHandler(
    entry_points=[CommandHandler("info",info_command)],
    states={INFO_HANDLER: [CallbackQueryHandler(info_callback_handler, pattern=r"^info_(booking|object|terms)"),
                           CallbackQueryHandler(info_command, pattern=r"^info_menu$")]},
    fallbacks=[
        CommandHandler("cancel", cancel),
        CommandHandler("help", help_and_end),
        CommandHandler("invite", start_invite)
    ],
    per_message = False
)