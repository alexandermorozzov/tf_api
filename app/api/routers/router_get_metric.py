from functools import cache
import asyncio
import shapely

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse



from contextlib import suppress

from app.scripts.calculate_metric import calculate_tf_d1

from app.exceptions.exceptions import OutOfBoundaryError
from .router_utils import load_gdf, load_graphml, load_main_city_center_node, load_region, load_country, get_region_roads_g, general_crs
from transport_frames.src.metrics import indicators



import geopandas as gpd
from fastapi import Depends
from app.api.schemes.schemes import Region
import json
import pathlib
import os

router = APIRouter()


def read_json_file(filename):
    with open(filename, 'r') as f:
        json_object = json.load(f)

    result_dict = {}

    for key in json_object.keys():
        if isinstance(json_object[key], str):  # check if the value is a string
            try:
                gdf = gpd.read_file(json_object[key])
                result_dict[key] = gdf
            except:
                try:
                    result_dict[key] = json.loads(json_object[key])
                except json.JSONDecodeError:
                    result_dict[key] = json_object[key]
        else:
            result_dict[key] = json_object[key]

    return result_dict

# /Users/test/Documents/code/tf_api/app/db/indicators/Ленинградская_область/Ленинградская область_indicators_gpsp.json

async def read_region_file(region_name, indicator_name:str):
    cwd = os.getcwd()
    parents = pathlib.Path(cwd)
    path = str(parents) + f'/app/db/indicators/{region_name}/{region_name}_indicators_{indicator_name}.json'
    file = read_json_file(path)
    return json.loads(file[list(file)[0]].to_json())


@router.get("/get_region/")
async def get_d0(query_params: Region=Depends()):   
    return await read_region_file(query_params.region.value, "gpsp")
    
@router.get("/get_mr/")
async def get_d1(query_params: Region=Depends()):   
    return await read_region_file(query_params.region.value, "mr")

@router.get("/get_gpsp/")
async def get_d2(query_params: Region=Depends()):   
    return await read_region_file(query_params.region.value, "region")
    