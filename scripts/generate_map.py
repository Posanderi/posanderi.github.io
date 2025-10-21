
import folium
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import io
import base64
import os
import json
import shapely
from shapely.geometry import mapping

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

CAM_POINT_PATH = os.path.join(ROOT_DIR, "data", "camera_locations.gpkg")
CAM_POLY_PATH = os.path.join(ROOT_DIR, "data", "camera_polygons.gpkg")
NDVI_TIMESERIES_DIR = os.path.join(ROOT_DIR, "data", "s2_timeseries")
GCC_TIMESERIES_DIR = os.path.join(ROOT_DIR, "data","gcc_timeseries")
IMAGES_DIR = os.path.join(ROOT_DIR, "data", "camera_pictures")
OUTPUT_HTML = os.path.join(ROOT_DIR, "docs", "index.html")

def plot_ndvi_timeseries(df):
    """Return a base64-encoded PNG of NDVI time series."""
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(4, 3))
    df["date"] = pd.to_datetime(df["date"])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    monthly_median_df=(
        df.groupby(['year', 'month'])['NDVI']
            .median()
            .reset_index()
    )
    monthly_median_df["year_month"]=pd.to_datetime(monthly_median_df[['year', 'month']].assign(DAY=1))
    
    #rolling_df=df.rolling("14D", on="date").median()
    
    ax.plot(monthly_median_df["year_month"], monthly_median_df["NDVI"], marker="o", linestyle="-", linewidth=1.5)
    ax.set_title("Monthly Median NDVI", fontsize=10)
    ax.set_xlabel("Month")
    ax.set_ylabel("NDVI")
    plt.xticks(rotation=90)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()
    
def plot_gcc_timeseries(gcc_ts):
    gcc_ts['Date'] = pd.to_datetime(gcc_ts['Date'])    
    #Pivot tables for plotting
    pivot_p90 = gcc_ts.pivot(index='Date', columns='ROI', values='GCC_90p')
    pivot_mean = gcc_ts.pivot(index='Date', columns='ROI', values='GCC_mean')
    
    # === Plot gcc90 for each roi ===
    fig=plt.figure(figsize=(12, 6))
    doy = pivot_p90.index.to_series().dt.dayofyear
    
    for roi in pivot_p90.columns:
        plt.plot(doy, pivot_p90[roi], marker='o', markersize=4, linestyle='-', label=roi, linewidth=0.5)
    plt.xlabel("DOY")
    plt.ylabel("GCC (90th)")
    plt.title(f"GCC 3-day non-overlapping 90th percentile")
    plt.ylim(0.3, 0.7)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()
    

def run():
    
    camera_points = gpd.read_file(CAM_POINT_PATH).to_crs("EPSG:4326")
    camera_polys = gpd.read_file(CAM_POLY_PATH).to_crs("EPSG:4326")
    m = folium.Map(location=[camera_points.geometry.y.mean(), camera_points.geometry.x.mean()], zoom_start=10)

    for i, row in camera_points.iterrows():
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
        html += f'<img src="data:image/jpg;base64,{camera_img_b64}" width="{300}">'


        ndvi_ts_b64 = plot_ndvi_timeseries(ndvi_ts_df)
        if ndvi_ts_b64:
            html += f"<img src='data:image/png;base64,{ndvi_ts_b64}' width='300'><br>"

        gcc_ts_b64 = plot_gcc_timeseries(gcc_ts_df)
        if gcc_ts_b64:
            html += f"<img src='data:image/png;base64,{gcc_ts_b64}' width='300'><br>"


        iframe = folium.IFrame(html, width=440, height=330)
        popup = folium.Popup(iframe, max_width=520)

        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            popup=popup,
            radius=5,
            fill=True
        ).add_to(m)
        

        camera_poly=camera_polys.loc[camera_polys["Kamera"]==row["Kamera"]]
        folium.GeoJson(mapping(camera_poly)).add_to(m)

    m.save(OUTPUT_HTML)
    print(f"🌍 Map generated at {OUTPUT_HTML}")

def main():
    run()


if __name__ == "__main__":
    main()

