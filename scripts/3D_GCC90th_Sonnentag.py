#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Aug 4th 2025

This script calculates the 3-day moving window gcc90 and mean as Sonnentag et al. 2012: the 3-day windows do not overlap, uses all images
and calculates 90th percentile of all image-level GCCs. The result is assigned to the middle day, e.g. Aug 1-3 -> result in Aug 2nd,
then Aug 4-6 -> result in Aug 5th.

Packages: pillow, numpy, pandas, matplotlib
conda install pillow numpy pandas matplotlib
OR pip install pillow numpy pandas matplotlib

"""
import os
import json
import re
from datetime import datetime, timedelta
from PIL import Image
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# === Select camera ===
#cam = 'Eduardo/all'
#cam = 'Eduardo/cloudy'
#cam = 'Eduardo/sunny'

#cam = 'Haltiala/all'
#cam = 'Haltiala/cloudy'
#cam = 'Haltiala/sunny'

#cam = 'Herttoniemi/all'
#cam = 'Herttoniemi/cloudy'
#cam = 'Herttoniemi/sunny'

#cam = 'Keskuspuisto/all'
#cam = 'Keskuspuisto/cloudy'
#cam = 'Keskuspuisto/sunny'

#cam = 'Keskustakampus/all'
#cam = 'Keskustakampus/cloudy'
#cam = 'Keskustakampus/sunny'

#cam = 'Laakso/all'
#cam = 'Laakso/cloudy'
#cam = 'Laakso/sunny'

#cam = 'Patterinmaki/all'
#cam = 'Patterinmaki/cloudy'
#cam = 'Patterinmaki/sunny'

#cam = 'Roihuvuori/all'
#cam = 'Roihuvuori/cloudy'
#cam = 'Roihuvuori/sunny'

#cam = 'Tahtitorni/all'
#cam = 'Tahtitorni/cloudy'
#cam = 'Tahtitorni/sunny'

#cam = 'Toukola/all'
#cam = 'Toukola/cloudy'
#cam = 'Toukola/sunny'

# === Paths ===
base_folder = 'C:\\Users\\yxkirsi\\Documents\\'
roi_path = 'C:\\Users\\yxkirsi\\Documents\\camera_rois\\Tahtitorni_rois.json' # ROI
folder = os.path.join(base_folder, cam)
output_folder = os.path.join(base_folder, 'outputs_csv')
os.makedirs(output_folder, exist_ok=True)

# === Load & sort jpg files ===
img_files = sorted([f for f in os.listdir(folder) if f.lower().endswith('.jpg')])
if not img_files:
    raise FileNotFoundError("No .jpg files found in folder.")

# === Load ROIs ===
with open(roi_path, 'r') as f:
    rois = json.load(f)

# === Extract datetime from filename ===
def extract_date(filename):
    match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d_%H-%M-%S')
    return None

# === Compute GCC for each image and ROI ===
gcc_data = []

for file in img_files:
    dt = extract_date(file)
    if not dt:
        continue  # skips files without valid date

    # Load image and convert to numpy array (float32)
    img_path = os.path.join(folder, file)
    img = Image.open(img_path).convert('RGB')
    img_np = np.array(img, dtype=np.float32)

    # Compute GCC per ROI
    for i, roi in enumerate(rois):
        x, y, w, h = map(int, roi)
        crop = img_np[y:y + h, x:x + w]
        R, G, B = crop[:, :, 0], crop[:, :, 1], crop[:, :, 2]
        GCC = G / (R + G + B + 1e-8)  # Avoid division by zero
        GCC_mean = np.nanmean(GCC)
        gcc_data.append({'datetime': dt, 'ROI': f'ROI_{i+1}', 'GCC': GCC_mean})


# === Create dataframe ===
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

# === Final result as dataframe, rois as columns ===
per90_mean_df = pd.DataFrame(window_results)
per90_mean_df['Date'] = pd.to_datetime(per90_mean_df['Date'])

# Pivot tables for plotting
pivot_p90 = per90_mean_df.pivot(index='Date', columns='ROI', values='GCC_90p')
pivot_mean = per90_mean_df.pivot(index='Date', columns='ROI', values='GCC_mean')
# === Plot gcc90 for each roi ===
plt.figure(figsize=(12, 6))
doy = pivot_p90.index.to_series().dt.dayofyear

for roi in pivot_p90.columns:
    plt.plot(doy, pivot_p90[roi], marker='o', markersize=4, linestyle='-', label=roi, linewidth=0.5)
plt.xlabel("DOY")
plt.ylabel("GCC (90th)")
plt.title(f"GCC 3-day non-overlapping 90th percentile – {cam}")
plt.ylim(0.3, 0.7)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# === Plot mean GCC ===
plt.figure(figsize=(12, 6))
doy = pivot_mean.index.to_series().dt.dayofyear

for roi in pivot_mean.columns:
    plt.plot(doy, pivot_mean[roi], marker='o', markersize=4, linestyle='-', label=roi, linewidth=0.5)
plt.xlabel("DOY")
plt.ylabel("GCC (mean)")
plt.title(f"GCC 3-day non-overlapping mean – {cam}")
plt.ylim(0.3, 0.7)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

mean_std = pivot_mean.std().mean()
p90_std = pivot_p90.std().mean()
print(f"Mean GCC STD: {mean_std:.4f}")
print(f"90th Percentile GCC STD: {p90_std:.4f}")

# === Save to CSV ===
# csv_path_90p = os.path.join(output_folder, f'{cam.replace("/", "_")}_3day_per90.csv')
# pivot_p90.to_csv(csv_path_90p)
# print(f"Saved 3-day 90th percentile GCC data to: {csv_path_90p}")

# csv_path_mean = os.path.join(output_folder, f'{cam.replace("/", "_")}_3day_mean.csv')
# pivot_mean.to_csv(csv_path_mean)
# print(f"Saved 3-day mean GCC data to: {csv_path_mean}")
