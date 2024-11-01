from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Literal
import os
import geopandas as gpd
import pickle
from app.api.utils.constants import DATA_PATH

router = APIRouter(tags=["Accessibility Matrix"])

class AccessibilityMatrixModel(BaseModel):
    index: list[int]
    columns: list[int]
    values: list[list[float]]


def load_matrix(region_id: int, graph_type: Literal['car', 'inter']):
    matrix_path = os.path.join(DATA_PATH, f'matrices/{region_id}_{graph_type}_matrix.pickle')
    
    try:
        with open(matrix_path, 'rb') as f:
            matrix = pickle.load(f)
        return matrix
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"{graph_type.capitalize()} matrix file not found for region {region_id}")

@router.get('/{region_id}/get_matrix', response_model=AccessibilityMatrixModel)
def get_accessibility_matrix(region_id: int, graph_type: Literal['car', 'inter']) -> AccessibilityMatrixModel:
    matrix = load_matrix(region_id, graph_type)
    
    res = {
        'index': matrix.index,
        'columns': matrix.columns,
        'values': matrix.values
    }

    return res