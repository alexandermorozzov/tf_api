from functools import cache
import asyncio
import shapely

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse



from contextlib import suppress

from app.exceptions.exceptions import OutOfBoundaryError
from .router_utils import load_parquet
#  load_gdf, load_graphml, load_main_city_center_node, load_region, load_country, get_region_roads_g, general_crs



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

async def read_region_file(region_name, level:str):
    cwd = os.getcwd()
    parents = pathlib.Path(cwd)
    path = str(parents) + f'/app/db/indicators/{region_name}_{level}'
    file = load_parquet(path)
    return json.loads(file.to_json())


@router.get("/get_region/")
async def get_d0(query_params: Region=Depends()):   
    return await read_region_file(query_params.region.value, query_params.Level.value)
    