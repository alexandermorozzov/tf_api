from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
import json
from loguru import logger
import shapely
import os
import pandas as pd
import geopandas as gpd
import networkx as nx
import pickle
from transport_frames.indicators.indicator_area import indicator_area, preprocess_service_accessibility
from transport_frames.indicators.utils import create_service_dict
from app.api.utils.constants import REGIONS_DICT, REGIONS_CRS, DATA_PATH, RESPONSE_MESSAGE
import app.api.utils.urban_api as ua
from enum import Enum

class Indicator(Enum):
    NUMBER_OF_RAILWAY_STATIONS = 'Количество остановок железнодорожного транспорта'
    RAILWAY_STATIONS_ACCESSIBILITY = 'Средняя доступность остановок железнодорожного транспорта'
    NUMBER_OF_FUEL_STATIONS = 'Количество автозаправочных станций'
    FUEL_STATIONS_ACCESSIBILITY = 'Средняя доступность автозаправочных станций'
    NUMBER_OF_PORTS = 'Количество портов'
    PORTS_ACCESSIBILITY = 'Средняя доступность портов'
    NUMBER_OF_LOCAL_AERODROME = 'Количество аэропортов местного значения'
    LOCAL_AERODROME_ACCESSIBILITY = 'Средняя доступность аэропортов местного значения' 
    NUMBER_OF_INTERNATIONAL_AERODROME = 'Количество международных аэропортов'
    INTERNATIONAL_AERODROME_ACCESSIBILITY = 'Средняя доступность международных аэропортов'
    NUMBER_OF_BUS_STOPS = 'Количество остановок общественного транспорта'
    CONNECTIVITY_DRIVE = 'Связанность населенных пунктов'
    CONNECTIVITY_INTER = 'Связанность общественным транспортом'
    TO_REGION_ADMIN_CENTER = 'Средняя удаленность до центра региона'
    TO_REG1 = 'Средняя удаленность до федеральных транспортных магистралей'
    TRAIN_PATH_LENGTH = 'Общая протяженность железнодорожных путей'
    NUMBER_OF_BUS_ROUTES = 'Количество маршрутов общественного транспорта'
    REG1_LENGTH = 'Протяженность дорог федерального значения'
    REG2_LENGTH = 'Протяженность дорог регионального значения'
    REG3_LENGTH = 'Протяженность дорог местного значения'
    ROAD_DENSITY = 'Плотность улично-дорожной сети'

INDICATORS_IDS = {
    Indicator.NUMBER_OF_RAILWAY_STATIONS : 75,
    Indicator.RAILWAY_STATIONS_ACCESSIBILITY : 76,
    Indicator.NUMBER_OF_FUEL_STATIONS : 71,
    Indicator.FUEL_STATIONS_ACCESSIBILITY : 72,
    Indicator.NUMBER_OF_PORTS : 85,
    # Indicator.PORTS_ACCESSIBILITY ,
    Indicator.NUMBER_OF_LOCAL_AERODROME : 80,
    Indicator.LOCAL_AERODROME_ACCESSIBILITY : 83,
    Indicator.NUMBER_OF_INTERNATIONAL_AERODROME : 79,
    Indicator.INTERNATIONAL_AERODROME_ACCESSIBILITY : 82,
    Indicator.NUMBER_OF_BUS_STOPS : 69,
    Indicator.CONNECTIVITY_DRIVE : 59,
    Indicator.CONNECTIVITY_INTER : 266,
    Indicator.TO_REGION_ADMIN_CENTER : 52,
    Indicator.TO_REG1 : 50,
    Indicator.TRAIN_PATH_LENGTH : 74,
    Indicator.NUMBER_OF_BUS_ROUTES : 68,
    Indicator.REG1_LENGTH : 62,
    Indicator.REG2_LENGTH : 63,
    Indicator.REG3_LENGTH : 64,
    Indicator.ROAD_DENSITY : 60
}

router = APIRouter(tags=["Region Calculation"])

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

def _assess_region_indicators(region_id : int) -> list[gpd.GeoDataFrame]:
    car_graph = load_graph(region_id)
    car_graph.graph['crs'] = int(car_graph.graph['crs'])
    matrix_car, matrix_inter = load_matrices(region_id)

    railway_stations = ua.get_train_stations(region_id)
    railway_paths = ua.get_train_paths(region_id)
    bus_stops = ua.get_bus_stops(region_id)
    bus_routes = ua.get_bus_routes(region_id)
    fuel_stations = ua.get_fuel_stations(region_id)
    local_aerodrome = ua.get_airports(region_id)
    international_aerodrome = ua.get_international_airports(region_id)
    water_objects = ua.get_water_objects(region_id)
    nature_reserve = ua.get_protected_areas(region_id)
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
    
    units_gdfs, towns_gdfs = ua.fetch_territories(region_id)
    towns_gdfs['geometry'] = towns_gdfs['geometry'].representative_point()
    region_polygon = units_gdfs[2]
    districts_polygons = units_gdfs[3]
    settlements_polygons = units_gdfs[4]
    region_admin_center = ua.get_region_admin_center(region_id)
    
    preprocessed_accessibility = preprocess_service_accessibility(towns_gdfs, services, car_graph, local_crs)
    ind_area = indicator_area(car_graph, [region_polygon, districts_polygons, settlements_polygons], preprocessed_accessibility, services, local_crs, matrix_car, matrix_inter, region_admin_center)

    return ind_area

def safe_cast(value, to_type, default=None):
    if pd.isna(value): 
        return default
    return to_type(value)

def _save_indicators(ind_area: list[gpd.GeoDataFrame]): 
    for gdf in ind_area:
        for territory_id, row in gdf.iterrows():  
            indicators = {
                Indicator.NUMBER_OF_RAILWAY_STATIONS: safe_cast(row['number_of_railway_stations'], int),
                Indicator.RAILWAY_STATIONS_ACCESSIBILITY : safe_cast(row['railway_stations_accessibility_min'], float),
                Indicator.NUMBER_OF_FUEL_STATIONS : safe_cast(row['number_of_fuel_stations'], int),
                Indicator.FUEL_STATIONS_ACCESSIBILITY : safe_cast(row['fuel_stations_accessibility_min'], float),
                Indicator.NUMBER_OF_PORTS : safe_cast(row['number_of_ports'], int),
                Indicator.NUMBER_OF_LOCAL_AERODROME : safe_cast(row['number_of_local_aerodrome'], int),
                Indicator.LOCAL_AERODROME_ACCESSIBILITY : safe_cast(row['local_aerodrome_accessibility_min'], float),
                Indicator.NUMBER_OF_INTERNATIONAL_AERODROME : safe_cast(row['number_of_international_aerodrome'], int),
                Indicator.INTERNATIONAL_AERODROME_ACCESSIBILITY : safe_cast(row['international_aerodrome_accessibility_min'], int),
                Indicator.NUMBER_OF_BUS_STOPS : safe_cast(row['number_of_bus_stops'], float),
                Indicator.CONNECTIVITY_DRIVE : safe_cast(row['connectivity_drive_min'], float),
                Indicator.CONNECTIVITY_INTER : safe_cast(row['connectivity_inter_min'], float),
                Indicator.TO_REGION_ADMIN_CENTER :safe_cast(row['to_region_admin_center_km'], float),
                Indicator.TO_REG1 : safe_cast(row['to_reg_1_km'], float),
                Indicator.TRAIN_PATH_LENGTH : safe_cast(row['train_path_length_km'], float),
                Indicator.NUMBER_OF_BUS_ROUTES : safe_cast(row['number_of_bus_routes'], int),
                Indicator.REG1_LENGTH : safe_cast(row['reg1_length_km'], float),
                Indicator.REG2_LENGTH : safe_cast(row['reg2_length_km'], float),
                Indicator.REG3_LENGTH : safe_cast(row['reg3_length_km'], float),
                Indicator.ROAD_DENSITY : safe_cast(row['road_density_km/km2'], float)
            }
            for indicator, value in indicators.items():
                indicator_id = INDICATORS_IDS[indicator]
                ua.post_territory_indicator(indicator_id, territory_id, value)
                logger.success('Calculations completed')
                # logger.info(f'terr={territory_id} ind={indicator} id={indicator_id} v={value}')
                # ua.save_territory_indicatordfdfsdfsdfs(territory_id, indicator_id, value)


def _assess_and_save(region_id : int):
    ind_area = _assess_region_indicators(region_id)
    _save_indicators(ind_area)

@router.post('/{region_id}/transport_indicator_region')
def assess_region(region_id : int, background_tasks: BackgroundTasks):
    background_tasks.add_task(_assess_and_save, region_id)
    return RESPONSE_MESSAGE