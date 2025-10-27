from fastapi import APIRouter
from typing import List

router = APIRouter()

_INCIDENTS = []

@router.get('/', response_model=List[dict])
async def list_incidents():
    return _INCIDENTS

@router.post('/', response_model=dict)
async def add_incident(item: dict):
    _INCIDENTS.append(item)
    return item
