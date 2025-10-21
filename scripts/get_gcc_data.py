import os
import json
import re
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import zipfile
from pathlib import Path
import time

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
ROI_DIR= os.path.join(ROOT_DIR, "data", "camera_rois")

#Adjust this later
PICTURE_DIRS="Z:/Documents/Amanda-hommat/Kamerat"

CAM_POINT_PATH = os.path.join(ROOT_DIR, "data", "camera_locations.gpkg")

OUTPUT_DIR = os.path.join(ROOT_DIR, "data", "gcc_timeseries")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_date(filename):
    match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d_%H-%M-%S')
    return None

def run():
    camera_points=gpd.read_file(CAM_POINT_PATH)

    for i, row in camera_points.iterrows():

        zip_list=os.listdir(os.path.join(PICTURE_DIRS, row["Kamera"]))
        gcc_data = []

        with open(os.path.join(ROI_DIR, str(row["Kamera"])+ "_rois.json"), 'r') as f:
            rois = json.load(f)

        for zip_name in zip_list:
            if zip_name.endswith(".zip"):
                fp=os.path.join(PICTURE_DIRS, row["Kamera"], zip_name)
                with zipfile.ZipFile(fp, "r") as zip_file:
                    for pic_name in zip_file.namelist():
                        dt=extract_date(pic_name)
                        if not dt:
                            continue

                        with zip_file.open(pic_name) as pic_file:
                            img_data = pic_file.read()
                            img=Image.open(BytesIO(img_data)).convert("RGB")
                            img_np = np.array(img, dtype=np.float32)


                            for i, roi in enumerate(rois):
                                x, y, w, h = map(int, roi)
                                crop = img_np[y:y + h, x:x + w]
                                R, G, B = crop[:, :, 0], crop[:, :, 1], crop[:, :, 2]
                                GCC = G / (R + G + B + 1e-8)  # Avoid division by zero
                                GCC_mean = np.nanmean(GCC)
                                gcc_data.append({"Kamera": row["Kamera"], 'datetime': dt, 'ROI': f'ROI_{i+1}', 'GCC': GCC_mean})
        df = pd.DataFrame(gcc_data)
        df['date'] = df['datetime'].dt.date # extracts date for grouping

        # === Group into non-overlapping 3-day windows & calculate 90th percentile ===
        df.sort_values(by='datetime', inplace=True)
        start_date = df['date'].min()
        end_date = df['date'].max()

        window_results = []

        current = start_date
        while current <= end_date - timedelta(days=2):
            window_end = current + timedelta(days=3)
            window_center = current + timedelta(days=1)  # middle day

            window_df = df[(df['date'] >= current) & (df['date'] < window_end)]

            if not window_df.empty:
                for roi in df['ROI'].unique():
                    roi_values = window_df[window_df['ROI'] == roi]['GCC'].dropna()
                    if not roi_values.empty:
                        p90 = np.percentile(roi_values, 90)
                        mean_val = roi_values.mean()
                        window_results.append({
                            'Date': window_center,
                            'ROI': roi,
                            'GCC_90p': p90,
                            'GCC_mean': mean_val
                        })
            current += timedelta(days=3)

        per90_mean_df = pd.DataFrame(window_results)
        per90_mean_df['Date'] = pd.to_datetime(per90_mean_df['Date'])
        per90_mean_df.to_csv(os.path.join(OUTPUT_DIR, f"{row['Kamera']}.csv"))
        print(f"Saved 3-day window GCC-timeseries of {row["Kamera"]}!")

def main():
    run()
    
if __name__ == "__main__":
    main()
