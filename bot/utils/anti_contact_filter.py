import re

def sanitize_message(text: str) -> str:
    # 9+ цифр подряд → ***
    #text = re.sub(r"\d{9,}", "***", text)
    # email → ***
    text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "***", text)
    # Telegram @username → ***
    text = re.sub(r"@\w{3,}", "***", text)
    # ссылки на мессенджеры → ***
    text = re.sub(r"(t\.me/|wa\.me/|viber://|vk\.com/|instagram\.com/)\S+", "***", text)
    return text
