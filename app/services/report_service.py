import io
import pandas as pd
from typing import List, Dict, Any


class ReportService:
    def violations_to_xlsx(self, nlp_result: Dict[str, Any]) -> bytes:
        """
        Преобразует результат NLP анализа в Excel отчет только с нарушениями и юридической информацией.

        :param nlp_result: Результат из NLPService.analyze()
        :return: Данные Excel в виде bytes
        """
        violations = nlp_result.get('violations', [])

        # Создаем DataFrame только с нужными колонками
        if not violations:
            # Если нет нарушений, создаем пустой DataFrame с заголовками
            df = pd.DataFrame(columns=[
                'rule_id', 'rule_name', 'severity', 'category', 'signal',
                'закон', 'статья', 'выдержка_описание', 'штраф'
            ])
        else:
            violations_data = []
            for v in violations:
                law_info = v.get('law', {})
                violation_data = {
                    'rule_id': v.get('rule_id', ''),
                    'rule_name': v.get('rule_name', ''),
                    'severity': v.get('severity', ''),
                    'category': v.get('category', ''),
                    'signal': v.get('signal', ''),
                    'закон': law_info.get('name', ''),
                    'статья': str(law_info.get('article', '')),
                    'выдержка_описание': law_info.get('excerpt', ''),
                    'штраф': law_info.get('risk', '')
                }
                violations_data.append(violation_data)

            df = pd.DataFrame(violations_data)

        # Сохраняем в Excel с одним листом
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Нарушения', index=False)

            # Настраиваем ширину колонок для лучшего отображения
            worksheet = writer.sheets['Нарушения']
            worksheet.column_dimensions['A'].width = 15  # rule_id
            worksheet.column_dimensions['B'].width = 35  # rule_name
            worksheet.column_dimensions['C'].width = 12  # severity
            worksheet.column_dimensions['D'].width = 15  # category
            worksheet.column_dimensions['E'].width = 25  # signal
            worksheet.column_dimensions['F'].width = 25  # закон
            worksheet.column_dimensions['G'].width = 8  # статья
            worksheet.column_dimensions['H'].width = 60  # выдержка_описание
            worksheet.column_dimensions['I'].width = 40  # штраф

        return buf.getvalue()

    # Метод для обратной совместимости
    def incidents_to_xlsx(self, incidents: List[Dict[str, Any]], total_risk: int = 0, risk_level: str = 'low') -> bytes:
        """
        Старый метод для обратной совместимости.
        """
        # Преобразуем incidents в violations формат
        violations = []
        for incident in incidents:
            violation = {
                'rule_id': incident.get('rule_id', ''),
                'rule_name': incident.get('message', ''),
                'severity': incident.get('severity', 'medium'),
                'category': incident.get('category', 'general'),
                'signal': incident.get('signal', ''),
                'law': incident.get('law', {})
            }
            violations.append(violation)

        nlp_result = {
            'violations': violations,
            'total_risk': total_risk,
            'risk_level': risk_level,
            'text': '',
            'ad_info': {},
            'pd_fields': {},
            'entities': {}
        }
        return self.violations_to_xlsx(nlp_result)