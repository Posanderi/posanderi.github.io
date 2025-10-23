from fig_scripts import plot_plotly_timeseries
import folium
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import io
import base64
import os
import json
import shapely
from shapely import Polygon
from shapely.geometry import mapping
import plotly.express as px
import plotly.graph_objects as go

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

CAM_POINT_PATH = os.path.join(ROOT_DIR, "data", "camera_locations.gpkg")
CAM_POLY_PATH = os.path.join(ROOT_DIR, "data", "camera_polygons.gpkg")
HELSINKI_POLY_PATH = os.path.join(ROOT_DIR, "data", "helsinki_poly", "helsinki_poly.shp")
NDVI_TIMESERIES_DIR = os.path.join(ROOT_DIR, "data", "s2_timeseries")
GCC_TIMESERIES_DIR = os.path.join(ROOT_DIR, "data","gcc_timeseries")
IMAGES_DIR = os.path.join(ROOT_DIR, "data", "camera_pictures")
OUTPUT_HTML = os.path.join(ROOT_DIR, "docs", "index.html")


def run():
    
    camera_polys = gpd.read_file(CAM_POLY_PATH).to_crs("EPSG:4326")
    m = folium.Map(tiles="Cartodb Positron", location=[camera_polys.geometry.centroid.y.mean(), camera_polys.geometry.centroid.x.mean()], zoom_start=11)

    #Add a mask for areas outside of Helsinki
    world = Polygon([
    [-90, -180],
    [90, -180],
    [90, 180],
    [-90, 180],
    ])
    helsinki_poly=gpd.read_file(HELSINKI_POLY_PATH).to_crs("EPSG:4326").geometry
    mask = world.difference(helsinki_poly)
    folium.GeoJson(
        data=mask.__geo_interface__,
        style_function=lambda x: {
        'fillColor': 'gray',
        'color': 'gray',
        'weight': 1,
        'fillOpacity': 0.7,
        }
    ).add_to(m)

    #Add popup content for each of the cameras
    for i, row in camera_polys.iterrows():
        
        #Popup title
        html=f"<h1>{row['Kamera']}</h1><br>"

        #Example camera image
        camera_img_path = os.path.join(IMAGES_DIR, row["Kamera"], os.listdir(os.path.join(IMAGES_DIR, row["Kamera"]))[0])
        with open(camera_img_path, "rb") as f:
            camera_img_b64 = base64.b64encode(f.read()).decode()
        html += f"<img src='data:image/jpg;base64,{camera_img_b64}' width='{200}'>"

        #NDVI and GCC Timeseries plot
        ndvi_ts_path = os.path.join(NDVI_TIMESERIES_DIR, f"{row['Kamera']}_ndvi.csv")
        if not os.path.exists(ndvi_ts_path):
            continue
        ndvi_ts_df = pd.read_csv(ndvi_ts_path)

        gcc_ts_path = os.path.join(GCC_TIMESERIES_DIR, f"{row["Kamera"]}.csv")
        if not os.path.exists(gcc_ts_path):
            continue
        gcc_ts_df = pd.read_csv(gcc_ts_path)
        
        ply_fig_html = plot_plotly_timeseries(ndvi_ts_df, gcc_ts_df)
        if ply_fig_html:
            html += ply_fig_html

        #Generate the popup window
        iframe = folium.IFrame(html, width=500, height=600)
        popup = folium.Popup(iframe, max_width="100%", max_height="100%")

        #Generate the popup icon
        folium.Circle(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            popup=popup,
            radius=500,
            fill=True
        ).add_to(m)

    m.save(OUTPUT_HTML)
    print(f"🌍 Map generated at {OUTPUT_HTML}")

def main():
    run()

if __name__ == "__main__":
    main()

