#!/usr/bin/python3
# 2024-03-19
# Script to read GPS and PM sensor and write to SQLite db
# the PMS5003 is running off of version 0.5 of the library, not the latest version.

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--no-pijuice', dest='pijuice', action='store_false')
parser.add_argument('--pijuice', dest='pijuice', action='store_true')
parser.add_argument('--no-neopixels', dest='neopixels', action='store_false')
parser.add_argument('--neopixels', dest='neopixels', action='store_true')
parser.add_argument('--no-influxdb', dest='influxdb', action='store_false')
parser.add_argument('--influxdb', dest='influxdb', action='store_true')
args = parser.parse_args()

USING_INFLUXDB = args.influxdb
USING_PIJUICE = args.pijuice
USING_NEOPIXELS = args.neopixels

print(USING_INFLUXDB, USING_PIJUICE, USING_NEOPIXELS, flush=True)

import sqlite3
import time
from pa1010d import PA1010D
import plantower #https://pypi.org/project/plantower/
from datetime import datetime
if USING_NEOPIXELS:
  import neopixel
  import board
from influxdb import InfluxDBClient #https://influxdb-python.readthedocs.io/en/latest/include-readme.html#installation-1
import socket
if USING_PIJUICE: #sudo apt-get install pijuice-base  
  from pijuice import PiJuice #More info here: https://github.com/PiSupply/PiJuice/blob/master/Software/README.md
import psutil
import nmcli #https://pypi.org/project/nmcli/

#setup neopixels
if USING_NEOPIXELS:
  NUM_PIXELS = 8
  ORDER = neopixel.GRB
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
if USING_PIJUICE:
  BATTERY_DEV = "pijuice"
else:
  BATTERY_DEV = "no_pijuice"
PARTICIPANT_ID = "PARTICIPANT_1" #Participant ID for influxdb
WRITE_TIMEOUT = 10 #Timeout for writing to influxdb

# Define sensors and neopixels
gps = PA1010D()
pms5003 = plantower.Plantower(port='/dev/serial0')
pms5003.mode_change(plantower.PMS_PASSIVE_MODE) #Change to passive mode
if USING_NEOPIXELS:
  pixels = neopixel.NeoPixel(
      PIXEL_PIN, NUM_PIXELS, brightness=0.01, auto_write=False, pixel_order=ORDER
  )
if USING_PIJUICE:
  pijuice = PiJuice(1, 0x14) # Instantiate PiJuice interface object

tday = datetime.today().strftime('%Y-%m-%d')
print(tday)

# Define database and json filenames (modify as needed)
database_file = "/home/pi/aq-sensor/sensor_data_v4.db"

# Define LED colours
RED = [200, 0, 0]
GREEN = [0, 200, 0]
BLUE = [0, 0, 200]
OFF = [0, 0, 0]
YELLOW = [200, 200, 0]

##Set up influxdb client. Note this is non-blocking.
if USING_INFLUXDB:
  client_local = InfluxDBClient(
    host=HOST_LOCAL, port=PORT, 
    username=USER, 
    password=PASSWORD,
    timeout=WRITE_TIMEOUT) #Local
  client_remote = InfluxDBClient(
    host=HOST_REMOTE, 
    port=PORT, 
    username=USER, 
    password=PASSWORD,
    timeout=WRITE_TIMEOUT) #Remote

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

    system_data = [
    {
      "measurement": "system_info",
          "tags": {
              "participant_id": PARTICIPANT_ID,
          },
          "time": timestamp,
          "fields": {
              "cpu_usage" : VALUE_DICT['cpu_usage'],
              "ram_usage": VALUE_DICT['ram_usage'],
              "disk_usage": VALUE_DICT['disk_usage'],
              "wifi_ssid": VALUE_DICT['wifi_ssid'],
              "wifi_signal": VALUE_DICT['wifi_signal'],
              "ip_address": VALUE_DICT['ip_address']
          }
      }
    ]

    influx_json = particle_data + gps_data + battery_data + system_data
    sql_list = [
                timestamp,
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
                VALUE_DICT['battery_status'],
                VALUE_DICT['cpu_usage'],
                VALUE_DICT['ram_usage'],
                VALUE_DICT['disk_usage'],
                VALUE_DICT['wifi_ssid'],
                VALUE_DICT['wifi_signal'],
                VALUE_DICT['ip_address']
                ]
    
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
  
# Get current wifi network
def get_wifi_details():
  if test_connection():
    if USING_NEOPIXELS:
      pixels[1] = GREEN
    try:
      for i in range(0, len(nmcli.device.wifi())-1):
        if nmcli.device.wifi()[i].in_use == True:
          ssid = nmcli.device.wifi()[i].ssid
          signal = nmcli.device.wifi()[i].signal
          ip_address = nmcli.device.show("wlan0")["IP4.ADDRESS[1]"]
    except Exception as e:
      print(f"Error getting wifi details: {e}", flush=True)
      ssid = "Not connected to wifi"
      ip_address = "Not connected to wifi"
      signal = 0
      if USING_NEOPIXELS:
        pixels[1] = RED
  else:
    ssid = "Not connected to wifi"
    ip_address = "Not connected to wifi"
    signal = 0
    print(f"Error getting wifi details: {e}", flush=True)
    if USING_NEOPIXELS:
      pixels[1] = RED
  try:
    return {"ssid": ssid, "signal": signal, "ip_address": ip_address}
  except Exception as e:
    print(f"Error getting wifi details: {e}", flush=True)
    return {"ssid": "Not connected to wifi", "signal": 0, "ip_address": "Not connected to wifi"}

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
                  battery_status TEXT,
                  cpu_usage REAL,
                  ram_usage REAL,
                  disk_usage REAL,
                  wifi_ssid TEXT,
                  wifi_signal REAL,
                  ip_address TEXT
                  )''')
  conn.commit()

def write_to_database(conn, data):
  """Writes data to the sensor_data table in the database."""
  cursor = conn.cursor()
  cursor.execute("INSERT INTO sensor_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", data)
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
  if USING_NEOPIXELS:
    if result.pm25_std < 10:
      pixels[2] = GREEN
    elif 10 <= result.pm25_std < 20:
      pixels[2] = BLUE
    else:
      pixels[2] = RED
  return pmdata

def read_battery():
  """Reads data from the PiJuice battery sensor (if using pijuice, empty data otherwise) and returns a dictionary."""
  battery_data = {}
  if USING_PIJUICE:
    battery_data.update({"battery_voltage": pijuice.status.GetBatteryVoltage()["data"]})
    battery_data.update({"battery_current": pijuice.status.GetBatteryCurrent()["data"]})
    battery_data.update({"battery_charge": pijuice.status.GetChargeLevel()["data"]})
    charge = pijuice.status.GetChargeLevel()["data"]
    if USING_NEOPIXELS:
      if charge < 25:
        pixels[7] = RED
        pixels[6] = OFF
        pixels[5] = OFF
        pixels[4] = OFF
      elif 25 <= charge < 50:
        pixels[7] = BLUE
        pixels[6] = BLUE
        pixels[5] = OFF
        pixels[4] = OFF
      elif 50 <= charge < 75:
        pixels[7] = YELLOW
        pixels[6] = YELLOW
        pixels[5] = YELLOW
        pixels[4] = OFF
      elif 75 <= charge:
        pixels[7] = GREEN
        pixels[6] = GREEN
        pixels[5] = GREEN
        pixels[4] = GREEN
      else:
        pixels[3] = GREEN
    if pijuice.status.GetStatus()["data"]["battery"] == "NORMAL":
      battery_data.update({"battery_status": "On battery power"})
    elif pijuice.status.GetStatus()["data"]["battery"] == "CHARGING_FROM_IN":
      if pijuice.status.GetChargeLevel()["data"] >= 95:
        battery_data.update({"battery_status": "Fully Charged"})
      else:
        battery_data.update({"battery_status": "Charging"})
    else:
      battery_data.update({"battery_status": "Error"})
    return battery_data
  else:
    return {"battery_voltage": 0, "battery_current": 0, "battery_charge": 0, "battery_status": "No pijuice"}

def read_system_info():
  """Reads system information and returns a dictionary."""
  system_data = {}
  system_data.update({"cpu_usage": psutil.cpu_percent()})
  system_data.update({"ram_usage": psutil.virtual_memory().percent})
  system_data.update({"disk_usage": psutil.disk_usage('/').percent})
  system_data.update({"wifi_ssid": get_wifi_details()["ssid"]})
  system_data.update({"wifi_signal": get_wifi_details()["signal"]})
  system_data.update({"ip_address": get_wifi_details()["ip_address"]})
  return system_data

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
        if USING_PIJUICE:
          pijuice.status.SetLedState('D2', RED)
        if USING_NEOPIXELS:
          pixels[0] = RED
    elif  gps_data["sats"] > 0:
        if USING_PIJUICE:
          pijuice.status.SetLedState('D2', GREEN)
        if USING_NEOPIXELS:
          pixels[0] = GREEN
    else:
        if USING_PIJUICE:
          pijuice.status.SetLedState('D2', RED)
        if USING_NEOPIXELS:
          pixels[0] = RED
    pms_data = read_pms5003()
    battery_data = read_battery()
    system_data = read_system_info()
    influx_data = {}
    influx_data.update(gps_data)
    influx_data.update(pms_data)
    influx_data.update(battery_data)
    influx_data.update(system_data)
    remote_data_to_write, local_data_to_write = influxdb_write_constructor(influx_data, time.time_ns())
    print(local_data_to_write, flush=True)
    write_to_database(conn, local_data_to_write) #Write to local sql
    print("Written to local file", flush=True)

    if USING_INFLUXDB:
      LOCAL = test_connection(host=HOST_LOCAL, port=PORT, timeout=2)
      REMOTE = test_connection(host=HOST_REMOTE, port=PORT, timeout=2)
      if REMOTE: # Check if can connect to remote
        try:
          client_remote.write_points(remote_data_to_write, database=INFLUXDB_DB)
          print("Written to remote influxdb", flush=True)
        except Exception as e:
          print(f"Error writing to remote influxdb: {e}", flush=True)

      if LOCAL: # Or check local
        try:
          client_local.write_points(remote_data_to_write, database=INFLUXDB_DB)
          print("Written to local influxdb", flush=True)
        except Exception as e:
          print(f"Error writing to local influxdb: {e}", flush=True)

      if not LOCAL and not REMOTE:
        print("Cannot connect to influxdb", flush=True)#else write to local json

    elif not USING_INFLUXDB: #Write to local file when not using influxdb
      print("Not using influxdb", flush=True)
    
    pixels.show()
    
    time.sleep(10)

#Main
if __name__ == "__main__":
  main()
