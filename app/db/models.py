# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.db.database import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text)
    rule_id = Column(String, index=True)
    rule_name = Column(String)
    severity = Column(String)
    category = Column(String)
    signal = Column(String)
    закон = Column(String)  # law_name
    статья = Column(String)  # law_article  
    выдержка_описание = Column(Text)  # law_excerpt
    штраф = Column(Text)  # law_risk
    created_at = Column(DateTime, default=datetime.utcnow)