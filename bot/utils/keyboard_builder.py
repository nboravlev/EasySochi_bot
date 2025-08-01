from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_types_keyboard(types, selected):
    """Формирует inline-клавиатуру с отметками выбранных типов."""
    keyboard = []
    for t in types:
        mark = "📍 " if t["id"] in selected else ""
        keyboard.append([InlineKeyboardButton(f"{mark}{t['name']}", callback_data=f"type_{t['id']}")])
    
    # Добавляем кнопку подтверждения
    keyboard.append([InlineKeyboardButton("✅ Подтвердить выбор", callback_data="confirm_types")])
    return keyboard

def build_price_filter_keyboard():
    return [
        [InlineKeyboardButton("0 – 3000 ₽", callback_data="price_0_3000")],
        [InlineKeyboardButton("3000 – 5900 ₽", callback_data="price_3000_5900")],
        [InlineKeyboardButton("6000+ ₽", callback_data="price_6000_plus")],
        [InlineKeyboardButton("💰 Без фильтра", callback_data="price_all")]
    ]