from fig_scripts import plot_plotly_timeseries, plot_temp_timeseries
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

CAM_POLY_PATH = os.path.join(ROOT_DIR, "data", "camera_polygons.gpkg")
HELSINKI_POLY_PATH = os.path.join(ROOT_DIR, "data", "helsinki_poly", "helsinki_poly.shp")

NDVI_TIMESERIES_DIR = os.path.join(ROOT_DIR, "data", "s2_timeseries")
GCC_TIMESERIES_DIR = os.path.join(ROOT_DIR, "data","gcc_timeseries")
TEMP_TIMESERIES_DIR = os.path.join(ROOT_DIR, "data","temp_timeseries")
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
    
    helsinki_json=helsinki_poly.to_json()
    
    folium.GeoJson(data=helsinki_json,
    color='gray', weight=3, fill=False
    ).add_to(m)
    
    map_title = "Urban phenology research map"
    title_html = f'<h1 style="font-size: 70px;position:absolute;border: 5px solid #000000;width:600px;z-index:100000;left:2vw;" >{map_title}</h1>'
    m.get_root().html.add_child(folium.Element(title_html))
    
    map_subtitle = "What you are seeing here are the approximate locations of cameras used in my urban phenology-related Phd project! Click on the popup markers to view some cool information on the phenology of the camera location. For more information my work and research conducted at the TREE-D Lab research group at the University of Helsinki, please visit this website: <a href=https://www.helsinki.fi/en/researchgroups/tree-d-lab/people> https://www.helsinki.fi/en/researchgroups/tree-d-lab/people</a>"
    
    subtitle_html = f'<h2 style="font-size: 30px;width: 600px;position:absolute;z-index:100000;left:2vw;top:250px" >{map_subtitle}</h2>'
    m.get_root().html.add_child(folium.Element(subtitle_html))

    #Add popup content for each of the cameras
    for i, row in camera_polys.iterrows():
                
        #Popup title
        
        html=""
        html+=f"<h1>{row['Kamera']}</h1>"

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
            
        #Temperature plot
        temp_ts_path = os.path.join(TEMP_TIMESERIES_DIR, f"{row["Kamera"]}.csv")
        if not os.path.exists(temp_ts_path):
            continue
        temp_ts_df = pd.read_csv(temp_ts_path)
        temp_fig_html=plot_temp_timeseries(temp_ts_df)
        if temp_fig_html:
            html += temp_fig_html
            
        html+="</body> </html>"


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

