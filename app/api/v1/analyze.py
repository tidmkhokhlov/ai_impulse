from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.nlp_service import NLPService
from app.services.rules_engine import RulesEngine
from app.services.report_service import ReportService
from app.db.database import SessionLocal
from app.db.models import Incident
import base64

router = APIRouter()

nlp = NLPService()
rules = RulesEngine()  # Авто-загрузка правил из rules/rules_v4.yaml
report_service = ReportService()

class AnalyzeRequest(BaseModel):
    text: str

@router.post("/", response_model=dict)
async def analyze(req: AnalyzeRequest):
    """
    Возвращает NLP-анализ текста и список инцидентов с уровнем риска.
    """
    try:
        nlp_result = nlp.analyze(req.text)
        result = rules.evaluate(nlp_result)
        return {
            "nlp": nlp_result,
            "incidents": result['incidents'],
            "total_risk": result['total_risk'],
            "risk_level": result['risk_level']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report", response_model=dict)
async def analyze_report(req: AnalyzeRequest):
    """
    Возвращает XLSX-отчет в base64-encoded виде вместе с инцидентами и суммарным риском.
    """
    try:
        nlp_result = nlp.analyze(req.text)
        result = rules.evaluate(nlp_result)

        # Генерация Excel с суммарным риском
        xlsx_bytes = report_service.incidents_to_xlsx(
            incidents=result['incidents'],
            total_risk=result['total_risk'],
            risk_level=result['risk_level']
        )
        encoded = base64.b64encode(xlsx_bytes).decode('utf-8')

        return {
            "incidents": result['incidents'],
            "total_risk": result['total_risk'],
            "risk_level": result['risk_level'],
            "xlsx_base64": encoded
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
