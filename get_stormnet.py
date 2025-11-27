import requests
import geopandas as gpd
from shapely.geometry import shape
import json

BASE_URL = "https://www.fairfaxcounty.gov/mercator/rest/services/DPWES/StormNetServReq/MapServer"

LAYERS = {
    13: "Stormwater Structures",
    14: "Stormwater Pipes",
    15: "Stormwater Structures Maintenance",
    16: "Stormwater Pipes Maintenance",
    17: "Open Channels",
    18: "Sanitary Structures",
    19: "Sanitary Pipes",
    20: "Stormwater Facilities",
    21: "Tax Map Grid"
}

OUTPUT_GEOJSON = "stormnet_all_layers.geojson"

CHUNK_SIZE = 1000

def download_layer(layer_num):
    print(f"\n=== Downloading Layer {layer_num}: {LAYERS[layer_num]} ===")

    features = []
    offset = 0
    while True:
        query_url = (
            f"{BASE_URL}/{layer_num}/query"
            f"?where=1=1"
            f"&outFields=*"
            f"&f=geojson"
            f"&resultOffset={offset}"
            f"&resultRecordCount={CHUNK_SIZE}"
        )

        response = requests.get(query_url)
        if response.status_code != 200:
            raise Exception(f"Failed to download layer {layer_num}: HTTP {response.status_code}")

        data = response.json()

        # No more data
        if "features" not in data or len(data["features"]) == 0:
            break

        features.extend(data["features"])
        offset += CHUNK_SIZE

        print(f"  Retrieved {len(data['features'])} features (offset {offset})")

    print(f"  → Total features downloaded: {len(features)}")
    return features


for layer in LAYERS:
    layer_features = download_layer(layer)

    for f in layer_features:
        f["properties"]["_layer"] = LAYERS[layer]

    geojson = {
    "type": "FeatureCollection",
    "features": layer_features
    }

    with open(f"stormnet/{layer}.geojson", "w") as f:
        json.dump(geojson, f)
