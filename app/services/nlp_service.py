import re
from typing import Dict, Any

class NLPService:
    def __init__(self, model=None):
        self.model = model

    def preprocess(self, text: str) -> str:
        """Удаление лишних пробелов и нормализация текста."""
        return text.strip()

    def extract_inn(self, text: str) -> str | None:
        """Находит ИНН (10 или 12 цифр)."""
        m = re.search(r"\b(\d{10}|\d{12})\b", text)
        return m.group(0) if m else None

    def detect_personal_data_fields(self, text: str) -> Dict[str, bool]:
        """Определяет наличие полей персональных данных."""
        fields = {
            'phone': bool(re.search(r"\+?\d[\d\s\-()]{6,}\d", text)),
            'email': bool(re.search(r"[\w\.\-]+@[\w\.\-]+", text)),
            'name_prompt': bool(re.search(r"\bимя\b|\bфамилия\b", text, flags=re.IGNORECASE)),
            'form_or_bot': bool(re.search(r"\bвведите\b|\bотправьте\b|\bзаполните форму\b|\bбот для регистрации\b", text, flags=re.IGNORECASE)),
        }
        return fields

    def classify_ad(self, text: str) -> dict:
        """Определяет, является ли текст рекламой."""
        t = text.lower()

        # Явная реклама — добавляем #реклама
        explicit_keywords = ['реклама', '#реклама', 'promo', 'ad', 'sponsored']
        # Неявная реклама (скидки, акции, промокоды)
        implicit_keywords = ['скидк', 'акци', 'промокод', 'промо']

        is_explicit_ad = any(k in t for k in explicit_keywords)
        is_implicit_ad = any(k in t for k in implicit_keywords)

        is_ad = is_explicit_ad or is_implicit_ad
        score = 0.9 if is_ad else 0.2

        return {"is_ad": is_ad, "score": score, "explicit": is_explicit_ad, "implicit": is_implicit_ad}

    def analyze(self, text: str) -> Dict[str, Any]:
        """Собирает все NLP-данные для RulesEngine."""
        preprocessed_text = self.preprocess(text)
        pd_fields = self.detect_personal_data_fields(preprocessed_text)
        ad_info = self.classify_ad(preprocessed_text)
        inn = self.extract_inn(preprocessed_text)

        return {
            'text': preprocessed_text,
            'inn': inn,
            'pd_fields': pd_fields,
            'ad': ad_info,
        }
