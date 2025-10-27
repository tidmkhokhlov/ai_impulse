import io
import pandas as pd
from typing import List, Dict, Any


class ReportService:
    def violations_to_xlsx(self, nlp_result: Dict[str, Any]) -> bytes:
        """
        Преобразует результат NLP анализа в Excel отчет.

        :param nlp_result: Результат из NLPService.analyze()
        :return: Данные Excel в виде bytes
        """
        violations = nlp_result.get('violations', [])
        total_risk = nlp_result.get('total_risk', 0)
        risk_level = nlp_result.get('risk_level', 'low')

        # Создаем основной DataFrame с нарушениями
        if not violations:
            df = pd.DataFrame(columns=[
                'rule_id', 'rule_name', 'severity', 'category', 'signal'
            ])
        else:
            df = pd.DataFrame([{
                'rule_id': v.get('rule_id', ''),
                'rule_name': v.get('rule_name', ''),
                'severity': v.get('severity', ''),
                'category': v.get('category', ''),
                'signal': v.get('signal', '')
            } for v in violations])

        # Создаем сводную информацию
        summary_data = {
            'total_risk': [total_risk],
            'risk_level': [risk_level],
            'violation_count': [len(violations)],
            'text_preview': [
                nlp_result.get('text', '')[:100] + '...' if len(nlp_result.get('text', '')) > 100 else nlp_result.get(
                    'text', '')]
        }

        # Добавляем информацию о рекламе
        ad_info = nlp_result.get('ad_info', {})
        summary_data['is_ad'] = [ad_info.get('is_ad', False)]
        summary_data['ad_score'] = [ad_info.get('score', 0)]
        summary_data['explicit_ad'] = [ad_info.get('explicit', False)]
        summary_data['implicit_ad'] = [ad_info.get('implicit', False)]

        # Добавляем информацию о персональных данных
        pd_fields = nlp_result.get('pd_fields', {})
        summary_data['has_phone_field'] = [pd_fields.get('phone', False)]
        summary_data['has_email_field'] = [pd_fields.get('email', False)]
        summary_data['has_name_field'] = [pd_fields.get('name_prompt', False)]
        summary_data['has_form_bot'] = [pd_fields.get('form_or_bot', False)]

        summary_df = pd.DataFrame(summary_data)

        # Создаем информацию о сущностях
        entities = nlp_result.get('entities', {})
        entities_data = {
            'entity_type': [],
            'values': []
        }

        for entity_type, values in entities.items():
            if values:  # только если есть значения
                entities_data['entity_type'].append(entity_type)
                entities_data['values'].append(', '.join(values) if isinstance(values, list) else str(values))

        entities_df = pd.DataFrame(entities_data) if entities_data['entity_type'] else pd.DataFrame(
            columns=['entity_type', 'values'])

        # Сохраняем в Excel с несколькими листами
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            # Лист с нарушениями
            if not df.empty:
                df.to_excel(writer, sheet_name='Нарушения', index=False)
            else:
                pd.DataFrame({'Сообщение': ['Нарушений не обнаружено']}).to_excel(
                    writer, sheet_name='Нарушения', index=False
                )

            # Лист со сводной информацией
            summary_df.to_excel(writer, sheet_name='Сводка', index=False)

            # Лист с сущностями
            if not entities_df.empty:
                entities_df.to_excel(writer, sheet_name='Сущности', index=False)

            # Лист со статистикой по нарушениям
            if not df.empty:
                severity_stats = df['severity'].value_counts().reset_index()
                severity_stats.columns = ['severity', 'count']
                severity_stats.to_excel(writer, sheet_name='Статистика', index=False)

        return buf.getvalue()

    # Метод для обратной совместимости
    def incidents_to_xlsx(self, incidents: List[Dict[str, Any]], total_risk: int = 0, risk_level: str = 'low') -> bytes:
        """
        Старый метод для обратной совместимости.
        """
        nlp_result = {
            'violations': incidents,
            'total_risk': total_risk,
            'risk_level': risk_level,
            'text': '',
            'ad_info': {},
            'pd_fields': {},
            'entities': {}
        }
        return self.violations_to_xlsx(nlp_result)