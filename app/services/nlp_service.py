import re
import yaml
from pathlib import Path
from typing import Dict, Any, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class NLPService:
    def __init__(self, rules_config: str = None):
        # Автоматический поиск файла правил
        self.rules = self._find_and_load_rules(rules_config)
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
        self._fit_vectorizer()
        self.severity_points = {'high': 5, 'medium': 2, 'low': 1}

    def _find_and_load_rules(self, rules_config: str = None) -> List[Dict]:
        """Находит и загружает файл правил."""
        possible_paths = []

        # Если путь указан явно
        if rules_config:
            possible_paths.append(Path(rules_config))

        # Автоматический поиск от текущего файла
        current_dir = Path(__file__).parent
        possible_paths.extend([
            current_dir / "rules_v4.yaml",
            current_dir / "rules" / "rules_v4.yaml",
            current_dir.parent / "rules" / "rules_v4.yaml",
            current_dir.parent.parent / "rules" / "rules_v4.yaml",
            Path("rules_v4.yaml"),
            Path("rules/rules_v4.yaml"),
        ])

        # Попробовать найти файл
        for path in possible_paths:
            if path.exists():
                print(f"[NLPService] Загружаем правила из: {path}")
                return self._load_rules(path)

        # Если файл не найден, создаем базовые правила
        print("[NLPService] Файл правил не найден, используем базовые правила")

    def _load_rules(self, path: Path) -> List[Dict]:
        """Загружает правила из YAML файла."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            rules = config.get('rules', [])
            print(f"[NLPService] Загружено {len(rules)} правил")
            return rules
        except Exception as e:
            print(f"[NLPService] Ошибка загрузки правил: {e}")
            return self._get_basic_rules()

    # Остальные методы остаются без изменений...
    def _fit_vectorizer(self):
        """Обучает векторизатор на ключевых словах из правил."""
        all_keywords = []
        for rule in self.rules:
            condition = rule.get('condition', {})
            all_keywords.extend(condition.get('contains', []))
            all_keywords.extend(condition.get('not_contains', []))

        sample_texts = list(set(all_keywords))
        if sample_texts:
            self.vectorizer.fit(sample_texts)

    def preprocess(self, text: str) -> str:
        """Удаление лишних пробелов и нормализация текста."""
        return re.sub(r'\s+', ' ', text.strip())

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Извлекает сущности из текста."""
        return {
            'INN': self._extract_inn(text),
            'phone': self._extract_phone(text),
            'email': self._extract_email(text),
            'links': self._extract_links(text)
        }

    def _extract_inn(self, text: str) -> List[str]:
        """Находит ИНН (10 или 12 цифр)."""
        inn_pattern = r'\b\d{10}\b|\b\d{12}\b'
        return re.findall(inn_pattern, text)

    def _extract_phone(self, text: str) -> List[str]:
        """Извлекает телефоны из текста."""
        phone_pattern = r'\+?7[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}'
        return re.findall(phone_pattern, text)

    def _extract_email(self, text: str) -> List[str]:
        """Извлекает email из текста."""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(email_pattern, text)

    def _extract_links(self, text: str) -> List[str]:
        """Извлекает ссылки из текста."""
        link_pattern = r'https?://[^\s]+|www\.[^\s]+|t\.me/[^\s]+|bit\.ly/[^\s]+'
        return re.findall(link_pattern, text)

    def detect_personal_data_fields(self, text: str) -> Dict[str, bool]:
        """Определяет наличие полей персональных данных."""
        text_lower = text.lower()
        fields = {
            'phone': bool(re.search(r"\+?\d[\d\s\-()]{6,}\d", text)),
            'email': bool(re.search(r"[\w\.\-]+@[\w\.\-]+", text)),
            'name_prompt': bool(re.search(r"\bимя\b|\bфамилия\b", text_lower)),
            'form_or_bot': bool(
                re.search(r"\bвведите\b|\bотправьте\b|\bзаполните форму\b|\bбот для регистрации\b", text_lower)),
        }
        return fields

    def _check_condition(self, text: str, condition: Dict) -> bool:
        """Проверяет условие правила для текста."""
        text_lower = text.lower()

        # Проверка на наличие требуемых фраз
        if 'contains' in condition:
            contains_rules = condition['contains']
            if isinstance(contains_rules, list):
                if not any(phrase in text_lower for phrase in contains_rules):
                    return False
            elif isinstance(contains_rules, str) and contains_rules not in text_lower:
                return False

        # Проверка на отсутствие запрещенных фраз
        if 'not_contains' in condition:
            not_contains_rules = condition['not_contains']
            if isinstance(not_contains_rules, list):
                if any(phrase in text_lower for phrase in not_contains_rules):
                    return False
            elif isinstance(not_contains_rules, str) and not_contains_rules in text_lower:
                return False

        # Проверка регулярных выражений
        if 'contains_pattern' in condition:
            patterns = condition['contains_pattern']
            if isinstance(patterns, list):
                if not any(re.search(pattern, text) for pattern in patterns):
                    return False
            elif isinstance(patterns, str) and not re.search(patterns, text):
                return False

        # Проверка сущностей
        if 'requires_entity' in condition:
            entities = self.extract_entities(text)
            required_entities = condition['requires_entity']
            for entity_type in required_entities:
                if not entities.get(entity_type.lower(), []):
                    return False

        return True

    def classify_ad(self, text: str) -> Dict[str, Any]:
        """Определяет, является ли текст рекламой."""
        t = text.lower()

        # Явная реклама
        explicit_keywords = ['реклама', '#реклама', 'promo', 'ad', 'sponsored']
        # Неявная реклама
        implicit_keywords = ['скидк', 'акци', 'промокод', 'промо', 'распродаж']

        is_explicit_ad = any(k in t for k in explicit_keywords)
        is_implicit_ad = any(k in t for k in implicit_keywords)

        is_ad = is_explicit_ad or is_implicit_ad
        score = 0.9 if is_ad else 0.2

        return {"is_ad": is_ad, "score": score, "explicit": is_explicit_ad, "implicit": is_implicit_ad}

    def _calculate_risk_level(self, violations: List) -> Dict:
        """Рассчитывает уровень риска на основе нарушений."""
        total_risk = sum(self.severity_points.get(i['severity'], 1) for i in violations)
        if total_risk >= 8:
            risk_level = 'high'
        elif total_risk >= 4:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        return {
            'total_risk': total_risk,
            'risk_level': risk_level
        }

    def analyze(self, text: str) -> Dict[str, Any]:
        """Собирает все NLP-данные и применяет правила."""
        preprocessed_text = self.preprocess(text)
        entities = self.extract_entities(preprocessed_text)
        ad_info = self.classify_ad(preprocessed_text)
        pd_fields = self.detect_personal_data_fields(preprocessed_text)

        # Применяем правила
        violations = []
        for rule in self.rules:
            if self._check_condition(preprocessed_text, rule.get('condition', {})):
                violations.append({
                    'rule_id': rule['id'],
                    'rule_name': rule['name'],
                    'signal': rule['signal'],
                    'severity': rule.get('severity', 'medium'),
                    'category': rule.get('category', 'general')
                })

        # Расчет уровня риска
        risk_info = self._calculate_risk_level(violations)

        return {
            'text': preprocessed_text,
            'entities': entities,
            'ad_info': ad_info,
            'pd_fields': pd_fields,
            'violations': violations,
            'violation_count': len(violations),
            **risk_info
        }
