import sys
import transport_frames.src.graph_builder.criteria as criteria
import transport_frames.src.metrics.indicators as indicators
import transport_frames.src.metrics.grade_territory as grade_territory
import transport_frames.src.graph_builder.graphbuilder as graphbuilder
import momepy
import osmnx as ox
import geopandas as gpd
import shapely
import pandas as pd
import networkx as nx
import numpy as np
import json

pd.set_option("future.no_silent_downcasting", True)



def calculate_tf_d1(region_roads_g, region_poly, polys18, points, polys188, inter_g, city_center, lo_center,fuel, stops, international_aero, aero, ferry):
     d1 = indicators.indicator_area(region_roads_g, region_poly, polys18, points, polys188, inter_g, city_center, lo_center,fuel, stops, international_aero, aero, ferry)

     return json.loads(str(d1))