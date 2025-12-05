import geopandas as gpd
from rasterio.mask import mask
from pysheds.grid import Grid
from pysheds.sview import Raster
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import shape
from scipy.ndimage import gaussian_filter, distance_transform_edt
from rasterio.features import shapes
from tqdm import tqdm

import sys, os
name = os.listdir('watersheds')[int(sys.argv[1])]
print(name)
watersheds = gpd.read_file('GIS/WATERSHEDS.geojson')
watersheds['NAME'] = watersheds['NAME'].str.lower()
watershed = watersheds[watersheds['NAME'].str.contains(name.replace('_', ' ')[:name.find('dem')-1])]
watershed = watershed.to_crs('EPSG:26918')
grid = Grid.from_raster(f"watersheds/{name}")
dem = grid.read_raster(f"watersheds/{name}")

pits = grid.fill_pits(dem)
print("Filled pits")
depressions = grid.fill_depressions(pits)
print("Filled depressions")
del pits
flats = grid.resolve_flats(depressions)
print("Resolved flats")
del depressions
flowdir = grid.flowdir(flats)
print("Flow direction")
del flats

nodes = gpd.read_file('nodes.geojson')
drainage = nodes[nodes.node_type == 'infall'].clip(watershed.geometry)
del nodes

Ainv = grid.affine.__invert__()
sink_patch = np.array([[2,4,8],
                       [1,-2,16],
                       [128,64,32]], dtype=flowdir.dtype)

subcatchments = np.zeros_like(flowdir, dtype=np.uint8)
mask = (dem == -9999)

area = np.sum(~mask)
subcatchment_area = 0

geometries = tqdm(drainage.geometry)

for k, source in enumerate(geometries):
    j, i = Ainv * (source.x, source.y)
    i = int(round(i))
    j = int(round(j))
    # modification without replacement was tested to reveal neglible difference in delineation
    try:
        flowdir[i-1:i+2, j-1:j+2] = sink_patch
    except ValueError:
        continue

    sub = grid.catchment(x=j, y=i, fdir=flowdir, xytype='index')

    sub &= ~mask
    mask[i, j] = True 

    count = sub.sum()
    if count == 0:
        continue

    subcatchment_area += count

    subcatchments[sub] = 1
    mask |= sub


    geometries.set_description(
        f"Area covered - {subcatchment_area / area * 100:.2f}%"
    )


polygons = []
arr = (subcatchments != 0).astype(np.uint8)
print("Rasterizing")
for geom, val in tqdm(shapes(arr, mask=arr==1, transform=grid.affine)):
    polygons.append(shape(geom))

polygon_gdf = gpd.GeoDataFrame(
    {"geometry": polygons},
    crs=grid.crs
)

polygon_gdf.to_file(f"subs/{name[:name.find('dem')-1]}.geojson", driver="GeoJSON")
