import os
import pandas as pd
import geopandas as gpd
import osmnx as ox 
import networkx as nx
import pickle
from loguru import logger
from app.api.utils.constants import REGIONS_DICT, REGIONS_CRS, DATA_PATH
from transport_frames.graphbuilder.graph import Graph


def check_graph_exists(region_id : int):
    graph_file = os.path.join(DATA_PATH, f'graphs/{region_id}_car_graph.pickle')
    return os.path.exists(graph_file), graph_file

def create_graph(region_id : int, polygon : gpd.GeoDataFrame):
    crs = REGIONS_CRS[region_id]
    g = Graph.from_polygon(polygon, crs=f'{crs}')
    return g.graph

def read_graph_pickle(file_path: str) -> nx.Graph:
    state = None
    with open(file_path, "rb") as f:
        state = pickle.load(f)
    return state

def to_pickle(graph : nx.Graph, file_path: str) -> None:
    with open(file_path, "wb") as f:
        pickle.dump(graph, f)

def process_graph():
    for region_id, region_name in REGIONS_DICT.items():
        exists, graph_file = check_graph_exists(region_id)
        
        if exists:
            logger.info(f'Graph for {region_name} already exists.')
        else:
            logger.info(f'Graph for {region_name} not found. Creating...')
            
            polygon_file = os.path.join(DATA_PATH, f'polygons/{region_id}_polygon_for_graph.parquet')
            if os.path.exists(polygon_file):
                polygon = gpd.read_parquet(polygon_file)

                graph = create_graph(region_id, polygon)
                graph_file = os.path.join(DATA_PATH, f'graphs/{region_id}_car_graph.pickle')
                to_pickle(graph, graph_file)
                
                logger.success(f'Graph for {region_name} has been successfully created.')
            else:
                logger.info(f'Polygon file for region {region_name} not found: {polygon_file}')