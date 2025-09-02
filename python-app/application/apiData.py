import requests
import pandas as pd
from io import StringIO
from datetime import datetime
import sqlite3

# Constants
API_URL = "https://api.aquasensor.co.uk/aq.php"
API_PARAMS = {
    'op': 'readings',
    'username': 'shu',
    'token': 'aebbf6305f9fce1d5591ee05a3448eff',
    'sensorid': 'sensor022',
    'fromdate': '01-01-24',
    'todate': '02-01-24'
}
DATABASE_FILE = "aqua_sensor_data1.db"  # Replace with your actual database path

class SensorDataClient:
    def __init__(self, db_file):
        self.db_file = db_file
        self.insert_counter = 0

    def connect_db(self):
        """Establish a connection to the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_file)
            return conn
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return None

    def fetch_sensor_info(self, sensor_name):
        """Fetch sensor information from the database based on the sensor name."""
        conn = self.connect_db()
        if not conn:
            return None
        
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT sensorInfo.sensorID, sensorInfo.riverID, riverData.riverName, 
                sensorInfo.lat || ',' || sensorInfo.long AS latlong
                FROM sensorInfo
                LEFT JOIN riverData ON sensorInfo.riverID = riverData.riverID
                WHERE sensorInfo.sensorName = ? AND sensorInfo.status = 'active'
            ''', (sensor_name,))
            result = cursor.fetchone()
            return result if result else None
        except sqlite3.Error as e:
            print(f"Error fetching sensor info: {e}")
            return None
        finally:
            conn.close()

    def save_data_to_db(self, sensor_name, date, time, message_ctr, temperature, per_do, ml_do):
        """Insert sensor data into the database."""
        sensor_info = self.fetch_sensor_info(sensor_name)
        if not sensor_info:
            print(f"Sensor {sensor_name} is not registered or inactive.")
            return

        sensorID, riverID, river, latlong = sensor_info
        created_at = datetime.strptime(f"{date} {time}", "%d-%m-%y %H:%M:%S")

        conn = self.connect_db()
        if not conn:
            return
        
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO SensorData (
                    SensorID, created_at, updated_at, riverID, river, latlong, 
                    message_counter, temperature, percent_dissolved_oxygen, mg_per_l_dissolved_oxygen
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sensorID, created_at, datetime.utcnow(), riverID, river, latlong, message_ctr, temperature, per_do, ml_do))
            conn.commit()
            self.insert_counter += 1
            print(f"Data inserted successfully. Total inserts: {inseself.insert_counter}")
        except sqlite3.Error as e:
            print(f"Error inserting data into database: {e}")
        finally:
            conn.close()

def fetch_sensor_data(api_url, params):
    """Fetch sensor data from the API."""
    try:
        response = requests.get(api_url, params=params, verify=False)  # Bypass SSL verification
        response.raise_for_status()
        csv_data = response.content.decode('utf-8')
        df = pd.read_csv(StringIO(csv_data))
        return df
    except requests.RequestException as e:
        print(f"Failed to retrieve data from API: {e}")
        return None
    except pd.errors.ParserError as e:
        print(f"Error parsing CSV data: {e}")
        return None

def main():
    # Initialize the SensorDataClient
    client = SensorDataClient(DATABASE_FILE)
    
    # Fetch data from the API
    df = fetch_sensor_data(API_URL, API_PARAMS)
    if df is not None:
        # Loop through the DataFrame and insert data into the database
        for index, row in df.iterrows():
            try:
                client.save_data_to_db(
                    sensor_name=API_PARAMS['sensorid'],  # Using sensor ID as sensor name
                    date=row['date'],
                    time=row['time'],
                    message_ctr=index + 1,  # Message counter based on row index
                    temperature=row['temperature'],
                    per_do=row['percent'],
                    ml_do=row['mg/l']
                )
            except KeyError as e:
                print(f"Missing expected data column: {e}")
    else:
        print("No data fetched from the API, skipping database insertion.")

if __name__ == "__main__":
    main()
