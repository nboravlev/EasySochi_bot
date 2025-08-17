import re

def replace_adler_with_kp_regex(place_name: str) -> str:
    # Ищем "Адлерский" и индекс 354392 с любыми пробелами/запятыми
    pattern = r",\s*\d{6}\s*,"
    return re.sub(pattern, ",", place_name).strip()