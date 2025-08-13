import re

def replace_adler_with_kp_regex(place_name: str) -> str:
    # Ищем "Адлерский" и индекс 354392 с любыми пробелами/запятыми
    pattern = r"Адлерский,\s*354392"
    return re.sub(pattern, "Красная Поляна", place_name)