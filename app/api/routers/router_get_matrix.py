from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import os
from typing import List, Literal
import geopandas as gpd
import pickle
from shapely.geometry import Point
from app.api.utils.constants import REGIONS_DICT, REGIONS_CRS, DATA_PATH
from idu_clients import UrbanAPI
from transport_frames.indicators.utils import availability_matrix

router = APIRouter()

class AccessibilityMatrixModel(BaseModel):
    index: list[int]
    columns: list[int]
    values: list[list[float]]

def load_graph(region_id: int):
    graph_path = os.path.join(DATA_PATH, f'graphs/{region_id}_car_graph.pickle')
    
    try:
        with open(graph_path, 'rb') as f:
            graph = pickle.load(f)
        return graph
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Graph file not found")

async def fetch_region_points(region_id: int) -> gpd.GeoDataFrame:
    urban_api = UrbanAPI('http://10.32.1.107:5300')
    gdfs_dict = await urban_api.get_region_territories(region_id)

    if not gdfs_dict:
        raise HTTPException(status_code=404, detail="No territories found for the region")
    
    last_key, last_value = list(gdfs_dict.items())[-1]
    last_value['geometry'] = last_value['geometry'].representative_point()  
    return last_value

def get_local_crs(region_id: int):
    local_crs = REGIONS_CRS.get(region_id)
    if not local_crs:
        raise HTTPException(status_code=400, detail="CRS not found for the region")
    return local_crs

def calculate_accessibility_matrix(graph, points, local_crs):
    try:
        acc_mx = availability_matrix(graph, points, points, local_crs=local_crs)
        return acc_mx
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating matrix: {str(e)}")

@router.get('/regions/{region_id}/get_matrix')
async def get_accessibility_matrix(region_id: int) -> AccessibilityMatrixModel:
    graph = load_graph(region_id)
    points = await fetch_region_points(region_id)
    local_crs = get_local_crs(region_id)
    acc_mx = calculate_accessibility_matrix(graph.graph, points, local_crs)
    res = {
        'index': acc_mx.index.tolist(),
        'columns': acc_mx.columns.tolist(),
        'values': acc_mx.values.tolist()
    }

    return res