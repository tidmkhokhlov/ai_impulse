import re
from typing import Dict, Any

class NLPService:
    def __init__(self, model=None):
        self.model = model

    def preprocess(self, text: str) -> str:
        return text.strip()

    def extract_inn(self, text: str) -> str | None:
        m = re.search(r"\b(\d{10}|\d{12})\b", text)
        return m.group(0) if m else None

    def detect_personal_data_fields(self, text: str) -> Dict[str, bool]:
        fields = {
            'phone': bool(re.search(r"\+?\d[\d\s\-()]{6,}\d", text)),
            'email': bool(re.search(r"[\w\.\-]+@[\w\.\-]+", text)),
            'name_prompt': bool(re.search(r"\bимя\b|\bфамилия\b", text, flags=re.IGNORECASE)),
        }
        return fields

    def classify_ad(self, text: str) -> Dict[str, Any]:
        t = text.lower()
        keywords = ['реклама', 'promo', 'ad', 'sponsored']
        is_ad = any(k in t for k in keywords)
        score = 0.9 if is_ad else 0.2
        return {"is_ad": is_ad, "score": score}

    def analyze(self, text: str) -> Dict[str, Any]:
        return {
            'text': text,
            'inn': self.extract_inn(text),
            'pd_fields': self.detect_personal_data_fields(text),
            'ad': self.classify_ad(text),
        }
