import requests
import shapely
import json
import pandas as pd
import geopandas as gpd

URBAN_API = 'http://10.32.1.107:5300'
PAGE_SIZE = 10000
CRS = 4326
POPULATION_COUNT_INDICATOR_ID = 1

# updated territories methods

def get_territories(parent_id : int | None = None, all_levels = False, geometry : bool = False) -> pd.DataFrame | gpd.GeoDataFrame:
  res = requests.get(URBAN_API + f'/api/v1/all_territories{"" if geometry else "_without_geometry"}', {
      'parent_id': parent_id,
      'get_all_levels': all_levels
  })
  res_json = res.json()
  if geometry:
      gdf = gpd.GeoDataFrame.from_features(res_json, crs=CRS)
      return gdf.set_index('territory_id', drop=True)
  df = pd.DataFrame(res_json)
  return df.set_index('territory_id', drop=True)

def get_territories_population(territories_gdf : gpd.GeoDataFrame, regional_scenario_id : int | None = None):
  res = requests.get(f'{URBAN_API}/api/v1/indicator/{POPULATION_COUNT_INDICATOR_ID}/values')
  res_df = pd.DataFrame(res.json())
  res_df = res_df[res_df['territory_id'].isin(territories_gdf.index)]
  res_df = res_df.groupby('territory_id').agg({'value': 'last'}).rename(columns={'value':'population'})
  return territories_gdf[['geometry']].merge(res_df, how='left', left_index=True, right_index=True)

def _fetch_territories(region_id : int) -> tuple[dict[int, gpd.GeoDataFrame], gpd.GeoDataFrame]:
  # fetch towns
  territories_gdf = get_territories(region_id, all_levels = True, geometry=True)
  territories_gdf['was_point'] = territories_gdf['properties'].apply(lambda p : p['was_point'] if 'was_point' in p else False)
  #filter towns gdf
  towns_gdf = territories_gdf[territories_gdf['was_point']]
  # towns_gdf = await get_territories_population(towns_gdf) # раскоментить если нужно население, если индикатора нет, там будет nan
  #filter units gdf
  units_gdf = territories_gdf[~territories_gdf['was_point']]
  levels = units_gdf['level'].unique()
  # fetch population
  return {level:units_gdf[units_gdf.level == level] for level in levels}, towns_gdf

def get_scenario_by_id(scenario_id : int, token : str):
    res = requests.get(URBAN_API + f'/api/v1/scenarios/{scenario_id}', headers={'Authorization': f'Bearer {token}'})
    return res.json()

def get_project_by_id(project_id : int, token : str):
    res = requests.get(URBAN_API + f'/api/v1/projects/{project_id}/territory_info', headers={'Authorization': f'Bearer {token}'})
    return res.json()

# methods relocated from idu_clients:

def get_country_regions(country_id : int) -> pd.DataFrame: # returns region districts
  res = requests.get(f'{URBAN_API}/api/v1/all_territories', {
      'parent_id':country_id
  })
  return gpd.GeoDataFrame.from_features(res.json()['features'], crs=CRS).set_index('territory_id', drop=True)

def get_countries_without_geometry() -> pd.DataFrame:
  res = requests.get(f'{URBAN_API}/api/v1/all_territories_without_geometry')
  return pd.DataFrame(res.json()).set_index('territory_id', drop=True)

def get_regions():
  countries = get_countries_without_geometry()
  countries_ids = countries.index
  countries_regions = [get_country_regions(country_id) for country_id in countries_ids]
  return pd.concat(countries_regions)

def get_territory_types() -> pd.DataFrame:
  res = requests.get(f'{URBAN_API}/api/v1/territory_types')
  return pd.DataFrame(res.json()).set_index('territory_type_id', drop=True)

def get_region_territories(region_id : int) -> dict[int, gpd.GeoDataFrame]:
  res = requests.get(f'{URBAN_API}/api/v1/all_territories', {
      'parent_id': region_id,
      'get_all_levels': True
  })
  gdf = gpd.GeoDataFrame.from_features(res.json()['features'], crs=4326)
  df = pd.json_normalize(gdf['territory_type']).rename(columns={
      'name':'territory_type_name'
  })
  gdf = pd.DataFrame.join(gdf, df).set_index('territory_id', drop=True)
  return {level:gdf[gdf['level'] == level] for level in set(gdf.level)}

# deafult methods:

def _get_physical_objects(region_id : int, pot_id : int, page : int, page_size : int =PAGE_SIZE):
  res = requests.get(f'{URBAN_API}/api/v1/territory/{region_id}/physical_objects_with_geometry', {
    'physical_object_type_id': pot_id,
    'page': page,
    'page_size': page_size,
  })
  return res.json()

def get_physical_objects(region_id : int, pot_id : int):
  page = 1
  results = []
  while True:
    res_json = _get_physical_objects(region_id, pot_id, page, page_size=PAGE_SIZE)
    results.extend(res_json['results'])
    if res_json['next'] is None:
      break
    page += 1
  for result in results:
    g = result['geometry']
    result['geometry'] = shapely.from_geojson(json.dumps(g))
  return gpd.GeoDataFrame(results, crs=4326)

def _get_service_objects(region_id : int, st_id : int, page : int, page_size : int = PAGE_SIZE):
  res = requests.get(f'{URBAN_API}/api/v1/territory/{region_id}/services_with_geometry', {
    'service_type_id': st_id,
    'page': page,
    'page_size': page_size,
  })
  return res.json()

def get_service_objects(region_id : int, st_id : int):
  page = 1
  results = []
  while True:
    res_json = _get_service_objects(region_id, st_id, page, page_size=PAGE_SIZE)
    results.extend(res_json['results'])
    if res_json['next'] is None:
      break
    page += 1
  for result in results:
    g = result['geometry']
    result['geometry'] = shapely.from_geojson(json.dumps(g))
  return gpd.GeoDataFrame(results, crs=4326)

def get_bus_stops(region_id : int):
  try:
    results = get_physical_objects(region_id, 10)
    return gpd.GeoDataFrame(results, crs=4326)
  except:
    return gpd.GeoDataFrame(geometry=[], crs=4326)

def get_train_stations(region_id : int):
  try:
    results = get_physical_objects(region_id, 30)
    return gpd.GeoDataFrame(results, crs=4326)
  except:
    return gpd.GeoDataFrame(geometry=[], crs=4326)

def get_airports(region_id : int):
  try:
    results = get_physical_objects(region_id, 82)
    return gpd.GeoDataFrame(results, crs=4326)
  except:
    return gpd.GeoDataFrame(geometry=[], crs=4326)

def get_ports(region_id : int):
  try:
    results = get_physical_objects(region_id, 28)
    return gpd.GeoDataFrame(results, crs=4326)
  except:
    return gpd.GeoDataFrame(geometry=[], crs=4326)

def get_water_objects(region_id : int):
  try:
    results = get_physical_objects(region_id, 2)
    return gpd.GeoDataFrame(results, crs=4326)
  except:
    return gpd.GeoDataFrame(geometry=[], crs=4326)

#пока вроде их нет
def get_protected_areas(region_id : int):
  return None