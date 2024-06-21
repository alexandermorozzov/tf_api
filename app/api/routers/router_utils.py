import geopandas as gpd
import networkx as nx
import osmnx as ox
from transport_frames.src.graph_builder import graphbuilder

data_path = 'app/api/routers/indicators/'
general_crs=4326

def load_parquet(name:str):
    print('loading:  ', name)
    return gpd.read_parquet(name+'.parquet')

def load_graphml(name:str):
    print('loading:  ', name)
    return nx.read_graphml(data_path+name+'.graphml')


def load_country():
    print('loading: country')
    res = ox.geocode_to_gdf("Russia")
    print(type(res))
    return  res#  get border of the country

def load_region(osmid=176095, crs=32636, inner_city_osmid: int | None=337422, buffer_roads=3000):
    lo_polygon = ox.geocode_to_gdf('R'+str(osmid), by_osmid=True).to_crs(epsg=crs)
    spb_polygon = ox.geocode_to_gdf('R'+str(inner_city_osmid), by_osmid=True).to_crs(epsg=crs).buffer(buffer_roads)
    city = lo_polygon.union(spb_polygon).to_crs(epsg=general_crs) #  get lo polygon
    return city
    
def load_main_city_center_node(node_osmid=27490597):
    print('loading ', node_osmid)
    return ox.geocode_to_gdf('N'+str(node_osmid), by_osmid=True)  # СПб


def get_region_roads_g(region_poly, country_poly, crs=32636):
    print('loading roads for region')
    citygraph = graphbuilder.get_graph_from_polygon(region_poly, crs=crs,country_polygon=country_poly)
    return citygraph
