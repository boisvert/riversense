# init_db.py
import sqlite3

database_file = 'aqua_sensor_data.db'

conn = sqlite3.connect(database_file)
c = conn.cursor()

# Create riverData table
c.execute('''
            CREATE TABLE IF NOT EXISTS riverData (
                riverID INTEGER PRIMARY KEY AUTOINCREMENT,
                riverName TEXT NOT NULL,
                location TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    # Create sensorInfo table
c.execute('''CREATE TABLE IF NOT EXISTS sensorInfo (
                    sensorID INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensorName TEXT NOT NULL,
                    location TEXT NOT NULL,
                    lat TEXT NOT NULL,
                    long TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    riverID INTEGER,
                    status TEXT NOT NULL,
                    FOREIGN KEY (riverID) REFERENCES riverData(riverID)
                )''')

    # Create SensorData table
c.execute('''CREATE TABLE IF NOT EXISTS SensorData (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    SensorID INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    riverID INTEGER,
                    river TEXT,
                    latlong TEXT,
                    message_counter INTEGER,
                    temperature REAL,
                    percent_dissolved_oxygen REAL,
                    mg_per_l_dissolved_oxygen REAL,
                    FOREIGN KEY (SensorID) REFERENCES sensorInfo(sensorID),
                    FOREIGN KEY (riverID) REFERENCES riverData(riverID)
                )''')

    # Create readingInfo table
c.execute('''CREATE TABLE IF NOT EXISTS readingInfo (
                    readingID INTEGER PRIMARY KEY AUTOINCREMENT,
                    readingType TEXT NOT NULL,
                    value REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sensorDataID INTEGER,
                    FOREIGN KEY (sensorDataID) REFERENCES SensorData(id)
                )''')

    # Create counters table for sequence generation
c.execute('''CREATE TABLE IF NOT EXISTS counters (
                    id TEXT PRIMARY KEY,
                    sequence_value INTEGER
                )''')

    # Initialize counters if they don't exist
c.execute('''INSERT OR IGNORE INTO counters (id, sequence_value) VALUES
                ('Sensor_id', 0),
                ('riverID', 0),
                ('readingID', 0),
                ('sensorID', 0)''')

conn.commit()
conn.close()
