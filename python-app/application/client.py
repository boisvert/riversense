# client.py

from datetime import datetime
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from constant import database_file

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class Client:
    topic_interested = None
    message_counter = 0

    def __init__(self, client_name, location, topic_interested):
        self.subscriber_client_name = client_name
        self.subscriber_client_location = location
        self.topic_interested = topic_interested
        self.executor = ThreadPoolExecutor(max_workers=10)
        logging.debug(f"Client initialized for topic: {topic_interested}")

    def mydatetime(self):
        return datetime.now().strftime("%Y.%m.%d %H%M%S")

    def on_connect(self, client, userdata, flags, rc):
        logging.debug(f"{self.mydatetime()}: result code {rc}")
        self.mqtt_client.subscribe(self.topic_interested)
        logging.debug(f"{self.mydatetime()}: Subscription completed, Waiting for message....")
        print(f"{self.mydatetime()}: Subscription completed, Waiting for message....")

    def hello(self):
        logging.debug("hello")

    def is_json(self, myjson):
        try:
            json.loads(myjson)
        except ValueError as e:
            return False
        return True

    def on_message(self, client, userdata, msg):
        self.executor.submit(self.process_message, msg)

    def process_message(self, msg):
        try:
            topicfrmPub = msg.topic
            msg_data = str(msg.payload.decode('utf-8'))
            logging.debug(f"Received message: {msg_data} on topic: {topicfrmPub}")
            print(f"Received message: {msg_data} on topic: {topicfrmPub}")

            data_parts = msg_data.strip('{}').split(',')
            if len(data_parts) != 7:
                logging.debug("Unexpected message format, skipping")
                return

            date = data_parts[0]
            time = data_parts[1]
            sensor_name = data_parts[2]
            message_ctr = int(data_parts[3])
            temperature = float(data_parts[4])
            per_do = float(data_parts[5])
            ml_do = float(data_parts[6])

            logging.debug(f"Parsed data - Date: {date}, Time: {time}, Sensor Name: {sensor_name}, "
                          f"Message Counter: {message_ctr}, Temperature: {temperature}, "
                          f"% Dissolved Oxygen: {per_do}, mg/L Dissolved Oxygen: {ml_do}")

            self.message_counter += 1
            logging.debug(f"Total messages received so far: {self.message_counter}")
            logging.debug(f"{self.mydatetime()}: Waiting for message....")

            self.save_to_db(sensor_name, message_ctr, temperature, per_do, ml_do)
        except Exception as e:
            logging.error(f"Error processing message: {e}")

    def save_to_db(self, sensor_name, message_ctr, temperature, per_do, ml_do):
        try:
            conn = sqlite3.connect(database_file)
            cursor = conn.cursor()

            # Fetch riverID, river, and latlong from sensorInfo based on sensor_name and check if sensor is active
            cursor.execute('''
                SELECT sensorInfo.riverID, riverData.riverName, sensorInfo.lat || ',' || sensorInfo.long AS latlong
                FROM sensorInfo
                LEFT JOIN riverData ON sensorInfo.riverID = riverData.riverID
                WHERE sensorInfo.sensorName = ? AND sensorInfo.status = 'active'
            ''', (sensor_name,))
            result = cursor.fetchone()
            if result:
                riverID, river, latlong = result
            else:
                logging.debug(f"Sensor {sensor_name} is not registered or not active, skipping")
                return

            cursor.execute('''
                INSERT INTO SensorData (SensorID, created_at, updated_at, riverID, river, latlong, message_counter, temperature, percent_dissolved_oxygen, mg_per_l_dissolved_oxygen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sensor_name, datetime.utcnow(), datetime.utcnow(), riverID, river, latlong, message_ctr, temperature, per_do, ml_do))
            conn.commit()
            conn.close()
            logging.debug("Data inserted successfully")
        except Exception as e:
            logging.error(f"Error inserting data into SQLite: {e}")
