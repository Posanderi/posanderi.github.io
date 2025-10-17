
import folium
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import io
import base64
import os

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

CAM_POLY_PATH = os.path.join(ROOT_DIR, "data", "camera_polygons.gpkg")
TIMESERIES_DIR = os.path.join(ROOT_DIR, "data", "timeseries")
IMAGES_DIR = os.path.join(ROOT_DIR, "data", "camera_pictures")
OUTPUT_HTML = os.path.join(ROOT_DIR, "docs", "index.html")


def plot_timeseries(df):
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
    ax.set_title("NDVI over time", fontsize=10)
    ax.set_xlabel("Date")
    ax.set_ylabel("NDVI")
    plt.xticks(rotation=90)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def run():
    cameras = gpd.read_file(CAM_POLY_PATH)
    m = folium.Map(location=[cameras.geometry.centroid.y.mean(), cameras.geometry.centroid.x.mean()], zoom_start=7)

    for i, row in cameras.iterrows():
        ts_path = os.path.join(TIMESERIES_DIR, f"{row['Kamera']}_ndvi.csv")
        if not os.path.exists(ts_path):
            continue

        df = pd.read_csv(ts_path)

        html=f"<b>{row['Kamera']}</b><br>"

        plot_b64 = plot_timeseries(df)

        if plot_b64:
            html += f"<img src='data:image/png;base64,{plot_b64}' width='300'><br>"

        local_img = os.path.join(IMAGES_DIR, row["Kamera"], os.listdir(os.path.join(IMAGES_DIR, row["Kamera"]))[0])
        html += f"<img src='{local_img}' width='300'><br>"

        iframe = folium.IFrame(html, width=440, height=330)
        popup = folium.Popup(iframe, max_width=520)

        folium.CircleMarker(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            popup=popup,
            fill=True
        ).add_to(m)

    m.save(OUTPUT_HTML)
    print(f"🌍 Map generated at {OUTPUT_HTML}")

def main():
    run()


if __name__ == "__main__":
    main()

