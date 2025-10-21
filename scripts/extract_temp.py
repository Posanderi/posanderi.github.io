# -*- coding: utf-8 -*-
"""
Created on Wed Jun  4 10:26:11 2025

@author: kirsi

Purpose of the script is to extract the temperature information from the image. This script now works relatively well,
put it struggles with separating 1 and 7 --> values like 17, 21, 27 are unreliable.

Issue example: 1.4. 013 read as 139, 21 degrees read usually as 27 or 179.

Handles negative values moderately, some -1 degrees shown as -07 or -017


In the end some plotting & saving the results as CSV.

"""
from PIL import Image
import pytesseract
import os
import cv2
import re
import numpy as np
import pandas as pd
import datetime as datetime
import matplotlib.pyplot as plt

#tesseract OCR needs to be separately downloaded online
#from here https://github.com/UB-Mannheim/tesseract/wiki
pytesseract.pytesseract.tesseract_cmd = 'C:\\Users\\kirsi\\AppData\\Local\\Programs\\Tesseract-OCR\\tesseract.exe'

# select camera
# cam = 'Keskuspuisto'
#cam = 'Roihuvuori'
#cam = 'Herttoniemi'
#cam = 'Patterinmäki'
cam = 'Toukola'
#cam = 'Laakso'
#cam = 'Haltiala'
#cam = 'Eduardo'
#cam = 'Tähtitorninmäki'
folder = 'C:\\Users\\kirsi\\Documents\\AmandaPHD\\Toukola\\' + cam


#function to enhance the data so that it reads the temperature from cropped area, 
def preprocess_for_ocr(pil_image):
    # Crop only the small area where the temperature appears
    width, height = pil_image.size
    crop_box = (width * 0.7687, height * 0.969, width * 0.88, height)
    temp_region = pil_image.crop(crop_box)

    # Convert to grayscale (no enhancement yet)
    gray = temp_region.convert('L')

    # Convert to NumPy and invert (white-on-black to black-on-white)
    img_cv = np.array(gray)
    inverted = cv2.bitwise_not(img_cv)

    # Apply standard binary thresholding
    _, thresh = cv2.threshold(inverted, 140, 255, cv2.THRESH_BINARY)

    return Image.fromarray(thresh)

# extracts the values, set which characters are considered and added to output strings
def extract_temperature(text):
    # Allow digits, C, and minus sign
    clean_text = re.sub(r'[^0-9C\-]', '', text.upper())

    # Look for optional '-' sign followed by 1-3 digits and 'C'
    match = re.search(r'(-?\d{1,3})C', clean_text)
    if match:
        value_str = match.group(1)
        
        # zero-pad positive values to 3 digits, keep negative as is
        if value_str.startswith('-'):
            value = int(value_str)  # convert to int including minus
            value_str_padded = value_str  # keep as is for display
        
        else:
            value = int(value_str)
            value_str_padded = value_str.zfill(3)
            
        return f"{value_str_padded}°C", value
    
    else:
        return "NA", None

output_data = []

for idx, filename in enumerate(sorted(os.listdir(folder))):
    if filename.lower().endswith('.jpg'):
        path = os.path.join(folder, filename)
        with Image.open(path) as pil_img:
            processed_img = preprocess_for_ocr(pil_img.copy())

        processed_img = preprocess_for_ocr(pil_img)

        config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789°C-'
        raw_text = pytesseract.image_to_string(processed_img, config=config).strip()
        print(f"Raw OCR: '{raw_text}'")

        temp_str, temp_val = extract_temperature(raw_text)

        # Try to extract a timestamp from the filename (adjust as needed) --> note that the time stamp is incorrect in filename
        try:
           # Match date and time in format 2025-06-08_13-00-23
           match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', filename)
           if match:
               date_part = match.group(1)
               time_part = match.group(2).replace('-', ':')
               datetime_str = f"{date_part} {time_part}"
               timestamp = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
               
           else:
               timestamp = None
            
        except Exception as e:
            print(f"Timestamp parsing failed for {filename}: {e}")
            timestamp = None
        
        output_data.append({
            'filename': filename,
            'datetime': timestamp,
            'temperature_C': temp_val,
            'camera': cam
        })

        print(f"{idx+1:03}: {filename} → {temp_str}")




# ------- Adjusting the extraction ROI ----------------
# testing with one picture (can be used to adjust the box where text is extracted)
# fp = os.path.join(folder, sorted(os.listdir(folder))[470]) # just a random image from the folder
# img = Image.open(fp)
# img.show()

# # Convert to OpenCV format for thresholding
# cv_image = np.array(img)
# _, thresh_img = cv2.threshold(cv_image, 180, 255, cv2.THRESH_BINARY_INV)  # Invert to black text

# processed_pil = Image.fromarray(thresh_img)

# crop_box = (width * 0.7685, height * 0.969, width * 0.88, height)
# temp_reg = processed_pil.crop(crop_box)
# temp_reg.show()

# text = pytesseract.image_to_string(processed_pil)
# processed_pil.show() 
# custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789°C'
# text = pytesseract.image_to_string(processed_pil, config=custom_config)
# print(text)



# -------- clean the data -----------
df = pd.DataFrame(output_data)
# Sort by timestamp to make sure previous and next comparisons make sense
df = df.sort_values('datetime').reset_index(drop=True)

# Make a copy of the original values to avoid overwriting prematurely
temps = df['temperature_C'].values



# List to hold cleaned temperatures
cleaned_temps = []

for i in range(len(temps)):
    current = temps[i]
    
    if i == 0 or i == len(temps) - 1:
        # First and last values: no previous or next to compare with
        cleaned_temps.append(current)
    else:
        prev = temps[i - 1]
        next_ = temps[i + 1]

        # Check if the current value is a spike --> here you can adjust the number to define what is considered as unreliable
        # if the temperature is X degrees higher or lower than the previous and next temp, it is defined as a mistake (NA)
        if abs(current - prev) > 10 or abs(current - next_) > 10:
            cleaned_temps.append(np.nan)
        else:
            cleaned_temps.append(current)

# Assign the cleaned temperatures back to the dataframe
df['temperature_C_cleaned'] = cleaned_temps

plt.figure(figsize=(10, 5))
#plt.plot(df['datetime'], df['temperature_C'], label='Original', alpha=0.5, linestyle='--')
plt.plot(df['datetime'], df['temperature_C_cleaned'], label='Cleaned', marker='o')
plt.title(f'Temperature pattern (all) - {cam}')
plt.xlabel('Time')
plt.ylabel('Temperature (°C)')
plt.legend()
plt.grid(True)
plt.show()

# # Save to CSV (cleaned data)
# output_folder = 'C:\\Users\\kirsi\\Documents\\AmandaPHD\\Toukola\\'
# output_csv_path = os.path.join(output_folder, f'{cam}_temperatures.csv')
# df.to_csv(output_csv_path, index=False)
# print(f"Saved CSV to: {output_csv_path}")


# Calculate daily median temperature
df['date'] = df['datetime'].dt.date
daily_temps = df.groupby('date')['temperature_C_cleaned'].median().reset_index()
daily_temps = daily_temps.rename(columns={'temperature_C_cleaned':'temp_m'})

# Save to CSV
output_folder = 'C:\\Users\\kirsi\\Documents\\AmandaPHD\\Toukola\\'
output_csv_path = os.path.join(output_folder, f'{cam}_temps_m.csv')
daily_temps.to_csv(output_csv_path, index=False)
print(f"Saved CSV to: {output_csv_path}")


# Create the plot (median values)
plt.figure(figsize=(10, 5))
plt.plot(daily_temps['date'], daily_temps['temperature_C_cleaned'], label='Daily median', marker='o')
plt.title(f'Daily median temperature pattern - {cam}')
plt.xlabel('Date')
plt.ylabel('Temperature (°C)')
plt.legend()
plt.grid(True)
plt.show()


