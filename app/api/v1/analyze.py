from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import base64
import re
import traceback

from app.services.nlp_service import NLPService
from app.services.report_service import ReportService
from app.services.gigachat_service import generate_recommendation
from app.db.database import SessionLocal
from app.db.models import Incident

router = APIRouter()


nlp = NLPService("app/rules/rules_v5.yaml")
report_service = ReportService()


class AnalyzeRequest(BaseModel):
    text: str


# ===== /report endpoint =====
@router.post("/report", response_model=dict)
async def analyze_report(req: AnalyzeRequest):
    try:
        text = req.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Текст публикации пустой.")

        # 1. NLP-анализ (теперь включает правила)
        nlp_result = nlp.analyze(text)
        violations = nlp_result.get('violations', [])

        # Преобразуем violations в incidents для совместимости
        incidents = []
        for violation in violations:
            incidents.append({
                'rule_id': violation.get('rule_id', 'unknown'),
                'message': violation.get('rule_name', 'Нарушение'),
                'severity': violation.get('severity', 'medium'),
                'category': violation.get('category', 'general'),
                'signal': violation.get('signal', '')
            })

        # 2. Сохраняем инциденты в БД
        try:
            async with SessionLocal() as session:
                for inc in incidents:
                    incident = Incident(
                        text=text,
                        violation_type=inc.get('rule_id', 'unknown'),
                        recommendation=inc.get('recommendation', ''),
                        created_at=datetime.utcnow()
                    )
                    session.add(incident)
                await session.commit()
        except Exception as e_db:
            print("Ошибка при сохранении в БД:", e_db)
            traceback.print_exc()

        # 3. Генерация XLSX
        try:
            xlsx_bytes = report_service.violations_to_xlsx(nlp_result)
            encoded_xlsx = base64.b64encode(xlsx_bytes).decode('utf-8')
        except Exception as e_xlsx:
            print("Ошибка при генерации XLSX:", e_xlsx)
            traceback.print_exc()
            encoded_xlsx = None

        # 4. Получение рекомендаций GigaChat
        try:
            recs_ai = await generate_recommendation(text, incidents)
        except Exception as e_ai:
            print("Ошибка GigaChat:", e_ai)
            traceback.print_exc()
            recs_ai = "💡 Не удалось получить рекомендации от GigaChat."

        return {
            "incidents": incidents,
            "total_risk": nlp_result.get('total_risk', 0),
            "risk_level": nlp_result.get('risk_level', "low"),
            "xlsx_base64": encoded_xlsx,
            "recommendations": recs_ai,
            # Дополнительная информация из NLP анализа
            "entities": nlp_result.get('entities', {}),
            "ad_info": nlp_result.get('ad_info', {}),
            "pd_fields": nlp_result.get('pd_fields', {})
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {e}")