from flask import Flask, request
from flask_restful import abort, Api, Resource
import logging
import config

app = Flask('API')
api = Api(app)
log = logging.getLogger('werkzeug')  # Remove log requests in the terminal
log.disabled = True

DATA = {
    'sensor1': {'voltage': '4.5',
                'current': '12.1',
                'active_power': '3.2',
                'power_factor': '3.2'},
    'sensor2': {'voltage': '5.7',
                'current': '21.1',
                'active_power': '5.2',
                'power_factor': '3.2'},
    'sensor3': {'voltage': '4.7',
                'current': '2.1',
                'active_power': '7.2',
                'power_factor': '3.2'},
    'sensor4': {'voltage': '3.7',
                'current': '2.1',
                'active_power': '3.2',
                'power_factor': '3.2'},
    'sensor5': {'voltage': '8.7',
                'current': '6.1',
                'active_power': '4.2',
                'power_factor': '2.2'},
    'sensor6': {'voltage': '2.7',
                'current': '3.1',
                'active_power': '5.2',
                'power_factor': '6.2'}
}


def abort_request(sensor_id):
    if sensor_id not in DATA:
        abort(404, message="{} doesn't exist".format(sensor_id))


def start_api_server():
    app.run(debug=False, host=config.api['address'], port=config.api['port'])


# API Reference
class Data(Resource):
    # curl http://localhost:5000/api/probe/sensor1
    def get(self, sensor_id):
        abort_request(sensor_id)
        return DATA[sensor_id]

    # curl http://localhost:5000/api/probe/sensor1 -X DELETE
    def delete(self, sensor_id):
        abort_request(sensor_id)
        DATA[sensor_id]['voltage'] = None
        DATA[sensor_id]['current'] = None
        DATA[sensor_id]['active_power'] = None
        DATA[sensor_id]['power_factor'] = None
        return '', 204

    # curl http://localhost:5000/api/probe/sensor1 -d "voltage=1.1&current=2.2&active_power=3.2&power_factor=4.1" -X PUT
    def put(self, sensor_id):
        abort_request(sensor_id)
        DATA[sensor_id]['voltage'] = request.form['voltage']
        DATA[sensor_id]['current'] = request.form['current']
        DATA[sensor_id]['active_power'] = request.form['active_power']
        DATA[sensor_id]['power_factor'] = request.form['power_factor']
        return DATA[sensor_id], 201


class DataList(Resource):
    # curl http://localhost:5000/api/probe
    def get(self):
        return DATA

    # curl http://localhost:5000/api/probe -X DELETE
    def delete(self):
        for sensor_id in DATA.keys():
            DATA[sensor_id]['voltage'] = None
            DATA[sensor_id]['current'] = None
            DATA[sensor_id]['active_power'] = None
            DATA[sensor_id]['power_factor'] = None
        return '', 204

    # curl http://localhost:5000/api/probe -d "voltage=1.1&current=2.2&active_power=3.2&power_factor=4.1" -X POST
    def post(self):
        sensor_id = 'sensor%d' % (len(DATA) + 1)
        DATA[sensor_id] = {}
        DATA[sensor_id]['voltage'] = request.form['voltage']
        DATA[sensor_id]['current'] = request.form['current']
        DATA[sensor_id]['active_power'] = request.form['active_power']
        DATA[sensor_id]['power_factor'] = request.form['power_factor']
        return DATA[sensor_id], 201


# API routing resources
api.add_resource(Data, '/api/probe/<string:sensor_id>')
api.add_resource(DataList, '/api/probe')
