from fastapi import APIRouter, HTTPException, Depends
import os
import geopandas as gpd
import networkx as nx
import pickle
from transport_frames.framebuilder.frame import Frame
from transport_frames.frame_grader.advanced_grade import AdvancedGrader
from app.api.utils.constants import REGIONS_DICT, REGIONS_CRS, DATA_PATH
from app.api.utils.urban_api import get_bus_stops, get_train_stations, get_airports, get_ports, get_region_territories
from app.api.utils.get_matrix import load_settlement_points

ADM_UNIT_TERRITORY_TYPE_ID = 4

router = APIRouter()

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

def get_adm_units(gdfs: dict[int, gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
    for gdf in gdfs.values():
        levels = gdf.level.unique()
        if ADM_UNIT_TERRITORY_TYPE_ID in levels:
            return gdf
    return None

def get_polygons(region_id: int) -> dict[int, gpd.GeoDataFrame]:
    gdfs_dict = get_region_territories(region_id)
    
    if not gdfs_dict:
        region_name = REGIONS_DICT.get(region_id, f"Region ID {region_id}")
        raise FileNotFoundError(f"Territories for {region_name} not found.")
    
    return gdfs_dict


@router.post('/transport_indicator')
def assess_territory(region_id : int, geojson : dict, regional_scenario_id : int | None = None) -> list[float]:
    
    gdf = gpd.GeoDataFrame.from_features(geojson['features'], crs=4326)
    gdf['name'] = ''
    frame = load_frame(region_id)
    graded_territory = Frame.grade_territory(frame, gdf)

    bus_stops = get_bus_stops(region_id)
    train_stations = get_train_stations(region_id)
    airports = get_airports(region_id)
    ports = get_ports(region_id)

    settlement_points = load_settlement_points(region_id)

    gdfs_dict = get_polygons(region_id)
    polygons = get_adm_units(gdfs_dict)
    # polygons['index'] = polygons.index

    if polygons is None:
        raise HTTPException(status_code=404, detail="Administrative units not found")

    matrix_car, matrix_inter = load_matrices(region_id)

    local_crs = REGIONS_CRS[region_id]
    grader = AdvancedGrader(local_crs)

    # criteria_args = {
    #     "graded_terr": graded_territory,
    #     "points": settlement_points,
    #     "polygons": polygons,
    #     "adj_mx_drive": matrix_car,
    #     "adj_mx_inter": matrix_inter
    # }

    # if not bus_stops.empty:
    #     criteria_args["b_stops"] = bus_stops
    # if not train_stations.empty:
    #     criteria_args["r_stops"] = train_stations
    # if not airports.empty:
    #     criteria_args["aero"] = airports
    # if not ports.empty:
    #     criteria_args["ferry"] = ports

    # cri = grader.get_criteria(**criteria_args)

    cri = grader.get_criteria(
    graded_terr=graded_territory.reset_index(),
    points=settlement_points.reset_index(),
    polygons=polygons.reset_index(),
    adj_mx_drive=matrix_car,
    adj_mx_inter=matrix_inter,
    
    **({"b_stops": bus_stops.reset_index()} if not bus_stops.empty else {}),
    **({"r_stops": train_stations}.reset_index() if not train_stations.empty else {}),
    **({"aero": airports.reset_index()} if not airports.empty else {}),
    **({"ferry": ports.reset_index()} if not ports.empty else {})
)

    return cri['overall_assessment'].tolist()