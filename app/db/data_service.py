# # app/services/data_service.py

# import os
# from contextlib import suppress
# from functools import cache

# import geopandas as gpd
# from shapely.geometry import Polygon, MultiPolygon
# import sqlalchemy
# import pandas as pd
# from networkx.classes.multidigraph import MultiDiGraph
# import networkx as nx
# import requests
# from loguru import logger

# from app.exceptions.exceptions import *


# class DataGetter:

#     GENERAL_REQ_TIMEOUT = 10

#     postgis_engine = sqlalchemy.create_engine(f"postgresql://{os.environ['POSTGRES']}")
#     mongo_address = os.environ['MONGO']

#     @staticmethod
#     @cache
#     def get_nx_graph_mongo(city_name: str, graph_type: str, node_type: type=int) -> MultiDiGraph:

#         logger.info('Loading graph')

#         file_name = city_name.lower() + "_" + graph_type
#         try:
#             response = requests.get(
#                 DataGetter.mongo_address + "/uploads/city_graphs/" + file_name,
#                 timeout=DataGetter.GENERAL_REQ_TIMEOUT,
#             )
#             print(response.ok)
#             print(response.text)
#             if response.ok:
#                 graph = nx.readwrite.graphml.parse_graphml(
#                     response.text, node_type=node_type
#                 )
#                 return graph
#             else:
#                 with suppress(NoDataError):
#                     raise NoDataError(f'{graph_type} graph')
#         except requests.Timeout as exc:
#             with suppress(TimeOutError):
#                 raise TimeOutError(f'{graph_type} graph') from exc

#     @staticmethod
#     @cache
#     def get_city_utm_crs(city_name: str) -> int:
        
#         logger.info('Loading city utm crs')

#         query_crs = (
#             f"SELECT local_crs "
#             f"FROM cities "
#             f"WHERE code = '{city_name}'"
#         )

#         try:
#             with DataGetter.postgis_engine.connect() as conn:
#                 utm_crs = pd.read_sql(query_crs, con=conn).loc[:, 'local_crs']
#             utm_crs = utm_crs.item()
#         except ValueError as exc:
#             with suppress(NoDataError):
#                 raise NoDataError(f'{city_name} utm crs') from exc

#         return utm_crs
    
#     @staticmethod
#     @cache
#     def get_city_geometry(city_name: str) -> int:
        
#         logger.info('Loading city geometry')

#         query_crs = (
#             f"SELECT geometry "
#             f"FROM cities "
#             f"WHERE code = '{city_name}'"
#         )

#         with DataGetter.postgis_engine.connect() as conn:
#             city_geom = gpd.read_postgis(query_crs, con=conn, geom_col='geometry')

#         try:
#             city_geom = city_geom.iloc[0].item()
#             assert isinstance(city_geom, (Polygon, MultiPolygon))
#         except AssertionError as exc:
#             raise NoDataError(f'geometry, {city_name}') from exc
        
#         return city_geom
        