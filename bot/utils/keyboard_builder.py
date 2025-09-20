from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import calendar
from datetime import date, timedelta

# Префиксы для callback
CB_PREFIX = "CAL"
CB_SELECT = f"{CB_PREFIX}_SELECT"
CB_NAV = f"{CB_PREFIX}_NAV"

def build_calendar(year: int, month: int, check_in=None, check_out=None):
    """Строит inline-календарь"""
    cal = calendar.Calendar(firstweekday=0)
    keyboard = []

    # Шапка с месяцем
    keyboard.append([InlineKeyboardButton(f"{calendar.month_name[month]} {year}", callback_data="IGNORE")])

    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([InlineKeyboardButton(d, callback_data="IGNORE") for d in week_days])

    # Сетка дней
    for week in cal.monthdatescalendar(year, month):
        row = []
        for day in week:
            if day.month != month:
                row.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
            else:
                text = str(day.day)

                # Подсветка выбранного диапазона
                if check_in and check_out and check_in <= day <= check_out:
                    text = f"✔️{day.day}"
                elif check_in and day == check_in:
                    text = f"✔️{day.day}"
                elif check_out and day == check_out:
                    text = f"🔴{day.day}"

                row.append(InlineKeyboardButton(text, callback_data=f"{CB_SELECT}:{day.isoformat()}"))
        keyboard.append(row)

    # Навигация
    prev_month = (date(year, month, 1) - timedelta(days=1)).replace(day=1)
    next_month = (date(year, month, calendar.monthrange(year, month)[1]) + timedelta(days=1)).replace(day=1)
    keyboard.append([
        InlineKeyboardButton("◀️", callback_data=f"{CB_NAV}:{prev_month.year}:{prev_month.month}"),
        InlineKeyboardButton("▶️", callback_data=f"{CB_NAV}:{next_month.year}:{next_month.month}")
    ])

    return InlineKeyboardMarkup(keyboard)

def build_types_keyboard(types, selected):
    """Формирует inline-клавиатуру с отметками выбранных типов в 2 колонки."""
    keyboard = []
    row = []
    for i, t in enumerate(types, start=1):
        mark = "🔘 " if t["id"] in selected else "⚪️ "
        row.append(InlineKeyboardButton(f"{mark}{t['name']}", callback_data=f"type_{t['id']}"))
        if i % 2 == 0:  # каждые 2 кнопки — новая строка
            keyboard.append(row)
            row = []
    if row:  # если осталась одна "лишняя" кнопка
        keyboard.append(row)
    
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