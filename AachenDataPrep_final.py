# Data Preparation for Bus Stop Optimization
# Exports: aachen_data.gdx

from gamspy import Container, Set, Alias, Parameter
import pandas as pd
import geopandas as gpd
from shapely import wkt
import numpy as np


# 1. LOAD DATA
base_path = '/Users/clemensulbrich/Documents/Uni/Advanced_Data_Analysis/Bus_stop_locations/Aachen_Data/PM_WS25_26/Aachen Data Clean/'

df = pd.read_csv(base_path + 'merged_bus_stops.csv')
districts = gpd.read_file(base_path + 'aachen_districts.gpkg')
bus_stops = gpd.read_file(base_path + 'bus_stops_aachen.gpkg')

# 2. Latitude and Longitude from 'geometry' string in CSV
df['longitude'] = df['geometry'].apply(lambda x: float(x.replace('POINT (', '').replace(')', '').split()[0]))
df['latitude'] = df['geometry'].apply(lambda x: float(x.replace('POINT (', '').replace(')', '').split()[1]))

print(districts.head(20).iloc[:, :10])
print(bus_stops.head(20).iloc[:, :15])
print(df.head(20))

# 3. CALCULATE DEMAND (Spatial Join)
# Combination of Stops and opposite sides of street
bus_stops['merged_stop_name'] = bus_stops['stop_name'].str.replace(r'\.\w$', '', regex=True)

# Re-create the merged stops gdf for spatial join
from shapely.geometry import Point
def average_geometry(group):
    return Point(group.geometry.x.mean(), group.geometry.y.mean())

merged_bus_stops_geom = bus_stops.groupby('merged_stop_name').agg({
    'geometry': lambda x: average_geometry(x),
    'stop_name': 'first',
    'stop_id': 'first'
}).reset_index()

gdf_merged = gpd.GeoDataFrame(merged_bus_stops_geom, geometry='geometry', crs=bus_stops.crs).to_crs('EPSG:4326')

# Spatial Join to assign districts
stops_with_districts = gpd.sjoin(gdf_merged, districts, how="left", predicate="within")

# Calculate Demand
district_counts = stops_with_districts['st_name'].value_counts()
df_model_data = stops_with_districts.copy()
df_model_data['district_stop_count'] = df_model_data['st_name'].map(district_counts)

# Ensure population is numeric
df_model_data['population'] = pd.to_numeric(df_model_data['population'], errors='coerce')

# Demand = Pop / Count (Fill NaN with 10)
df_model_data['demand'] = (df_model_data['population'] / df_model_data['district_stop_count']).fillna(10)
#df_model_data['stop_id_str'] = df_model_data['stop_id'].astype(str)

df_model_data['stop_id_str'] = (
    df_model_data['merged_stop_name']
    .str.replace(' ', '_', regex=False)
    .str.replace(r'[^a-zA-Z0-9_]', '', regex=True)
)
# 4. DISTANCE MATRIX (haversine)
def haversine_vectorized(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return c * 6371000 # Meters

# USE df_model_data (Merged Stops) instead of df
lats = df_model_data.geometry.y.values
lons = df_model_data.geometry.x.values
stop_ids = df_model_data['stop_id_str'].values 

lat_col = lats[:, np.newaxis]
lon_col = lons[:, np.newaxis]
lat_row = lats[np.newaxis, :]
lon_row = lons[np.newaxis, :]

dist_matrix = haversine_vectorized(lon_col, lat_col, lon_row, lat_row)
dist_df = pd.DataFrame(dist_matrix, index=stop_ids, columns=stop_ids)
dist_long = dist_df.reset_index().melt(id_vars='index', var_name='j', value_name='value')
dist_long.columns = ['i', 'j', 'value']


# 5. GAMSPY CONTAINER & EXPORT
m = Container()

# Sets
i = Set(m, name="i", records=df_model_data['stop_id_str'].tolist(), description="Bus Stops")
j = Alias(m, name="j", alias_with=i)

# Parameters
d = Parameter(m, name="d", domain=[i, j], records=dist_long, description="Distance Matrix")
c = Parameter(m, name="c", domain=i, records=df_model_data[['stop_id_str', 'demand']], description="Demand")

lat_rec = df_model_data[['stop_id_str', 'geometry']].copy()
lat_rec['value'] = lat_rec['geometry'].apply(lambda g: g.y)
lat = Parameter(m, name="lat", domain=i, records=lat_rec[['stop_id_str', 'value']])

lon_rec = df_model_data[['stop_id_str', 'geometry']].copy()
lon_rec['value'] = lon_rec['geometry'].apply(lambda g: g.x)
lon = Parameter(m, name="lon", domain=i, records=lon_rec[['stop_id_str', 'value']])


sol_headers = Set(m, name="sol_headers", records=["lat", "lon", "status"], description="Map Headers")

# 2. Prepare the Data for map_data
df_map = df_model_data[['stop_id_str', 'geometry']].copy()
df_map['lat'] = df_map.geometry.y
df_map['lon'] = df_map.geometry.x

#  GAMS format: (i, header, value)

map_data_df = df_map.melt(
    id_vars=['stop_id_str'], 
    value_vars=['lat', 'lon'], 
    var_name='header', 
    value_name='value'
) 

# 3. Create the Parameter
map_data_input = Parameter(m, name="map_data_init", domain=[i, sol_headers], records=map_data_df, description="Initial Map Data")

# EXPORT
m.write("aachen_data_clean_withNames_testforreport.gdx")
print("\nSuccess! 'aachen_data_clean_withNames.gdx' has been created.")