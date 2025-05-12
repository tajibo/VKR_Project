import re


def clean_text(text: str) -> str:
    """
    Приводит текст к нижнему регистру, убирает пунктуацию и лишние пробелы.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
