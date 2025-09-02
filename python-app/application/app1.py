# integrated_app.py

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime, timezone
import logging
from constant import database_file

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

def get_db_connection():
    conn = sqlite3.connect(database_file)
    conn.row_factory = sqlite3.Row
    return conn

def get_next_sequence_value(sequence_name):
    """ Get the next value in a sequence. """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''INSERT INTO counters (id, sequence_value) VALUES (?, ?) 
                      ON CONFLICT(id) DO UPDATE SET sequence_value=sequence_value+1 WHERE id=?''', 
                   (sequence_name, 1, sequence_name))
    conn.commit()

    cursor.execute('SELECT sequence_value FROM counters WHERE id=?', (sequence_name,))
    sequence_value = cursor.fetchone()['sequence_value']

    conn.close()
    return sequence_value

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT created_at, percent_dissolved_oxygen FROM SensorData')
        data = cursor.fetchall()
        
        conn.close()
        
        if not data:
            return jsonify({"error": "No data found in SQLite database."})
        
        # Convert data to a list of dictionaries
        result = [dict(row) for row in data]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/todays-data', methods=['GET'])
def get_todays_data():
    try:
        # Define UTC timezone
        utc = timezone.utc

        # Get current time in UTC
        now = datetime.now(utc)
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Query for data between start and end of today
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''SELECT created_at, percent_dissolved_oxygen FROM SensorData WHERE created_at >= ? AND created_at < ?''', 
                       (start_of_today, end_of_today))
        results = cursor.fetchall()

        conn.close()

        # Convert rows to list of dictionaries and format datetime
        results = [dict(row) for row in results]
        for result in results:
            if 'created_at' in result:
                result['created_at'] = result['created_at'].isoformat()

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/submit_river_data', methods=['POST'])
def submit_river_data():
    try:
        # Parse JSON data from request
        river_data = request.json
        logging.debug(f"Received river data: {river_data}")

        # Assign riverID and created_at fields
        river_data['riverID'] = get_next_sequence_value('riverID')
        river_data['created_at'] = datetime.now(timezone.utc).isoformat()

        logging.debug(f"Final river data to insert: {river_data}")

        # Insert data into SQLite
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''INSERT INTO riverData (riverID, riverName, location, status, created_at)
                          VALUES (?, ?, ?, ?, ?)''',
                       (river_data['riverID'], river_data['riverName'], river_data['location'],
                        river_data['status'], river_data['created_at']))

        conn.commit()
        conn.close()

        logging.debug("River data inserted successfully")
        return jsonify({'status': 'success', 'data': river_data}), 200
    except Exception as e:
        logging.error(f"Error storing river data: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/navbar')
def navbar():
    return render_template('navbar.html')

@app.route('/map')
def map():
    return render_template('map.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/graph')
def graph():
    return render_template('graph.html')

# Handle favicon.ico requests to avoid 404 errors
@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)
