from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Literal
import os
from loguru import logger
from app.api.utils.constants import REGIONS_DICT, REGIONS_CRS, DATA_PATH
from app.api.utils.get_matrix import load_graph, load_settlement_points, to_pickle, calculate_accessibility_matrix

router = APIRouter()

class RecalculateMatrixResponse(BaseModel):
    status: str
    region_id: int
    graph_type: str
    message: str
    matrix_file: str

async def process_graph(region_id: int, graph_type: str, matrix_file: str):
    region_name = REGIONS_DICT.get(region_id, f"Region ID {region_id}")
    
    try:
        graph = load_graph(region_id, graph_type)
        points = await load_settlement_points(region_id)
        local_crs = REGIONS_CRS[region_id]
        acc_matrix = calculate_accessibility_matrix(graph, points, local_crs, region_id, graph_type)
        to_pickle(acc_matrix, matrix_file)
        logger.success(f'{graph_type.capitalize()} matrix for {region_name} has been successfully created.')
    except Exception as e:
        logger.error(f"Error while recalculating the {graph_type} matrix for region {region_name}: {str(e)}")

@router.put('/{region_id}/recalculate_matrix', response_model=RecalculateMatrixResponse)
def recalculate_accessibility_matrix(region_id: int, graph_type: Literal['car', 'inter'], background_tasks: BackgroundTasks) -> RecalculateMatrixResponse:
    matrix_file = os.path.join(DATA_PATH, f'matrices/{region_id}_{graph_type}_matrix.pickle')
    background_tasks.add_task(process_graph, region_id, graph_type, matrix_file)
    
    return RecalculateMatrixResponse(
        status="in_progress",
        region_id=region_id,
        graph_type=graph_type,
        message=f"Matrix recalculation for region {region_id} and graph type '{graph_type}' has started.",
        matrix_file=matrix_file
    )