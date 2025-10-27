from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import base64
import traceback

from app.services.nlp_service import NLPService
from app.services.report_service import ReportService
from app.services.gigachat_service import generate_recommendation, find_ads
from app.db.database import SessionLocal
from app.db.models import Incident

router = APIRouter()

nlp = NLPService("app/rules/rules_v6.yaml")
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

        # 1. Проверяем через GigaChat, является ли текст рекламой
        ad_check_result = None
        try:
            ad_check_result = await find_ads(text)
            print(f"[GigaChat Ad Check] Результат: {ad_check_result}")

            if ad_check_result == "Не реклама":
                return {
                    "incidents": [],
                    "total_risk": 0,
                    "risk_level": "low",
                    "xlsx_base64": None,
                    "recommendations": "✅ Текст не является рекламой. Дальнейшая проверка не требуется.",
                    "entities": {},
                    "ad_info": {"is_ad": False, "gigachat_check": ad_check_result},
                    "pd_fields": {},
                    "gigachat_ad_check": ad_check_result
                }
        except Exception as e_ad_check:
            print("Ошибка при проверке рекламы через GigaChat:", e_ad_check)
            traceback.print_exc()

        # 2. NLP-анализ
        nlp_result = nlp.analyze(text)
        violations = nlp_result.get('violations', [])
        total_risk = nlp_result.get('total_risk', 0)
        risk_level = nlp_result.get('risk_level', 'low')

        # Преобразуем violations в incidents для отчета
        incidents = []
        for violation in violations:
            law_info = violation.get('law', {})
            incident_data = {
                'rule_id': violation.get('rule_id', 'unknown'),
                'rule_name': violation.get('rule_name', 'Нарушение'),
                'severity': violation.get('severity', 'medium'),
                'category': violation.get('category', 'general'),
                'signal': violation.get('signal', ''),
                'law': law_info
            }
            incidents.append(incident_data)

        # 3. Сохраняем данные в БД
        try:
            async with SessionLocal() as session:
                for violation in violations:
                    law_info = violation.get('law', {})

                    incident = Incident(
                        text=text,
                        rule_id=violation.get('rule_id', 'unknown'),
                        rule_name=violation.get('rule_name', 'Нарушение'),
                        severity=violation.get('severity', 'medium'),
                        category=violation.get('category', 'general'),
                        signal=violation.get('signal', ''),
                        закон=law_info.get('name', ''),
                        статья=str(law_info.get('article', '')),
                        выдержка_описание=law_info.get('excerpt', ''),
                        штраф=law_info.get('risk', ''),
                        created_at=datetime.utcnow()
                    )
                    session.add(incident)

                await session.commit()

        except Exception as e_db:
            print("Ошибка при сохранении в БД:", e_db)
            traceback.print_exc()

        # 4. Генерация XLSX
        try:
            xlsx_bytes = report_service.violations_to_xlsx(nlp_result)
            encoded_xlsx = base64.b64encode(xlsx_bytes).decode('utf-8')
        except Exception as e_xlsx:
            print("Ошибка при генерации XLSX:", e_xlsx)
            traceback.print_exc()
            encoded_xlsx = None

        # 5. Получение рекомендаций GigaChat
        try:
            recs_ai = await generate_recommendation(text, incidents)
        except Exception as e_ai:
            print("Ошибка GigaChat:", e_ai)
            traceback.print_exc()
            recs_ai = "💡 Не удалось получить рекомендации от GigaChat."

        return {
            "incidents": incidents,
            "total_risk": total_risk,
            "risk_level": risk_level,
            "xlsx_base64": encoded_xlsx,
            "recommendations": recs_ai,
            "entities": nlp_result.get('entities', {}),
            "ad_info": nlp_result.get('ad_info', {}),
            "pd_fields": nlp_result.get('pd_fields', {}),
            "gigachat_ad_check": ad_check_result if ad_check_result else "Проверка не выполнена"
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {e}")