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
import http.client as httplib
import socket
from pijuice import PiJuice # Import pijuice module
import json

#setup neopixels
NUM_PIXELS = 8
ORDER = neopixel.RGB
PIXEL_PIN = board.D18

#THESE CAN BE CHANGED!
#HOST = "192.168.0.127" # IP address of home influx server (This is for a test server in azure for the timebeing)
HOST_REMOTE = "20.77.64.8" #Ip address of azure server
HOST_LOCAL = "192.168.0.127" #Ip of local server
PORT = 8086 # Port for influx server (default)
INFLUXDB_DB = "personal-aq-sensor-v2" # Influx database name
USER = "admin" # the userNAME/password created for accessing influxdb
PASSWORD = "admin"
PARTICLE_DEV = "rpi-pms5003" #Device tag for influxdb
GPS_DEV =  "rpi-pa1010d" #Device tag for influxdb
BATTERY_DEV = "pijuice"
PARTICIPANT_ID = "PARTICIPANT_1" #Participant ID for influxdb
USING_INFLUXDB = True #Set to True if using influxdb

# Define sensors and neopixels
gps = PA1010D()
pms5003 = plantower.Plantower(port='/dev/serial0')
pms5003.mode_change(plantower.PMS_PASSIVE_MODE) #Change to passive mode
pixels = neopixel.NeoPixel(
    PIXEL_PIN, NUM_PIXELS, brightness=0.2, auto_write=False, pixel_order=ORDER
)
pijuice = PiJuice(1, 0x14) # Instantiate PiJuice interface object

tday = datetime.today().strftime('%Y-%m-%d')
print(tday)

# Define database and json filenames (modify as needed)
database_file = "/home/pi/aq-sensor/sensor_data_v2.db"

# Define LED colours
RED = [200, 0, 0]
GREEN = [0, 200, 0]

##Set up influxdb client. Note this is non-blocking.
if USING_INFLUXDB:
  client_local = InfluxDBClient(
    host=HOST_LOCAL, port=PORT, 
    username=USER, 
    password=PASSWORD) #Local
  client_remote = InfluxDBClient(
    host=HOST_REMOTE, 
    port=PORT, 
    username=USER, 
    password=PASSWORD) #Remote

#Placeholder for various influxdb related functions
#String search function
def search(values, searchFor):
    for k in values:
        for v in k:
            if searchFor in v:
                return True
    return False

def influxdb_write_constructor(VALUE_DICT, timestamp):
    particle_data = [
    {
      "measurement": PARTICLE_DEV,
          "tags": {
              "participant_id": PARTICIPANT_ID,
          },
          "time": timestamp,
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
          "time": timestamp,
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
    battery_data = [
    {
      "measurement": BATTERY_DEV,
          "tags": {
              "participant_id": PARTICIPANT_ID,
          },
          "time": timestamp,
          "fields": {
              "battery_voltage" : VALUE_DICT['battery_voltage'],
              "battery_current": VALUE_DICT['battery_current'],
              "battery_charge": VALUE_DICT['battery_charge'],
              "battery_status": VALUE_DICT['battery_status']
          }
      }
    ]

    influx_json = particle_data + gps_data + battery_data
    sql_list = [timestamp,
                VALUE_DICT['lat'], 
                VALUE_DICT['lon'], 
                VALUE_DICT['alt'], 
                VALUE_DICT['speed'], 
                VALUE_DICT['sats'], 
                VALUE_DICT['fix'], 
                VALUE_DICT['qual'], 
                VALUE_DICT['pdop'], 
                VALUE_DICT['vdop'], 
                VALUE_DICT['hdop'], 
                VALUE_DICT['pm1'], 
                VALUE_DICT['pm25'],
                VALUE_DICT['pm10'],
                VALUE_DICT['battery_voltage'],
                VALUE_DICT['battery_current'],
                VALUE_DICT['battery_charge'],
                VALUE_DICT['battery_status']]
    
    return influx_json, sql_list

# function to check internet connectivity
def test_connection(host="8.8.8.8", port=53, timeout=3):
  try:
    socket.setdefaulttimeout(timeout)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
    return True
  except Exception as ex:
    #print(f"Internet Off. Error: {ex}", flush=True)
    return False

def create_database_table(conn):
  """Creates a table in the database if it doesn't exist."""
  cursor = conn.cursor()
  cursor.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
                  timestamp TEXT,
                  lat REAL,
                  lon REAL,
                  alt REAL,
                  speed REAL,
                  num_sats TEXT,
                  fix TEXT,
                  quality TEXT,
                  pdop TEXT,
                  vdop TEXT,
                  hdop TEXT,
                  pm_1_0 REAL,
                  pm2_5 REAL,
                  pm10 REAL,
                  battery_voltage REAL,
                  battery_current REAL,
                  battery_charge REAL,
                  battery_status TEXT
                  )''')
  conn.commit()

def write_to_database(conn, data):
  """Writes data to the sensor_data table in the database."""
  cursor = conn.cursor()
  cursor.execute("INSERT INTO sensor_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", data)
  conn.commit()

def read_gps():
  """Reads data from the GPS sensor and returns a list."""
  gps_dict = {}
  gps.update()
  gps_dict.update({"lat": float(gps.data['latitude']), 
                   "lon": float(gps.data['longitude']), 
                   "alt": gps.data['altitude'],
                   "speed": gps.data['speed_over_ground'],
                   "sats": int(gps.data['num_sats']),
                   "qual": gps.data['gps_qual'],
                   "pdop": gps.data['pdop'],
                   "hdop": gps.data['hdop'],
                   "vdop": gps.data['vdop'],
                   #"timestamp": gps.data['timestamp'],
                   "fix": gps.data['mode_fix_type'],
                   "timestamp": time.ctime()})
  return gps_dict

def read_pms5003():
  """Reads data from the PMS5003 sensor and returns a list."""
  pmdata = {}
  result = pms5003.read_in_passive()
  pmdata.update({"pm10": result.pm100_std})
  pmdata.update({"pm25": result.pm25_std})
  pmdata.update({"pm1": result.pm10_std})
  pmdata.update({"timestamp": time.ctime()})
  return pmdata

def read_battery():
  """Reads data from the PiJuice battery sensor and returns a dictionary."""
  battery_data = {}
  battery_data.update({"battery_voltage": pijuice.status.GetBatteryVoltage()["data"]})
  battery_data.update({"battery_current": pijuice.status.GetBatteryCurrent()["data"]})
  battery_data.update({"battery_charge": pijuice.status.GetChargeLevel()["data"]})
  if pijuice.status.GetStatus()["data"]["battery"] == "NORMAL":
    battery_data.update({"battery_status": "On battery power"})
  elif pijuice.status.GetStatus()["data"]["battery"] == "CHARGING_FROM_IN":
    battery_data.update({"battery_status": "Charging"})
  else:
    battery_data.update({"battery_status": "Error"})
  return battery_data

def main():
  """Continuously reads sensor data and writes to the database."""
  conn = sqlite3.connect(database_file)
  create_database_table(conn)  # Create table if it doesn't exist
  #Influxdb setup
  if USING_INFLUXDB:
    if test_connection(host=HOST_REMOTE, port=PORT, timeout=2):
      if not search(client_remote.get_list_database(), INFLUXDB_DB):
        client_remote.create_database(INFLUXDB_DB) #Check if database exists, if not create it
    else:
      print("Remote influxdb not available", flush=True)

    if test_connection(host=HOST_LOCAL, port=PORT, timeout=2):
      if not search(client_local.get_list_database(), INFLUXDB_DB):
        client_local.create_database(INFLUXDB_DB) #Check if database exists, if not create it
    else:
      print("Local influxdb not available", flush=True)

  while True:
    gps_data = read_gps()
    if  gps_data["sats"] == 0:
        pijuice.status.SetLedState('D2', RED)
    elif  gps_data["sats"] > 0:
        pijuice.status.SetLedState('D2', GREEN)
    else:
        pijuice.status.SetLedState('D2', RED)
    pms_data = read_pms5003()
    battery_data = read_battery()
    influx_data = {}
    influx_data.update(gps_data)
    influx_data.update(pms_data)
    influx_data.update(battery_data)
    remote_data_to_write, local_data_to_write = influxdb_write_constructor(influx_data, time.time_ns())
    print(local_data_to_write, flush=True)
    write_to_database(conn, local_data_to_write) #Write to local sql
    print("Written to local file", flush=True)

    if USING_INFLUXDB:
      LOCAL = test_connection(host=HOST_LOCAL, port=PORT, timeout=2)
      REMOTE = test_connection(host=HOST_REMOTE, port=PORT, timeout=2)
      if REMOTE: # Check if can connect to remote
        client_remote.write_points(remote_data_to_write, database=INFLUXDB_DB)
        print("Written to remote influxdb", flush=True)

      if LOCAL: # Or check local
        client_local.write_points(remote_data_to_write, database=INFLUXDB_DB)
        print("Written to local influxdb", flush=True)

      if not LOCAL and not REMOTE:
        print("Cannot connect to influxdb", flush=True)#else write to local json

    elif not USING_INFLUXDB: #Write to local file when not using influxdb
      print("Not using influxdb", flush=True)
 
    time.sleep(10)

#Main
if __name__ == "__main__":
  main()
