# 2024-03-19
# Script to read GPS and PM sensor and write to SQLite db
# the PMS5003 is running off of version 0.5 of the library, not the latest version.

import sqlite3
import time
from pa1010d import PA1010D
from pms5003 import PMS5003
from operator import itemgetter
from datetime import datetime

# Define sensors
gps = PA1010D()
pms5003 = PMS5003(device="/dev/ttyAMA0", baudrate=9600)

tday = datetime.today().strftime('%Y-%m-%d')
print(tday)

# Define database filename (modify as needed)
database_file = "sensor_data.db"

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
                  pm5 REAL,
                  pm10 REAL,
                  date TEXT
                  )''')
  conn.commit()

def write_to_database(conn, data):
  """Writes data to the sensor_data table in the database."""
  cursor = conn.cursor()
  cursor.execute("INSERT INTO sensor_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", data)
  conn.commit()

def read_gps():
  """Reads data from the GPS sensor and returns a list."""
  gps.update()
  # x = list(gps.data.values())
  y = [*gps.data.values()]
  return itemgetter(0,1,2,3,7,8,10,11,12,13)(y)

def read_pms5003():
  """Reads data from the PMS5003 sensor and returns a list."""
  pmdata = pms5003.read()
  return pmdata.data

def main():
  """Continuously reads sensor data and writes to the database."""
  conn = sqlite3.connect(database_file)
  create_database_table(conn)  # Create table if it doesn't exist

  while True:
    gps_data = list(read_gps())
    print(len(gps_data))
    pms_data = list(read_pms5003())
    data = [str(gps_data[0])] + gps_data[1:10] + pms_data[8:12] + [tday]
    print(data)
    write_to_database(conn, data)
    time.sleep(1)

if __name__ == "__main__":
  main()
