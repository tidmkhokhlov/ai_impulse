import yaml
from pathlib import Path
import re

class RulesEngine:
    def __init__(self, rules_path: str = None):
        if rules_path:
            self.rules = self.load_rules(Path(rules_path))
        else:
            # Авто-поиск rules_v4.yaml относительно корня проекта
            # Предполагается, что структура:
            # project_root/
            # ├── app/services/rules_engine.py
            # └── rules/rules_v4.yaml
            base_dir = Path(__file__).resolve().parent.parent.parent  # корень проекта
            default_path = base_dir / 'rules' / 'rules_v4.yaml'
            self.rules = self.load_rules(default_path)

        self.severity_points = {'high': 5, 'medium': 2, 'low': 1}

    def load_rules(self, path: Path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                doc = yaml.safe_load(f)
            return doc.get('rules', [])
        except FileNotFoundError:
            print(f"[RulesEngine] Файл правил не найден: {path}")
            return []

    def evaluate(self, nlp_result):
        incidents = []
        text = nlp_result.get('text', '').lower()

        for rule in self.rules:
            rule_id = rule.get('id')
            severity = rule.get('severity', 'medium')
            category = rule.get('category', 'general')
            condition = rule.get('condition', {})

            matched = False

            # Проверка contains
            for phrase in condition.get('contains', []):
                if phrase.lower() in text:
                    matched = True
                    break

            # Проверка contains_pattern
            for pattern in condition.get('contains_pattern', []):
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break

            # not_contains
            if matched and 'not_contains' in condition:
                for phrase in condition['not_contains']:
                    if phrase.lower() in text:
                        matched = False
                        break

            # requires_entity
            if 'requires_entity' in condition and nlp_result.get('ad', {}).get('is_ad', False):
                for entity in condition['requires_entity']:
                    if not nlp_result.get(entity.lower()):
                        matched = True

            # сбор персональных данных
            if rule_id in ['R3', 'R12']:
                pd_fields = nlp_result.get('pd_fields', {})
                if any(pd_fields.values()) and 'согласие' not in text and 'согласен' not in text:
                    matched = True

            # специальные слова для R1
            if rule_id == 'R1':
                sale_keywords = ['скидк', 'акци', 'промокод', 'промо']
                has_sale = any(k in text for k in sale_keywords)
                # учитываем explicit маркировку
                if has_sale and not nlp_result.get('ad', {}).get('explicit', False):
                    matched = True

            if matched:
                incidents.append({
                    'rule_id': rule_id,
                    'message': rule.get('name'),
                    'severity': severity,
                    'category': category
                })

        # Суммарный риск
        total_risk = sum(self.severity_points.get(i['severity'], 1) for i in incidents)
        if total_risk >= 8:
            risk_level = 'high'
        elif total_risk >= 4:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        return {
            'incidents': incidents,
            'total_risk': total_risk,
            'risk_level': risk_level
        }
