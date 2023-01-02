#!/usr/bin/env python
import time
import serial
import argparse

# parser = argparse.ArgumentParser()
# parser.add_argument('--action', action='store', type=str, required=True)
# args = parser.parse_args()

ser = serial.Serial(
        port='/dev/ttyS0',
        baudrate = 9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=20
)

action = "read"

while action == "read":
    
    input = input("What would you like to do? type 'read' to get data and 'stop' to stop and 'restart' to restart the program")

    if input == "read":
            message=bytes("read\n", "UTF-8")
            ser.write(message)
            print(ser.read_until())
            action = "read"

    elif input == "restart":
            message=bytes("read\n", "UTF-8")
            ser.write(message)
            print(ser.read_until())
            action = "read"

    elif input == "stop":
            message=bytes("stop\n", "UTF-8")
            ser.write(message)
            action = "stop"


