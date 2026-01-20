from handlers.ReferralLinkConversation import *

referral_conversation = ConversationHandler(
    entry_points=[CommandHandler("invite", start_invite)],
    states={
        CREATE_LINK: [CallbackQueryHandler(handle_terms, pattern="^(accept_terms|decline_terms)$")],
        HANDLE_BUTTONS:[CallbackQueryHandler(handle_link_buttons, pattern="^(copy_link|back_menu)$")]
    },
    fallbacks=[CommandHandler("cancel", cancel)], per_message=False
)
