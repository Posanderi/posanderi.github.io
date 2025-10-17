import ee
import geopandas as gpd
import pandas as pd
import os
from datetime import datetime
import shapely
import json

ee.Initialize(project="urban-phenology")

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

ROOT_DIR = SCRIPT_DIR.parent

CAM_POLY_PATH = os.path.join(ROOT_DIR, "data", "camera_polygons.gpkg")
OUTPUT_DIR = os.path.join(ROOT_DIR, "data", "timeseries")

START_DATE = "2024-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_ndvi_timeseries(camera_poly):

    collection = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(camera_poly)
    .filterDate(START_DATE, END_DATE)
    ).map(lambda img: img.addBands(img.normalizedDifference(['B8', 'B4']).rename('NDVI')))

    def mask_clouds(img):
        qa=img.select("QA60")
        cloudBitMask = 1<<10
        cirrusBitMask= 1<<11
        mask=qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
        return img.updateMask(mask)

    def mean_ndvi_per_polygon(img):
        ndvi = img.select('NDVI')
        mean = ndvi.reduceRegion(
            geometry=camera_poly,
            reducer=ee.Reducer.mean().setOutputs(["NDVI"]),
            scale=10,
            bestEffort=True
        )
        return ee.Feature(None, mean).set("date", img.date().format("YYYY-MM-dd"))

    masked_collection=collection.map(mask_clouds)
    features = masked_collection.map(mean_ndvi_per_polygon).getInfo()["features"]
    if not features:
        return pd.DataFrame(columns=["date", "NDVI"])

    data = [{"date": f["properties"]["date"], "NDVI": f["properties"].get("NDVI")} for f in features]
    return pd.DataFrame(data)

def run():
    cameras = gpd.read_file(CAM_POLY_PATH)
    cameras.explore()
    for i, row in cameras.iterrows():
        cam_json=json.loads(shapely.to_geojson(row.geometry))
        geom = ee.Geometry.Polygon(cam_json["coordinates"])
        df = get_ndvi_timeseries(geom)
        out_path = os.path.join(OUTPUT_DIR, f"{row['Kamera']}_ndvi.csv")
        df.to_csv(out_path, index=False)
        print(f"✅ Updated NDVI for point {row['Kamera']} -> {out_path}")


def main():
    run()


if __name__ == "__main__":
	main()




