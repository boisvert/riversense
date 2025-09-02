from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import Flask, render_template, jsonify
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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''INSERT INTO counters (id, sequence_value) VALUES (?, 1) 
                          ON CONFLICT(id) DO UPDATE SET sequence_value=sequence_value+1 WHERE id=?''',
                       (sequence_name, sequence_name))
        conn.commit()

        cursor.execute('SELECT sequence_value FROM counters WHERE id=?', (sequence_name,))
        sequence_value = cursor.fetchone()[0]

        conn.close()
        return sequence_value
    except Exception as e:
        logging.error(f"Error getting next sequence value: {e}")
        return None

@app.route('/submit_river_data', methods=['POST'])
def submit_river_data():
    try:
        data = request.json
        riverName = data['riverName']
        location = data['location']
        latitude = data['latitude']
        longitude = data['longitude']
        status = data['status']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO riverData (riverName, location, latitude, longitude, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (riverName, location, latitude, longitude, status))
        conn.commit()
        conn.close()

        return jsonify({'status': 'success', 'data': data}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/update_river_info/<int:riverID>', methods=['PUT'])
def update_river_info(riverID):
    try:
        data = request.json
        riverName = data['riverName']
        location = data['location']
        latitude = data['latitude']
        longitude = data['longitude']
        status = data['status']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE riverData
            SET riverName = ?, location = ?, latitude = ?, longitude = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE riverID = ?
        ''', (riverName, location, latitude, longitude, status, riverID))
        conn.commit()
        conn.close()

        return jsonify({'status': 'success', 'data': data}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_rivers', methods=['GET'])
def get_rivers():
    conn = get_db_connection()
    rivers = conn.execute('SELECT * FROM riverData').fetchall()
    conn.close()
    return jsonify({'rivers': [dict(ix) for ix in rivers]}), 200

@app.route('/submit_sensor_info', methods=['POST'])
def submit_sensor_info():
    try:
        sensor_data = request.json
        logging.debug(f"Received sensor data: {sensor_data}")

        sensor_data['sensorID'] = get_next_sequence_value('sensorID')
        sensor_data['created_at'] = datetime.now(timezone.utc)
        sensor_data['updatedAt'] = datetime.now(timezone.utc)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''INSERT INTO sensorInfo (sensorID, sensorName, location, lat, long, created_at, updatedAt, riverID, status)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (sensor_data['sensorID'], sensor_data['sensorName'], sensor_data['location'], sensor_data['lat'], sensor_data['long'], sensor_data['created_at'], sensor_data['updatedAt'], sensor_data['riverID'], sensor_data['status']))
        
        conn.commit()
        conn.close()
        
        logging.debug("Sensor info inserted successfully")
        return jsonify({'status': 'success', 'data': sensor_data}), 200
    except Exception as e:
        logging.error(f"Error storing sensor info: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/update_sensor_info/<int:sensorID>', methods=['PUT'])
def update_sensor_info(sensorID):
    try:
        sensor_data = request.json
        logging.debug(f"Received updated sensor data: {sensor_data}")

        sensor_data['updatedAt'] = datetime.now(timezone.utc)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''UPDATE sensorInfo 
                          SET sensorName = ?, location = ?, lat = ?, long = ?, updatedAt = ?, riverID = ?, status = ?
                          WHERE sensorID = ?''',
                       (sensor_data['sensorName'], sensor_data['location'], sensor_data['lat'], sensor_data['long'], sensor_data['updatedAt'], sensor_data['riverID'], sensor_data['status'], sensorID))
        
        conn.commit()
        conn.close()
        
        logging.debug("Sensor info updated successfully")
        return jsonify({'status': 'success', 'data': sensor_data}), 200
    except Exception as e:
        logging.error(f"Error updating sensor info: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_locations', methods=['GET'])
def get_locations():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT riverID, location FROM riverData')
        locations = [{'riverID': row['riverID'], 'location': row['location']} for row in cursor.fetchall()]

        conn.close()
        return jsonify({'locations': locations}), 200
    except Exception as e:
        logging.error(f"Error fetching locations: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_sensors', methods=['GET'])
def get_sensors():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT sensorID, sensorName, status, location, lat, long FROM sensorInfo')
        sensors = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jsonify({'sensors': sensors}), 200
    except Exception as e:
        logging.error(f"Error fetching sensors: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_sensor_names', methods=['GET'])
def get_sensor_names():
    try:
        #logging.debug(f"Enter")
        riverID = request.args.get('riverID')
        riverID = int(riverID)
        #logging.debug(f"Received riverID: {riverID}")
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT sensorName FROM sensorInfo WHERE riverID =?',(riverID,))
        sensors = [dict(row) for row in cursor.fetchall()]
        #logging.debug(sensors)

        conn.close()
        return jsonify(sensors)
    except Exception as e:
        logging.error(f"Error fetching sensors: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500    

@app.route('/get_river_name', methods=['GET'])
def get_river_name():
    try:
        logging.debug(f"Enter")
        riverID = request.args.get('riverID')
        riverID = int(riverID)
        logging.debug(f"Received riverID: {riverID}")
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT riverName FROM riverData WHERE riverID = ?',(riverID,))
        riverName = [dict(row) for row in cursor.fetchall()]
        logging.debug(riverName)
        conn.close()
        return jsonify(riverName), 200
    except Exception as e:
        logging.error(f"Error fetching locations: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_sensor_data', methods=['GET'])
def get_sensor_data():
    try:
        sensor_id = request.args.get('SensorID')
        app.logger.debug(f'Received sensor_id: {sensor_id}')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 100000))
        offset = (page - 1) * limit

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM SensorData WHERE SensorID = ?
            LIMIT ? OFFSET ?
        ''', (sensor_id,limit, offset))
        sensors = [dict(row) for row in cursor.fetchall()]

        cursor.execute('SELECT COUNT(*) FROM SensorData')
        total_records = cursor.fetchone()[0]
        total_pages = (total_records + limit - 1) // limit

        conn.close()
        #app.logger.debug(f'Received:{sensors}')
        return jsonify(sensors)
        '''return jsonify({
            'sensors': sensors,
            'page': page,
            'total_pages': total_pages
        }), 200'''
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_todays_sensor_data', methods=['GET'])
def get_todays_sensor_data():
    try:
        sensor_id = request.args.get('SensorID')
        app.logger.debug(f'Received sensor_id: {sensor_id}')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 100000))
        offset = (page - 1) * limit

        conn = get_db_connection()
        cursor = conn.cursor()
    
        cursor.execute('''
            SELECT * FROM SensorData
            WHERE date(created_at) = date('now') AND SensorID = ?  
            LIMIT ? OFFSET ?
        ''', (sensor_id,limit, offset))
        sensors = [dict(row) for row in cursor.fetchall()]

        cursor.execute('SELECT COUNT(*) FROM SensorData WHERE date(created_at) = date(\'now\')')
        total_records = cursor.fetchone()[0]
        total_pages = (total_records + limit - 1) // limit

        conn.close()
        return jsonify(sensors)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/get_data', methods=['GET'])
def get_data():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10,000))
        offset = (page - 1) * limit

        conn = get_db_connection()
        cursor = conn.cursor()
    
        cursor.execute('''
            SELECT * FROM SensorData 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        sensors = [dict(row) for row in cursor.fetchall()]

        cursor.execute('SELECT COUNT(*) FROM SensorData WHERE date(created_at) = date(\'now\')')
        total_records = cursor.fetchone()[0]
        total_pages = (total_records + limit - 1) // limit

        conn.close()
        return jsonify(sensors)
       
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_sensors_for_map', methods=['GET'])
def get_sensors_for_map():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM sensorInfo')
        sensors = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jsonify(sensors)
    except Exception as e:
        logging.error(f"Error fetching sensors: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/panel2')
def panel2():
    return render_template('panel2.html')

@app.route('/panels')
def panels():
    return render_template('panels.html')

@app.route('/panel1')
def index():
    return render_template('panel1.html')

@app.route('/index_sensor')
def index_sensor():
    return render_template('index_sensor.html')

@app.route('/navbar')
def navbar():
    return render_template('navbar.html')

@app.route('/map')
def map():
    return render_template('map.html')



if __name__ == '__main__':
    app.run(debug=True)
