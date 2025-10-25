from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.nlp_service import NLPService
from app.services.rules_engine import RulesEngine
from app.services.report_service import ReportService

router = APIRouter()

nlp = NLPService()
rules = RulesEngine()  # will load default rules from yaml
report_service = ReportService()

class AnalyzeRequest(BaseModel):
    text: str

@router.post("/", response_model=dict)
async def analyze(req: AnalyzeRequest):
    try:
        nlp_result = nlp.analyze(req.text)
        incidents = rules.evaluate(nlp_result)
        return {"nlp": nlp_result, "incidents": incidents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/report", response_model=dict)
async def analyze_report(req: AnalyzeRequest):
    """Возвращает xlsx в виде base64-encoded содержимого (упрощённо)"""
    try:
        nlp_result = nlp.analyze(req.text)
        incidents = rules.evaluate(nlp_result)
        xlsx_bytes = report_service.incidents_to_xlsx(incidents)
        # For a real app: return StreamingResponse with proper headers.
        import base64
        encoded = base64.b64encode(xlsx_bytes).decode('utf-8')
        return {"incidents": incidents, "xlsx_base64": encoded}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
