import requests
import json
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import os

BURREL_KEY_PATH=input("Please enter the path to the dataframe of Burrel access-keys: ")

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR=os.path.join(ROOT_DIR, "data", "temp_timeseries")
os.makedirs(OUTPUT_DIR, exist_ok=True)

auth_url="https://app.burrelcameras.com/api/v1/public/auth"
export_url="https://app.burrelcameras.com/api/v1/public/export"

def run():

    burrel_keys_df=pd.read_csv(BURREL_KEY_PATH, delimiter=";", encoding="latin8")

    for i, row in burrel_keys_df.iterrows():

        #Get access token
        auth_params={
            "accessKey": f"{row["access_key"]}"
        }
        auth_headers={
            'Content-type':'application/json', 
            'Accept':'application/json'
        }
        auth_response = requests.post(auth_url, json=auth_params, headers=auth_headers)
        token=json.loads(auth_response.text)["token"]
        token_str="Bearer " + token

        #Export the data
        export_response=requests.get(export_url, headers={"Authorization": token_str})
        export_json=json.loads(export_response.text)["media"]

        temp_df=pd.DataFrame(export_json).drop(columns=["thumbnail", "type"])
        temp_df["date"]=pd.to_datetime(temp_df["created"], format='%Y-%m-%dT%H:%M:%SZ')
        temp_df=temp_df.sort_values(by="date")

        daily_temp_df=temp_df.groupby([temp_df["date"].dt.date])["temperature"].mean()
        daily_temp_df.to_csv(os.path.join(OUTPUT_DIR, f"{row["Kamera"]}.csv"))
        print(f"Saved daily temperature mean of {row["Kamera"]}!")

def main():
    run()

if __name__ == "__main__":
    main()

