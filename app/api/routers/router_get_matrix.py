from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import os
import geopandas as gpd
import pickle
from app.api.utils.constants import DATA_PATH

router = APIRouter()

class AccessibilityMatrixModel(BaseModel):
    index: list[int]
    columns: list[int]
    values: list[list[float]]

def load_matrix(region_id: int):
    matrix_path = os.path.join(DATA_PATH, f'matrices/{region_id}_car_matrix.pickle')
    
    try:
        with open(matrix_path, 'rb') as f:
            matrix = pickle.load(f)
        return matrix
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Matrix file not found")

@router.get('/{region_id}/get_matrix', response_model=AccessibilityMatrixModel)
def get_accessibility_matrix(region_id: int) -> AccessibilityMatrixModel:
    matrix = load_matrix(region_id)
    
    res = {
        'index': matrix.index,
        'columns': matrix.columns,
        'values': matrix.values
    }

    return res