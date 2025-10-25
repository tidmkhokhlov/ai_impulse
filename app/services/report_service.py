import io
import pandas as pd
from typing import List, Dict, Any


class ReportService:
    def incidents_to_xlsx(self, incidents: List[Dict[str, Any]], total_risk: int = 0, risk_level: str = 'low') -> bytes:
        """
        Преобразует список инцидентов в Excel с суммарным риском и категориями.

        :param incidents: Список инцидентов из RulesEngine
        :param total_risk: Суммарный риск
        :param risk_level: Уровень риска (low, medium, high)
        :return: Данные Excel в виде bytes
        """
        # Если нет инцидентов, создаем пустой DataFrame с заголовками
        if not incidents:
            df = pd.DataFrame(columns=['rule_id', 'message', 'severity', 'category'])
        else:
            df = pd.DataFrame(incidents)

        # Добавляем суммарный риск и уровень риска как отдельную строку
        summary_df = pd.DataFrame([{
            'rule_id': 'TOTAL',
            'message': 'Суммарный риск',
            'severity': total_risk,
            'category': f'Risk Level: {risk_level}'
        }])

        # Объединяем
        final_df = pd.concat([df, summary_df], ignore_index=True)

        # Сохраняем в Excel
        buf = io.BytesIO()
        final_df.to_excel(buf, index=False)
        return buf.getvalue()
