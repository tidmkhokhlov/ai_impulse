import yaml
from pathlib import Path

class RulesEngine:
    def __init__(self, rules_path: str = None):
        if rules_path:
            self.rules = self.load_rules(Path(rules_path))
        else:
            # default path inside package
            self.rules = self.load_rules(Path('rules/rules_v1.yaml'))

    def load_rules(self, path: Path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                doc = yaml.safe_load(f)
            return doc.get('rules', [])
        except FileNotFoundError:
            return []

    def evaluate(self, nlp_result):
        incidents = []
        text = nlp_result.get('text', '').lower()

        # Heuristic rules (also based on rules yaml)
        # R1: If there are sale keywords but no explicit ad labeling
        if any(k in text for k in ['скидк', 'акци', 'промокод', 'промо']) and not nlp_result['ad']['is_ad']:
            incidents.append({
                'rule_id': 'R1',
                'message': 'Видна акция/скидка, но нет маркировки рекламы',
                'severity': 'high'
            })

        # R2: Ad without INN
        if nlp_result['ad']['is_ad'] and not nlp_result.get('inn'):
            incidents.append({
                'rule_id': 'R2',
                'message': 'Реклама без ИНН',
                'severity': 'high'
            })

        # R3: PD collection without consent
        pd = nlp_result.get('pd_fields', {})
        if any(pd.values()) and ('согласие' not in text and 'согласен' not in text):
            incidents.append({
                'rule_id': 'R3',
                'message': 'Сбор персональных данных без явного согласия',
                'severity': 'high'
            })

        return incidents
