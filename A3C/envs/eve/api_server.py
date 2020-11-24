from flask import Flask, request
from flask_restful import abort, Api, Resource
import logging
import config

app = Flask('API')
api = Api(app)
log = logging.getLogger('werkzeug')  # Remove log requests in the terminal
log.disabled = True

DATA = {
    'sensor1': {
        'mos': None,
        'bitrate': None
    },
    'sensor2': {
        'mos': None,
        'bitrate': None
    },
    'sensor3': {
        'mos': None,
        'bitrate': None
    },
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
        DATA[sensor_id]['mos'] = None
        DATA[sensor_id]['bitrate'] = None
        return '', 204

    # curl http://localhost:5000/api/probe/sensor1 -d "voltage=1.1&current=2.2&active_power=3.2&power_factor=4.1" -X PUT
    def put(self, sensor_id):
        abort_request(sensor_id)
        DATA[sensor_id]['mos'] = request.form['voltage']
        DATA[sensor_id]['bitrate'] = request.form['current']
        return DATA[sensor_id], 201


class DataList(Resource):
    # curl http://localhost:5000/api/probe
    def get(self):
        return DATA

    # curl http://localhost:5000/api/probe -X DELETE
    def delete(self):
        for sensor_id in DATA.keys():
            DATA[sensor_id]['mos'] = None
            DATA[sensor_id]['bitrate'] = None
        return '', 204

    # curl http://localhost:5000/api/probe -d "voltage=1.1&current=2.2&active_power=3.2&power_factor=4.1" -X POST
    def post(self):
        sensor_id = 'sensor%d' % (len(DATA) + 1)
        DATA[sensor_id] = {}
        DATA[sensor_id]['mos'] = request.form['voltage']
        DATA[sensor_id]['bitrate'] = request.form['current']
        return DATA[sensor_id], 201


# API routing resources
api.add_resource(Data, '/api/probe/<string:sensor_id>')
api.add_resource(DataList, '/api/probe')
