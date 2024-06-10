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

router = APIRouter()

spb_center_osmid = 27490597
lo_center_osmid = 27025179

points = load_gdf('points')
polys18 = load_gdf('polygons18')
polys188 = load_gdf('polygons188')
centers18 = load_gdf('17(18)_centers')
admin_centers_LO_188_nodes = load_gdf('admin_centers_LO_188_nodes')
svetlogorskoe = load_gdf('project Светогорского поселения')
shlisserburg = load_gdf('project Шлиссельбург')
pulkovo = load_gdf('pulkovo')
aero_lodeynoe = load_gdf('Аэродром лодейнопольское поселение')
aero_siversk = load_gdf('Аэродром Сиверск ')
vodomy = load_gdf('Водомы итог (конец)')
zhd_stops = load_gdf('ЖД остановки')
oopt_lo = load_gdf('ООПТ ЛО')

fuel = load_gdf('fuel')
aero_local = load_gdf('airports_local_LO')
water_transport = load_gdf('water_transport_LO')
international_aero = load_gdf('pulkovo').iloc[[0]]
international_aero['geometry'] = shapely.centroid(international_aero.geometry).iloc[[0]]

city_center = load_main_city_center_node(spb_center_osmid)
lo_center = load_main_city_center_node(lo_center_osmid)

region_poly = load_region()
country_poly = load_country()

regions_of_russia = load_gdf('regions_of_russia')
regions_of_russia = regions_of_russia[regions_of_russia['ISO3166-2']!='RU-CHU']
regions_of_russia = regions_of_russia.to_crs(general_crs)

inter_g = load_graphml('inter')
inter_g = indicators.prepare_graph(inter_g)
region_roads_g = get_region_roads_g(region_poly, country_poly)

    
@router.post("/get_isochrone/")
def get_d1():   

    d1 = calculate_tf_d1(region_roads_g, region_poly, polys18, points, polys188, inter_g, city_center, lo_center,fuel, zhd_stops, aero_local, aero_local, water_transport)

    return d1