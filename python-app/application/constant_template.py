# constant_template.py
# Constant values for accessing the database, the API and the mqtt broker
# This template contains publicly available values of the constants needed to run the system
# To set your own:
# - save this file as constants.py
# - choose mqtt subscriber name
# - Obtain an API user and token from Aquasensor

# mqtt settings
subscriber_name = "anonymous"
sensor_location = "Lat/Long"
topic = "sensor/#"

mqtt_broker = "excalibur.ioetec.com"
mqtt_broker_port = 1883
keepalive = 60
mqtt_client = None

# Data API
API_URL = "https://api.aquasensor.co.uk/aq.php"

# The API data is not publicly available. Contact Aquasensor.co.uk
API_USER = "user"
API_TOKEN = "token"

# SQLite settings
database_file = 'aqua_sensor_data.db'
