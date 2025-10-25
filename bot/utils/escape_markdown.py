import re

def escape_markdown(text: str) -> str:
    """
    Экранирует специальные символы для MarkdownV2 в Telegram.
    """
    escape_chars = r'_*\[\]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
