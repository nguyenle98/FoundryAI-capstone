import requests
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
import os
import pdb
from time import sleep

def extract_data():

    url = f"https://api.exchangerate.host/live?access_key=24350d1a3226aad12b9e47f7fe2fc424"
    print("Getting data from:", url)
    response = requests.get(url=url, timeout=10)
    response.raise_for_status()
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.status_code}")
    
    data = response.json()
    results = data.get("results", [])
    print(data)

    if not results:
        return data  # No more data to fetch
    
def main():
    print(" Extracting data...")
    file_path_1, new_last_id_1 = extract_data()  # First extraction
    print(f"Extracted data from offset {0} to {new_last_id_1}")

if __name__ == "__main__":
    main()
