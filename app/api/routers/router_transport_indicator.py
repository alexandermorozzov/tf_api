from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
import json
from loguru import logger
import shapely
import os
import geopandas as gpd
import networkx as nx
import pickle
from transport_frames.framebuilder.frame import Frame
from transport_frames.frame_grader.advanced_grade import AdvancedGrader
from app.api.utils.constants import REGIONS_DICT, REGIONS_CRS, DATA_PATH, RESPONSE_MESSAGE
import app.api.utils.urban_api as ua
from enum import Enum

class Indicator(Enum):
    FRAME_GRADE = 'Оценка по каркасу'
    OVERALL_ASSESSMENT = 'Итоговая оценка по транспорту'

INDICATORS_IDS = {
    Indicator.FRAME_GRADE : 193,
    Indicator.OVERALL_ASSESSMENT : 198
}

router = APIRouter(tags=["Territory Calculation"])

def load_frame(region_id: int) -> nx.MultiDiGraph:
    frame_path = os.path.join(DATA_PATH, f'frames/{region_id}_frame.pickle')
    if not os.path.exists(frame_path):
        raise HTTPException(status_code=404, detail=f"Frame for region {region_id} not found.")
    with open(frame_path, 'rb') as f:
        frame = pickle.load(f)
    return frame

def load_matrices(region_id: int):
    car_matrix_path = os.path.join(DATA_PATH, f'matrices/{region_id}_car_matrix.pickle')
    inter_matrix_path = os.path.join(DATA_PATH, f'matrices/{region_id}_inter_matrix.pickle')

    with open(car_matrix_path, 'rb') as f:
        matrix_car = pickle.load(f)
    with open(inter_matrix_path, 'rb') as f:
        matrix_inter = pickle.load(f)

    return matrix_car, matrix_inter

def _gpsp_from_units_gdfs(units_gdfs : dict[int, gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
    deepest_level = max(units_gdfs.keys())
    return units_gdfs[deepest_level]


def _assess_criteria(region_id : int, projects_gdf : gpd.GeoDataFrame, regional_scenario_id : int | None = None) -> gpd.GeoDataFrame:
    
    projects_gdf['name'] = ''
    # загружаем фрейм и оцениваем каждый полигон гдфа по каркасу
    frame = load_frame(region_id)
    graded_territory = Frame.grade_territory(frame, projects_gdf)

    # получаем количество сервисов
    bus_stops = ua.get_bus_stops(region_id)
    train_stations = ua.get_train_stations(region_id)
    airports = ua.get_airports(region_id)
    ports = ua.get_ports(region_id)
    
    units_gdfs, towns_gdfs = ua._fetch_territories(region_id)
    towns_gdfs['geometry'] = towns_gdfs['geometry'].representative_point()
    settlements_polygons = _gpsp_from_units_gdfs(units_gdfs)
    if settlements_polygons is None:
        raise HTTPException(status_code=404, detail="Administrative units not found")
    
    # загружаем матрички по региону
    matrix_car, matrix_inter = load_matrices(region_id)

    local_crs = REGIONS_CRS[region_id] # local_crs = settlements_points.estimate_utm_crs()
    grader = AdvancedGrader(local_crs)

    # финальный гдф с территориями и всякими показателями
    cri = grader.get_criteria(
    graded_terr=graded_territory.reset_index(drop=True),
    points=towns_gdfs.reset_index(drop=True),
    polygons=settlements_polygons.reset_index(drop=True),
    adj_mx_drive=matrix_car,
    adj_mx_inter=matrix_inter,
    
        **({"b_stops": bus_stops.reset_index(drop=True)} if not bus_stops.empty else {}),
        **({"r_stops": train_stations.reset_index(drop=True)} if not train_stations.empty else {}),
        **({"aero": airports.reset_index(drop=True)} if not airports.empty else {}),
        **({"ferry": ports.reset_index(drop=True)} if not ports.empty else {})
    )
    return cri

@router.post('/transport_criteria')
def assess_geojson(region_id : int, geojson : dict, regional_scenario_id : int | None = None) -> list[float]:
    
    # перевод геоджсона в гдф
    gdf = gpd.GeoDataFrame.from_features(geojson['features'], crs=4326)

    cri = _assess_criteria(region_id, gdf, regional_scenario_id)

    return cri['overall_assessment'].tolist()

def _get_project_geometry(project_scenario_id : int, token : str):
    project_id = ua.get_scenario_by_id(project_scenario_id, token)['project_id']
    project_info = ua.get_project_by_id(project_id, token)
    geometry_json = json.dumps(project_info['geometry'])
    return shapely.from_geojson(geometry_json)
    
def _get_regional_scenario_id(project_scenario_id : int, token : str):
    return None

def _save_indicators(project_scenario_id : int, cri : gpd.GeoDataFrame):
    ... # im saving something
    # интерпретацию сохранять в поле commentary
    result = cri.iloc[0]
    indicators = {
        Indicator.FRAME_GRADE : result['grade'],
        Indicator.OVERALL_ASSESSMENT : result['overall_assessment']
    }
    for indicator, value in indicators.items():
        indicator_id = INDICATORS_IDS[indicator]
        logger.success(f'ind={indicator} id={indicator_id} v={value}')
    for i in result.index:
        logger.success(f'{i} : {result.loc[i]}')
    # { scenario_id : project_scenario_id, commentary : my_interpr, value : foobar }

def _assess_and_save(region_id : int, project_scenario_id : int, token : str):
    project_geometry = _get_project_geometry(project_scenario_id, token)
    regional_scenario_id = _get_regional_scenario_id(project_scenario_id, token)
    project_gdf = gpd.GeoDataFrame(geometry=[project_geometry], crs=4326)
    cri = _assess_criteria(region_id, project_gdf, regional_scenario_id)
    _save_indicators(project_scenario_id, cri) # im saving something to somewhere


@router.post('/{region_id}/transport_criteria_project')
def assess_project(region_id : int, project_scenario_id : int, token : str, background_tasks: BackgroundTasks):
    background_tasks.add_task(_assess_and_save, region_id, project_scenario_id, token)
    return RESPONSE_MESSAGE