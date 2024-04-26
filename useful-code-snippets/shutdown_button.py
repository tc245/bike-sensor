#!/usr/bin/env python

import RPi.GPIO as GPIO
import subprocess
import time


GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Waiting for button press", flush=True)
GPIO.wait_for_edge(26, GPIO.FALLING)
print("Button pressed", flush=True)
time.sleep(1)

subprocess.call(['shutdown', '-h', 'now'], shell=False)
