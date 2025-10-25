from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text)
    violation_type = Column(String)
    recommendation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class LawRule(Base):
    __tablename__ = "law_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    pattern = Column(String)
    description = Column(Text)
