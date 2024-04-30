#!/usr/bin/python3
# 2024-03-19
# Script to read GPS and PM sensor and write to SQLite db
# the PMS5003 is running off of version 0.5 of the library, not the latest version.

import sqlite3
import time
from pa1010d import PA1010D
import plantower
from operator import itemgetter
from datetime import datetime
import board
import neopixel
#placeholder for influxdb stuff
import requests
from influxdb import InfluxDBClient
import os
import sys
import csv

#setup neopixels
NUM_PIXELS = 8
ORDER = neopixel.RGB
PIXEL_PIN = board.D18

#placeholder code for influxdb setup
HOST = "192.168.0.127" # IP address of influx server
PORT = 8086 # Port for influx server (default)
INFLUXDB_DB = "personal-aq-sensor" # Influx database name
USER = "admin" # the user/password created for the pi, with write access
PASSWORD = "admin"
PARTICLE_DEV = "rpi-pms5003" #Device tag for influxdb
GPS_DEV =  "rpi-pa1010d" #Device tag for influxdb
PARTICIPANT_ID = "PARTICIPANT_1" #Participant ID for influxdb


# Define sensors and neopixels
gps = PA1010D()
pms5003 = plantower.Plantower(port='/dev/serial0')
pixels = neopixel.NeoPixel(
    PIXEL_PIN, NUM_PIXELS, brightness=0.2, auto_write=False, pixel_order=ORDER
)

tday = datetime.today().strftime('%Y-%m-%d')
print(tday)

# Define database filename (modify as needed)
database_file = "/home/pi/aq-sensor/sensor_data.db"

#Placeholder for various influxdb related functions
#String search function
def search(values, searchFor):
    for k in values:
        for v in k:
            if searchFor in v:
                return True
    return False

def write_influxdb(VALUE_DICT):
    particle_data = [
    {
      "measurement": PARTICLE_DEV,
          "tags": {
              "participant_id": PARTICIPANT_ID,
          },
          "time": VALUE_DICT['timestamp'],
          "fields": {
              "pm25" : VALUE_DICT['pm25'],
              "pm10": VALUE_DICT['pm10'],
              "pm1": VALUE_DICT['pm1']
          }
      }
    ]
    gps_data = [
    {
      "measurement": GPS_DEV,
          "tags": {
              "participant_id": PARTICIPANT_ID,
          },
          "time": VALUE_DICT['timestamp'],
          "fields": {
              "lat" : VALUE_DICT['lat'],
              "lon": VALUE_DICT['lon'],
              "alt": VALUE_DICT['alt'],
              "speed": VALUE_DICT['speed'],
              "num_sats": VALUE_DICT['sats'],
              "fix": VALUE_DICT['fix'],
              "quality": VALUE_DICT['qual'],
              "pdop": VALUE_DICT['pdop'],
              "hdop": VALUE_DICT['hdop'],
              "vdop": VALUE_DICT['vdop']

          }
      }
    ]

    client.write_points(particle_data, database=INFLUXDB_DB) #THESE ARE OUTDATED AND NEED TO BE UPDATED!
    client.write_points(gps_data, database=INFLUXDB_DB) #THESE ARE OUTDATED AND NEED TO BE UPDATED!

def create_database_table(conn):
  """Creates a table in the database if it doesn't exist."""
  cursor = conn.cursor()
  cursor.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
                  timestamp TEXT,
                  lat REAL,
                  lon REAL,
                  alt REAL,
                  sats TEXT,
                  qual TEXT,
                  fix TEXT,
                  pdop TEXT,
                  vdop TEXT,
                  hdop TEXT,
                  pm_1_0 REAL,
                  pm2_5 REAL,
                  pm10 REAL,
                  date TEXT
                  )''')
  conn.commit()

def write_to_database(conn, data):
  """Writes data to the sensor_data table in the database."""
  cursor = conn.cursor()
  cursor.execute("INSERT INTO sensor_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", data)
  conn.commit()

def read_gps():
  """Reads data from the GPS sensor and returns a list."""
  gps.update()
  # x = list(gps.data.values())
  y = [*gps.data.values()]
  return itemgetter(0,1,2,3,7,8,10,11,12,13)(y)

def read_gps_influx():
  """Reads data from the GPS sensor and returns a list."""
  gps_dict = {}
  gps.update()
  gps_dict.update({"lat": gps.data['latitude'], 
                   "lon": gps.data['longitude'], 
                   "alt": gps.data['altitude'],
                   "speed": gps.data['speed_over_ground'],
                   "num_sats": gps.data['num_sats'],
                   "quality": gps.data['gps_qual'],
                   "pdop": gps.data['pdop'],
                   "hdop": gps.data['hdop'],
                   "vdop": gps.data['vdop'],
                   "timestamp": gps.data['timestamp'],
                   "fix": gps.data['mode_fix_type']})
  return gps_dict

def read_pms5003():
  """Reads data from the PMS5003 sensor and returns a list."""
  pmdata = {}
  result = pms5003.read()
  pmdata.update({"pm10": result.pm10_std})
  pmdata.update({"pm25": result.pm25_std})
  pmdata.update({"pm1": result.pm100_std})
  return pmdata

def main():
  """Continuously reads sensor data and writes to the database."""
  conn = sqlite3.connect(database_file)
  create_database_table(conn)  # Create table if it doesn't exist

  while True:
    gps_data = list(read_gps())
    gps_data_influx = read_gps_influx()
    pms_data = read_pms5003()
    influx_data = {}
    influx_data.update(gps_data_influx, pms_data)
    data = [str(gps_data[0])] + gps_data[1:10] + pms_data[0:3] + [tday]
    print(data, flush=True)
    write_to_database(conn, data)
    write_influxdb(influx_data)
    time.sleep(10)

## Other setup
##Influx DB setup
client = InfluxDBClient(host=HOST, port=PORT, username=USER, password=PASSWORD) #Initial influxdb client
dbs = client.get_list_database()
new_db = search(dbs, INFLUXDB_DB)
if not new_db:
    client.create_database(INFLUXDB_DB)

if __name__ == "__main__":
  main()