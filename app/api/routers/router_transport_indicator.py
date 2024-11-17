from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
import json
from loguru import logger
import shapely
import os
import pandas as pd
import geopandas as gpd
import networkx as nx
import pickle
from transport_frames.framebuilder.frame import Frame
from transport_frames.frame_grader.advanced_grade import AdvancedGrader
from transport_frames.indicators.indicator_terr import indicator_territory
from transport_frames.indicators.indicator_area import indicator_area, preprocess_service_accessibility
from transport_frames.indicators.utils import create_service_dict
from app.api.utils.constants import REGIONS_DICT, REGIONS_CRS, DATA_PATH, RESPONSE_MESSAGE
import app.api.utils.urban_api as ua
from enum import Enum

class Indicator(Enum):
    FRAME_GRADE = 'Оценка по каркасу'
    OVERALL_ASSESSMENT = 'Итоговая оценка по транспорту'
    
    TO_REGION_ADMIN_CENTER = 'Средняя удаленность до центра региона'
    TO_REG1 = 'Средняя удаленность до федеральных транспортных магистралей'
    FUEL_STATIONS_ACCESSIBILITY = 'Средняя доступность  автозаправочных станций'
    NUMBER_OF_FUEL_STATIONS = 'Количество автозаправочных станций'
    LOCAL_AERODROME_ACCESSIBILITY = 'Средняя доступность аэропортов местного значения'
    NUMBER_OF_LOCAL_AERODROME = 'Количество аэропортов местного значения'
    INTERNATIONAL_AERODROME_ACCESSIBILITY = 'Средняя доступность международных аэропортов'
    NUMBER_OF_INTERNATIONAL_AERODROME = 'Количество международных аэропортов'
    RAILWAY_STATIONS_ACCESSIBILITY = 'Средняя доступность остановок железнодорожного транспорта'
    NUMBER_OF_RAILWAY_STATIONS = 'Количество остановок железнодорожного транспорта'
    PORTS_ACCESSIBILITY = '123123'
    NUMBER_OF_PORTS = 'Количество портов'
    BUS_STOPS_ACCESSIBILITY = '123123'
    NUMBER_OF_BUS_STOPS = 'Количество остановок общественного транспорта'
    NUMBER_OF_WATER_OBJECTS = '123123'
    WATER_OBJECTS_ACCESSIBILITY = 'Доступность водных объектов'
    NUMBER_OF_NATURE_RESERVE = '123123'
    NATURE_RESERVE_ACCESSIBILITY = 'Доступность особо охраняемых природных территорий'
    TRAIN_PATHS_LENGTH = 'Общая протяженность железнодорожных путей'
    NUMBER_OF_BUS_ROUTES = 'Количество маршрутов общественного транспорта'
    TO_NEARESRT_DISTRICT_CENTER = 'Средняя доступность до центра района'
    TO_NEAREST_SETTLEMENT = 'Средняя доступность до близлежайшего крупного населенного пункта'
    ROAD_DENSITY = 'Плотность улично-дорожной сети'
    
    
INDICATORS_IDS = {
    Indicator.FRAME_GRADE : 193,
    Indicator.OVERALL_ASSESSMENT : 198,
    Indicator.TO_REGION_ADMIN_CENTER : 52,
    Indicator.TO_REG1 : 50,
    Indicator.FUEL_STATIONS_ACCESSIBILITY : 72,
    Indicator.NUMBER_OF_FUEL_STATIONS : 71,
    Indicator.LOCAL_AERODROME_ACCESSIBILITY : 83,
    Indicator.NUMBER_OF_LOCAL_AERODROME : 80,
    Indicator.INTERNATIONAL_AERODROME_ACCESSIBILITY : 82,
    Indicator.NUMBER_OF_INTERNATIONAL_AERODROME : 79,
    Indicator.RAILWAY_STATIONS_ACCESSIBILITY : 76,
    Indicator.NUMBER_OF_RAILWAY_STATIONS : 75,
    # Indicator.PORTS_ACCESSIBILITY : ,
    Indicator.NUMBER_OF_PORTS : 85,
    # Indicator.BUS_STOPS_ACCESSIBILITY : ,
    Indicator.NUMBER_OF_BUS_STOPS : 69,
    # Indicator.NUMBER_OF_WATER_OBJECTS : ,
    Indicator.WATER_OBJECTS_ACCESSIBILITY : 149,
    # Indicator.NUMBER_OF_NATURE_RESERVE : ,
    Indicator.NATURE_RESERVE_ACCESSIBILITY : 150,
    Indicator.TRAIN_PATHS_LENGTH : 74,
    Indicator.NUMBER_OF_BUS_ROUTES : 68,
    Indicator.TO_NEARESRT_DISTRICT_CENTER : 53,
    Indicator.TO_NEAREST_SETTLEMENT : 54,
    Indicator.ROAD_DENSITY : 60
}

router = APIRouter(tags=["Territory Calculation"])

def load_frame(region_id: int) -> nx.MultiDiGraph:
    frame_path = os.path.join(DATA_PATH, f'frames/{region_id}_frame.pickle')
    if not os.path.exists(frame_path):
        raise HTTPException(status_code=404, detail=f"Frame for region {region_id} not found.")
    with open(frame_path, 'rb') as f:
        frame = pickle.load(f)
    return frame

def load_graph(region_id: int):
    graph_file = os.path.join(DATA_PATH, f'graphs/{region_id}_car_graph.pickle')
    if not os.path.exists(graph_file):
        region_name = REGIONS_DICT.get(region_id, f"Region ID {region_id}")
        raise FileNotFoundError(f"Car graph for {region_name} not found.")
    
    with open(graph_file, "rb") as f:
        graph = pickle.load(f)
    
    return graph

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
    
    units_gdfs, towns_gdfs = ua.fetch_territories(region_id)
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

def _assess_indicator(region_id : int, projects_gdf : gpd.GeoDataFrame, regional_scenario_id : int | None = None) -> gpd.GeoDataFrame:

    # загружаем необходимые данные с бд
    railway_stations = ua.get_train_stations(region_id)
    railway_paths = ua.get_train_paths(region_id)
    bus_stops = ua.get_bus_stops(region_id)
    bus_routes = ua.get_bus_routes(region_id)
    fuel_stations = ua.get_fuel_stations(region_id)
    local_aerodrome = ua.get_airports(region_id)
    international_aerodrome = ua.get_international_airports(region_id)
    water_objects = ua.get_water_objects(region_id)
    nature_reserve = ua.get_protected_areas(region_id)

    region_admin_center = ua.get_region_admin_center(region_id)
    local_crs = REGIONS_CRS[region_id]

    services = create_service_dict(
                                railway_stations=railway_stations,
                                railway_paths=railway_paths,
                                bus_stops=bus_stops,
                                bus_routes=bus_routes,
                                fuel_stations=fuel_stations,
                                local_aerodrome=local_aerodrome,
                                international_aerodrome=international_aerodrome,
                                water_objects=water_objects,
                                nature_reserve=nature_reserve,          
                                local_crs=local_crs)
    
    graph = load_graph(region_id)
    graph.graph['crs'] = int(graph.graph['crs'])

    units_gdfs, towns_gdfs = ua.fetch_territories(region_id)
    towns_gdfs['geometry'] = towns_gdfs['geometry'].representative_point()
    # district_points = ua.get_region_admin_center(region_id)
    # settlement_points = ua.get_region_admin_center(region_id)
    district_points = ua.get_admin_centers(units_gdfs,towns_gdfs,3)
    settlement_points = ua.get_admin_centers(units_gdfs,towns_gdfs,4)
    districts_polygons = units_gdfs[3]

    ind = indicator_territory(graph=graph,
                        territory=projects_gdf,
                        services=services,
                        region_admin_center = region_admin_center,
                        district_points = district_points,
                        settlement_points = settlement_points,
                        districts = districts_polygons,
                        local_crs = local_crs
                        )
    return ind


@router.post('/{region_id}/transport_criteria')
def assess_geojson(region_id : int, geojson : dict, regional_scenario_id : int | None = None) -> list[float]:
    
    # перевод геоджсона в гдф
    gdf = gpd.GeoDataFrame.from_features(geojson['features'], crs=4326)

    cri = _assess_criteria(region_id, gdf, regional_scenario_id)

    return cri['overall_assessment'].tolist()

def _get_project_geometry(project_scenario_id : int, token : str):
    project_id = ua.get_scenario_by_id(project_scenario_id, token)['project']['project_id']
    project_info = ua.get_project_by_id(project_id, token)
    geometry_json = json.dumps(project_info['geometry'])
    return shapely.from_geojson(geometry_json)
    
def _get_regional_scenario_id(project_scenario_id : int, token : str):
    return None

def safe_cast(value, to_type, default=None):
    if pd.isna(value):  # Проверяем на NaN
        return default
    return to_type(value)

def _save_indicators(project_scenario_id : int, cri : gpd.GeoDataFrame, ind : gpd.GeoDataFrame, token : str):
    ... # im saving something
    # интерпретацию сохранять в поле commentary
    result_cri = cri.iloc[0]
    result_ind = ind.iloc[0]
    indicators = {
        Indicator.FRAME_GRADE: safe_cast(result_cri['grade'], float),
        Indicator.OVERALL_ASSESSMENT: safe_cast(result_cri['overall_assessment'], float),
        Indicator.TO_REGION_ADMIN_CENTER: safe_cast(result_ind['to_region_admin_center_km'], float),
        Indicator.TO_REG1: safe_cast(result_ind['to_reg_1_km'], float),
        Indicator.FUEL_STATIONS_ACCESSIBILITY: safe_cast(result_ind['fuel_stations_accessibility_min'], float),
        Indicator.NUMBER_OF_FUEL_STATIONS: safe_cast(result_ind['number_of_fuel_stations'], float),
        Indicator.LOCAL_AERODROME_ACCESSIBILITY: safe_cast(result_ind['local_aerodrome_accessibility_min'], float),
        Indicator.NUMBER_OF_LOCAL_AERODROME: safe_cast(result_ind['number_of_local_aerodrome'], float),
        Indicator.INTERNATIONAL_AERODROME_ACCESSIBILITY: safe_cast(result_ind['international_aerodrome_accessibility_min'], float),
        Indicator.NUMBER_OF_INTERNATIONAL_AERODROME: safe_cast(result_ind['number_of_international_aerodrome'], int),
        Indicator.RAILWAY_STATIONS_ACCESSIBILITY: safe_cast(result_ind['railway_stations_accessibility_min'], float),
        Indicator.NUMBER_OF_RAILWAY_STATIONS: safe_cast(result_ind['number_of_railway_stations'], float),
        # Indicator.PORTS_ACCESSIBILITY: safe_cast(result_ind['ports_accessibility_min'], float),
        Indicator.NUMBER_OF_PORTS: safe_cast(result_ind['number_of_ports'], int),
        # Indicator.BUS_STOPS_ACCESSIBILITY: safe_cast(result_ind['bus_stops_accessibility_min'], float),
        Indicator.NUMBER_OF_BUS_STOPS: safe_cast(result_ind['number_of_bus_stops'], int),
        # Indicator.NUMBER_OF_WATER_OBJECTS: safe_cast(result_ind['number_of_water_objects'], float),
        Indicator.WATER_OBJECTS_ACCESSIBILITY: safe_cast(result_ind['water_objects_accessibility_min'], float),
        # Indicator.NUMBER_OF_NATURE_RESERVE: safe_cast(result_ind['number_of_nature_reserve'], float),
        Indicator.NATURE_RESERVE_ACCESSIBILITY: safe_cast(result_ind['nature_reserve_accessibility_min'], float),
        Indicator.TRAIN_PATHS_LENGTH: safe_cast(result_ind['train_path_length_km'], float),
        Indicator.NUMBER_OF_BUS_ROUTES: safe_cast(result_ind['number_of_bus_routes'], int),
        Indicator.TO_NEARESRT_DISTRICT_CENTER: safe_cast(result_ind['to_nearest_district_center_km'], float),
        Indicator.TO_NEAREST_SETTLEMENT: safe_cast(result_ind['to_nearest_settlement_km'], float),
        Indicator.ROAD_DENSITY: safe_cast(result_ind['road_density_km/km2'], float)
    }

    for indicator, value in indicators.items():
        indicator_id = INDICATORS_IDS[indicator]
        ua.post_scenario_indicator(indicator_id, project_scenario_id, value, token)
        logger.success(f'ind={indicator} id={indicator_id} v={value}')

    for i in result_cri.index:
        logger.success(f'{i} : {result_cri.loc[i]}')
    for i in result_ind.index:
        logger.success(f'{i} : {result_cri.loc[i]}')
    # { scenario_id : project_scenario_id, commentary : my_interpr, value : foobar }

def _assess_and_save(region_id : int, project_scenario_id : int, token : str):
    project_geometry = _get_project_geometry(project_scenario_id, token)
    regional_scenario_id = _get_regional_scenario_id(project_scenario_id, token)
    project_gdf = gpd.GeoDataFrame(geometry=[project_geometry], crs=4326)
    cri = _assess_criteria(region_id, project_gdf, regional_scenario_id)
    ind = _assess_indicator(region_id, project_gdf, regional_scenario_id)
    _save_indicators(project_scenario_id, cri, ind, token) # im saving something to somewhere

def _get_token_from_request(request : Request) -> str:
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
        )
    # Проверяем формат: заголовок должен начинаться с 'Bearer '
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=400,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )
    
    token = auth_header[len("Bearer "):]

    if not token:
        raise HTTPException(
            status_code=400,
            detail="Token is missing in the authorization header"
        )
    
    return token



@router.post('/{region_id}/transport_criteria_project')
def assess_project(request : Request, region_id : int, project_scenario_id : int, background_tasks: BackgroundTasks):
    token = _get_token_from_request(request)
    background_tasks.add_task(_assess_and_save, region_id, project_scenario_id, token)
    return RESPONSE_MESSAGE