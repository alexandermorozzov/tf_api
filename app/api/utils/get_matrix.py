import os
import geopandas as gpd
import networkx as nx
import pickle
from loguru import logger
from shapely.geometry import Point
from app.api.utils.constants import REGIONS_DICT, REGIONS_CRS, DATA_PATH
from app.api.utils.urban_api import get_region_territories, _fetch_territories
from transport_frames.indicators.utils import availability_matrix

def load_graph(region_id: int, graph_type: str):
    graph_file = os.path.join(DATA_PATH, f'graphs/{region_id}_{graph_type}_graph.pickle')
    if not os.path.exists(graph_file):
        region_name = REGIONS_DICT.get(region_id, f"Region ID {region_id}")
        raise FileNotFoundError(f"{graph_type.capitalize()} graph for {region_name} not found.")
    
    with open(graph_file, "rb") as f:
        graph = pickle.load(f)
    
    return graph

def check_matrix_exists(region_id: int, matrix_type: str):
    matrix_file = os.path.join(DATA_PATH, f'matrices/{region_id}_{matrix_type}_matrix.pickle')
    return os.path.exists(matrix_file), matrix_file

def load_settlement_points(region_id: int) -> gpd.GeoDataFrame:
    tuple, towns_points = _fetch_territories(region_id)
    towns_points['geometry'] = towns_points['geometry'].representative_point()
    return towns_points

def to_pickle(data, file_path: str) -> None:
    with open(file_path, "wb") as f:
        pickle.dump(data, f)

def calculate_accessibility_matrix(graph, points, local_crs, region_id, matrix_type):
    try:
        acc_mx = availability_matrix(graph, points, points, local_crs=local_crs)
        return acc_mx
    except Exception as e:
        region_name = REGIONS_DICT.get(region_id, f"Region ID {region_id}")
        raise RuntimeError(f"Error calculating the {matrix_type} matrix for region {region_name}: {str(e)}")

def process_matrix():
    def process_calc_matrix(region_id, region_name, graph_type):
        matrix_exists, matrix_file = check_matrix_exists(region_id, graph_type)

        if matrix_exists:
            logger.info(f"{graph_type.capitalize()} matrix for {region_name} already exists.")
        else:
            logger.info(f"{graph_type.capitalize()} matrix for {region_name} not found. Creating...")
            graph = load_graph(region_id, graph_type)
            points = load_settlement_points(region_id)
            local_crs = REGIONS_CRS[region_id]
            acc_matrix = calculate_accessibility_matrix(graph, points, local_crs, region_id, graph_type)
            to_pickle(acc_matrix, matrix_file)
            logger.success(f'{graph_type.capitalize()} matrix for {region_name} has been successfully created.')

    for region_id, region_name in REGIONS_DICT.items():
        process_calc_matrix(region_id, region_name, 'car')
        process_calc_matrix(region_id, region_name, 'inter')