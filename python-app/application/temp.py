from datetime import datetime
from time import sleep
import json
from pymongo import MongoClient

class Client:
    topic_interested = None
    message_counter = 0

    def __init__(self, client_name, location, topic_interested, mongo_url, mongo_db, mongo_collection):
        self.subscriber_client_name = client_name
        self.subscriber_client_location = location
        self.topic_interested = topic_interested
        self.mongo_client = MongoClient(mongo_url)
        self.mongo_db = self.mongo_client[mongo_db]
        self.mongo_collection = self.mongo_db[mongo_collection]
        print(f"Connected to MongoDB at {mongo_url}, Database: {mongo_db}, Collection: {mongo_collection}")

    def mydatetime(self):
        return datetime.now().strftime("%Y.%m.%d %H%M%S")

    def on_connect(self, client, userdata, flags, rc):
        print(self.mydatetime(), ": result code " + str(rc))
        self.mqtt_client.subscribe(self.topic_interested)
        print(self.mydatetime(), ": Subscription completed, Waiting for message....")

    def hello(self):
        print("hello")

    def is_json(self, myjson):
        try:
            json.loads(myjson)
        except ValueError as e:
            return False
        return True

    def on_message(self, client, userdata, msg):
        try:
            topicfrmPub = msg.topic
            msg_data = str(msg.payload.decode('utf-8'))
            print(f"Received message: {msg_data} on topic: {topicfrmPub}")

            data_parts = msg_data.strip('{}').split(',')
            if len(data_parts) != 7:
                print("Unexpected message format, skipping")
                return

            date = data_parts[0]
            time = data_parts[1]
            sensor_id = data_parts[2]
            message_ctr = int(data_parts[3])
            temperature = float(data_parts[4])
            per_do = float(data_parts[5])
            ml_do = float(data_parts[6])
            
            print(f"Parsed data - Date: {date}, Time: {time}, Sensor ID: {sensor_id}, "
                  f"Message Counter: {message_ctr}, Temperature: {temperature}, "
                  f"% Dissolved Oxygen: {per_do}, mg/L Dissolved Oxygen: {ml_do}")
            
            self.message_counter += 1
            print("Total messages received so far: ", self.message_counter)
            print(self.mydatetime(), ": Waiting for message....")
            
            self.save_to_mongodb(date, time, sensor_id, message_ctr, temperature, per_do, ml_do)
        except Exception as e:
            print(f"Error processing message: {e}")

    def save_to_mongodb(self, date, time, sensor_id, message_ctr, temperature, per_do, ml_do):
        try:
            data = {
                "date": date,
                "time": time,
                "sensor_id": sensor_id,
                "message_counter": message_ctr,
                "temperature": temperature,
                "percent_dissolved_oxygen": per_do,
                "mg_per_l_dissolved_oxygen": ml_do
            }
            print(f"Attempting to insert data: {data}")
            result = self.mongo_collection.insert_one(data)
            print(f"Data inserted with id: {result.inserted_id}")
        except Exception as e:
            print(f"Error inserting data into MongoDB: {e}")




