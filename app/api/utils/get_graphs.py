import os
import pandas as pd
import geopandas as gpd
import osmnx as ox 
import networkx as nx
import pickle
import json
from loguru import logger 
from iduedu import get_drive_graph
from app.api.utils.constants import REGIONS_DICT, REGIONS_CRS, DATA_PATH
from app.api.utils.urban_api import get_regions
from transport_frames.graphbuilder.graph import Graph
from transport_frames.framebuilder.frame import Frame


MAX_TRIES = 3

def check_graph_exists(region_id : int):
    graph_file = os.path.join(DATA_PATH, f'graphs/{region_id}_car_graph.pickle')
    return os.path.exists(graph_file), graph_file

def create_graph(region_id : int, polygon : gpd.GeoDataFrame):
    crs = REGIONS_CRS[region_id]
    # for _ in range(0, MAX_TRIES):
    while True:
        try:
            g = Graph.from_polygon(polygon, crs=f'{crs}')
            return g.graph
        except json.decoder.JSONDecodeError as e:
            logger.error(f"Error decoding JSON response for region {region_id}: {e}. Retrying...")

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
            logger.info(f'Car graph for {region_name} already exists.')
        else:
            logger.info(f'Car graph for {region_name} not found. Creating...')
            
            polygon_file = os.path.join(DATA_PATH, f'polygons/{region_id}_polygon_for_graph.parquet')
            if os.path.exists(polygon_file):
                polygon = gpd.read_parquet(polygon_file)

                graph = create_graph(region_id, polygon)
                graph_file = os.path.join(DATA_PATH, f'graphs/{region_id}_car_graph.pickle')
                to_pickle(graph, graph_file)
                
                logger.success(f'Car graph for {region_name} has been successfully created.')
            else:
                logger.info(f'Polygon file for region {region_name} not found: {polygon_file}')

def check_frame_exists(region_id : int):
    frame_file = os.path.join(DATA_PATH, f'frames/{region_id}_frame.pickle')
    return os.path.exists(frame_file), frame_file

def load_graph(region_id: int) -> nx.Graph:
    graph_file = os.path.join(DATA_PATH, f'graphs/{region_id}_car_graph.pickle')
    if not os.path.exists(graph_file):
        region_name = REGIONS_DICT.get(region_id, f"Region ID {region_id}")
        raise FileNotFoundError(f"Car graph for {region_name} not found.")
    
    with open(graph_file, "rb") as f:
        graph = pickle.load(f)

    return graph

def create_frame(region_id: int, regions: gpd.GeoDataFrame, polygon: gpd.GeoDataFrame) -> Frame:
    graph = load_graph(region_id)
    local_crs = REGIONS_CRS[region_id]
    regions = regions.to_crs(local_crs)
    polygon = polygon.to_crs(local_crs)
    f = Frame(graph, regions, polygon)
    return f.frame

def save_frame(frame: nx.Graph, file_path: str) -> None:
    with open(file_path, "wb") as f:
        pickle.dump(frame, f)

def process_frames():
    for region_id, region_name in REGIONS_DICT.items():
        exists, frame_file = check_frame_exists(region_id)
        
        if exists:
            logger.info(f'Frame for {region_name} already exists.')
        else:
            logger.info("Downloading regions from the database...")
            regions = get_regions()
            logger.info("Regions successfully downloaded.")

            polygon_file = os.path.join(DATA_PATH, f'polygons/{region_id}_polygon_for_graph.parquet')
            if os.path.exists(polygon_file):
                polygon = gpd.read_parquet(polygon_file)
                logger.info(f"Creating frame for {region_name}...")
                frame = create_frame(region_id, regions, polygon)
                frame_file = os.path.join(DATA_PATH, f'frames/{region_id}_frame.pickle')
                save_frame(frame, frame_file)
                logger.success(f"Frame for {region_name} has been successfully created.")
            else:
                logger.error(f"Frame for {region_name} has not been created.")