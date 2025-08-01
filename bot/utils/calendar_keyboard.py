import calendar
from datetime import date, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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
                    text = f"🟩{day.day}"
                elif check_in and day == check_in:
                    text = f"🟢{day.day}"
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
