##!/usr/bin/env python3

"""A KNX to InfluxDB Bridge

This script receives KNX data and saves it to InfluxDB.

"""

import asyncio
import inspect
import logging
import re
import xknx.remote_value.remote_value_sensor as sensor
from influxdb import InfluxDBClient
from knxproj.knxproj import KnxprojLoader
from pathlib import Path
from xknx import XKNX
from xknx.devices import (
    BinarySensor, Climate, Cover, DateTime, ExposeSensor, Fan, Light,
    Notification, Scene, Sensor, Switch)

INFLUXDB_ADDRESS = '192.168.1.168'
INFLUXDB_USER = 'root'
INFLUXDB_PASSWORD = 'root'
INFLUXDB_DATABASE = 'knx'


class KnxBridge:
    def __init__(self):
        self._build_xknx_dpt_map()
        self._build_knx_sensor_list()

    async def start(self):
        self.xknx = XKNX()
        self._register_xknx_sensors()
#        self.xknx.telegram_queue.register_telegram_received_cb(self.telegram_received_cb)
        self.xknx.devices.register_device_updated_cb(self.device_updated_cb)

        await self.xknx.start(daemon_mode=True)

        await self.xknx.stop()

    async def telegram_received_cb(self, telegram):
        """Do something with the received telegram."""
        print("Telegram received: {0}".format(telegram))
        return True

    async def device_updated_cb(self, device):
        self._send_sensor_data_to_influxdb((device.name, device.resolve_state(), device.unit_of_measurement()))

    def _send_sensor_data_to_influxdb(self, sensor_data):
        influxdb_client = InfluxDBClient(INFLUXDB_ADDRESS, 8086, INFLUXDB_USER, INFLUXDB_PASSWORD, INFLUXDB_DATABASE)
        vtype = type(sensor_data[1]).__name__
        vfield = 'SensorValue_%s' % vtype
        json_body = [
            {
                'measurement': 'knx',
                'tags': {
                    'GroupAddressName': sensor_data[0],
                    'Unit': sensor_data[2],
                    'DataType': vtype
                 },
                'fields': {
                    vfield: sensor_data[1]
                }
            }
        ]
        logging.info("Updating influxdb: %s" % json_body)
        influxdb_client.write_points(json_body)

    def _build_xknx_dpt_map(self):
        """ Build a map of xknx supported DPTs and value_types. The DPTs are
            taken from the xknx function docstrings. """
        self.X_DPT = {}
        self.X_VT = {}

        for name, func_obj in inspect.getmembers(sensor):
            if name.startswith('DPT'):
                try:
                    type = re.findall("DPT [0-9.*]+", func_obj.__doc__)[0]
                    self.X_DPT[type] = name
                except IndexError:
                    logging.warning('Could not extract DPT from xknx %s' % name)

        for dtype in sensor.RemoteValueSensor.DPTMAP:
            self.X_VT[sensor.RemoteValueSensor.DPTMAP[dtype].__name__] = dtype

    def _init_influxdb_database(self):
        databases = influxdb_client.get_list_database()
        if len(list(filter(lambda x: x['name'] == INFLUXDB_DATABASE, databases))) == 0:
            influxdb_client.create_database(INFLUXDB_DATABASE)
        influxdb_client.switch_database(INFLUXDB_DATABASE)

    def _register_xknx_sensors(self):
        for addr, ga in self.groupaddresses.items():
            if ga['value_type'] is not None:
                sensor = Sensor(self.xknx,
                                ga['name'],
                                group_address_state=addr,
                                value_type=ga['value_type'])
                self.xknx.devices.add(sensor)
            else:
                pass

    def _build_knx_sensor_list(self, project_file="ets_export.knxproj"):
        knxproj_path = Path(project_file)
        group_addresses, _ = KnxprojLoader(knxproj_path=knxproj_path, parse_lenient=True).run()
        groupaddress_to_dtype = {}
        for group_address in group_addresses:
            try:
                dtype_hr = 'DPT %i.%-0.3i' % tuple([int(x) for x in group_address.dtype.split('-')[1:]])
            except (TypeError, AttributeError):
                dtype_hr = group_address.dtype
            try:
                vtype = self.X_VT[self.X_DPT[dtype_hr]]
            except KeyError:
                logging.error("Couldn't resolve %s", dtype_hr)
                vtype = None
            groupaddress_to_dtype[group_address.get_ga_str()] = {
                "dtype": group_address.dtype,
                "name": group_address.name,
                "dtype_human": dtype_hr,
                "value_type": vtype,
            }
        self.groupaddresses = groupaddress_to_dtype

def main():
#    _init_influxdb_database()
    logging.basicConfig(level=logging.INFO)
    knx = KnxBridge()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(knx.start())
    loop.close()

if __name__ == '__main__':
    print('KNX to InfluxDB bridge')
    main()
