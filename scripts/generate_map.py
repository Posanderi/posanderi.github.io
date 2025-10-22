
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

def plot_timeseries(ndvi_ts, gcc_ts):
    """Return a base64-encoded PNG of NDVI time series."""
    if ndvi_ts.empty or gcc_ts.empty:
        return None
    fig, ax = plt.subplots(figsize=(4, 3))
    
    ndvi_ts["date"] = pd.to_datetime(ndvi_ts["date"])
    
    """
    ndvi_ts['year'] = ndvi_ts['date'].dt.year
    ndvi_ts['month'] = ndvi_ts['date'].dt.month
    monthly_median_ndvi_ts=(
        ndvi_ts.groupby(['year', 'month'])['NDVI']
            .median()
            .reset_index()
    )
    monthly_median_ndvi_ts["year_month"]=pd.to_datetime(monthly_median_ndvi_ts[['year', 'month']].assign(DAY=1))
    """
    
    rolling_ndvi_ts=ndvi_ts.rolling("14D", on="date").median()
    
    gcc_ts['Date'] = pd.to_datetime(gcc_ts['Date'])    
    gcc_ts_roi=gcc_ts.groupby("Date").first().reset_index()

    #Pivot tables for plotting
    pivot_p90 = gcc_ts_roi.pivot(index='Date', columns='ROI', values='GCC_90p')
    pivot_mean = gcc_ts_roi.pivot(index='Date', columns='ROI', values='GCC_mean')    
    
    for roi in pivot_p90.columns:
        ax.plot(pivot_p90.index, pivot_p90[roi], linestyle='-', linewidth=1.5, label="GCC")

    
    
    ax.plot(rolling_ndvi_ts["date"], rolling_ndvi_ts["NDVI"], linestyle="-", linewidth=1.5, label="NDVI")
    ax.set_title("GCC and NDVI Timeseries", fontsize=10)
    ax.set_xlabel("Date")
    ax.set_ylabel("NDVI/GCC")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()    

def run():
    
    camera_polys = gpd.read_file(CAM_POLY_PATH).to_crs("EPSG:4326")
    
    
    world = Polygon([
    [-90, -180],
    [90, -180],
    [90, 180],
    [-90, 180],
    ])

    helsinki_poly=gpd.read_file(HELSINKI_POLY_PATH).to_crs("EPSG:4326").geometry
    mask = world.difference(helsinki_poly)

    m = folium.Map(tiles="Cartodb Positron", location=[camera_polys.geometry.centroid.y.mean(), camera_polys.geometry.centroid.x.mean()], zoom_start=11)
    
    folium.GeoJson(
        data=mask.__geo_interface__,
        style_function=lambda x: {
        'fillColor': 'gray',
        'color': 'gray',
        'weight': 1,
        'fillOpacity': 0.7,
        }
    ).add_to(m)


    for i, row in camera_polys.iterrows():
        ndvi_ts_path = os.path.join(NDVI_TIMESERIES_DIR, f"{row['Kamera']}_ndvi.csv")
        #if not os.path.exists(ndvi_ts_path):
        #    continue
        ndvi_ts_df = pd.read_csv(ndvi_ts_path)

        gcc_ts_path = os.path.join(GCC_TIMESERIES_DIR, f"{row["Kamera"]}.csv")
        #if not os.path.exists(gcc_ts_path):
        #    continue
        gcc_ts_df = pd.read_csv(gcc_ts_path)

        html=f"<b>{row['Kamera']}</b><br>"
        
        camera_img_path = os.path.join(IMAGES_DIR, row["Kamera"], os.listdir(os.path.join(IMAGES_DIR, row["Kamera"]))[0])
        with open(camera_img_path, "rb") as f:
            camera_img_b64 = base64.b64encode(f.read()).decode()
        html += f"<img src='data:image/jpg;base64,{camera_img_b64}' width='{300}'>"


        ts_b64 = plot_timeseries(ndvi_ts_df, gcc_ts_df)
        if ts_b64:
            html += f"<img src='data:image/png;base64,{ts_b64}' width='300'><br>"

        iframe = folium.IFrame(html, width=350, height=500)
        popup = folium.Popup(iframe, max_width="100%", max_height="100%")

        folium.CircleMarker(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            popup=popup,
            radius=5,
            fill=True
        ).add_to(m)

    m.save(OUTPUT_HTML)
    print(f"🌍 Map generated at {OUTPUT_HTML}")

def main():
    run()


if __name__ == "__main__":
    main()

