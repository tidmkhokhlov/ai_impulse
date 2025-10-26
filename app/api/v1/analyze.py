from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import base64
import re
import traceback

from app.services.nlp_service import NLPService
from app.services.rules_engine import RulesEngine
from app.services.report_service import ReportService
from app.services.gigachat_service import generate_recommendation
from app.db.database import SessionLocal
from app.db.models import Incident

router = APIRouter()

nlp = NLPService()
rules = RulesEngine()
report_service = ReportService()


class AnalyzeRequest(BaseModel):
    text: str


# ===== Markdown экранирование =====
def escape_markdown(text: str) -> str:
    escape_chars = r'_*\[\]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


# ===== /report endpoint =====
@router.post("/report", response_model=dict)
async def analyze_report(req: AnalyzeRequest):
    try:
        text = req.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Текст публикации пустой.")

        # 1. NLP-анализ и правила
        nlp_result = nlp.analyze(text)
        result = rules.evaluate(nlp_result)
        incidents = result.get('incidents', [])

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
            xlsx_bytes = report_service.incidents_to_xlsx(
                incidents=incidents,
                total_risk=result.get('total_risk', 0),
                risk_level=result.get('risk_level', "low")
            )
            encoded_xlsx = base64.b64encode(xlsx_bytes).decode('utf-8')
        except Exception as e_xlsx:
            print("Ошибка при генерации XLSX:", e_xlsx)
            traceback.print_exc()
            encoded_xlsx = None

        # 4. Получение рекомендаций GigaChat
        try:
            recs_ai = await generate_recommendation(text, incidents)
            recs_safe = escape_markdown(recs_ai)
        except Exception as e_ai:
            print("Ошибка GigaChat:", e_ai)
            traceback.print_exc()
            recs_safe = "💡 Не удалось получить рекомендации от GigaChat."

        return {
            "incidents": incidents,
            "total_risk": result.get('total_risk', 0),
            "risk_level": result.get('risk_level', "low"),
            "xlsx_base64": encoded_xlsx,
            "recommendations": recs_safe
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {e}")
