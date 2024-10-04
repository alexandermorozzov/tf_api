from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List
from transport_frames.frame_grader import advanced_grade

router = APIRouter()

class InterpretationRequest(BaseModel):
    grade: float = Field(ge=0.0, le=5.0, title="Оценка в диапазоне от 0.0 до 5.0", examples=[5])
    weight_r_stops: float = Field(ge=0.0, le=0.35, title="Наличие ЖД станций (0.0 или 0.35)", examples=[0.35])
    weight_b_stops: float = Field(ge=0.0, le=0.35, title="Наличие автобусных остановок (0.0 или 0.35)", examples=[0.35])
    weight_ferry: float = Field(ge=0.0, le=0.2, title="Наличие портов/причалов/переправ (0.0 или 0.2)", examples=[0.2])
    weight_aero: float = Field(ge=0.0, le=0.1, title="Наличие аэродромов (0.0 или 0.1)", examples=[0.1])
    car_access_quartile: int = Field(ge=1, le=4, title="Квартиль доступности для личного транспорта (от 1 до 4)", examples=[1])
    public_access_quartile: int = Field(ge=1, le=4, title="Квартиль доступности для общественного транспорта (от 1 до 4)", examples=[1])

@router.get('/interpretation')
def criteria_interpretation(request: InterpretationRequest = Depends()) -> list[str]:
    result = advanced_grade.interpretation(
            request.grade,  
            request.weight_r_stops, 
            request.weight_b_stops, 
            request.weight_ferry, 
            request.weight_aero,
            request.car_access_quartile,
            request.public_access_quartile
        )
    return result

