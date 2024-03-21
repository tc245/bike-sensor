#!/usr/bin/python
#!/usr/bin/env python
import time
import serial
import concurrent.futures
import logging
import queue
import threading
import json
import sys
sys.path.append('/home/pi/bike-sensor/e-Paper/RaspberryPi_JetsonNano/python/lib')
from waveshare_epd import epd2in9_V2
from PIL import Image,ImageDraw,ImageFont
import traceback
from pijuice import PiJuice # Import pijuice module


logging.basicConfig(level=logging.DEBUG)

#Set up the display and fonts and stuff

epd = epd2in9_V2.EPD()
pijuice = PiJuice(1, 0x14)

logging.info("init and Clear")
epd.init()
epd.Clear(0xFF)

#fonts
font_size = 45
font = ImageFont.truetype("/usr/share/fonts/garamond_roman.ttf", font_size)

font_size_small = 15
font_small = ImageFont.truetype("/usr/share/fonts/garamond_roman.ttf", font_size_small)

##variables
INTERVAL = 0.5

#Define thread functions
def serial_reader(queue, event, serial_object):
    while not event.is_set():
        serial_object.write(bytes('{"action": "read"}\n', 'UTF-8'))
        message = serial_object.read_until()
        logging.info("Producer got message: %s", message)
        queue.put(message)
        time.sleep(INTERVAL)

    logging.info("Producer received event. Exiting")

def consumer(queue, event, display_obj):
    """Pretend we're saving a number in the database."""
    while not event.is_set() or not queue.empty():
        message_image = Image.new('1', (display_obj.height, display_obj.width), 255)
        message_draw = ImageDraw.Draw(message_image)
        display_obj.display_Base(display_obj.getbuffer(message_image))
        num = 0
        while num <= 60:
            data = queue.get()
            pm10 = json.loads(data.decode('UTF-8').strip("\n"))["PM10"]
            pm25 = json.loads(data.decode('UTF-8').strip("\n"))["PM2.5"]
            co2 = json.loads(data.decode('UTF-8').strip("\n"))["CO2"]
            temp = int(json.loads(data.decode('UTF-8').strip("\n"))["Temp"])
            pressure = int(json.loads(data.decode('UTF-8').strip("\n"))["Pressure"])
            humidity = int(json.loads(data.decode('UTF-8').strip("\n"))["Humidity"])
            pm10_message = f"PM10: {pm10}mg/m\u00b3"
            pm25_message = f"PM2.5 {pm25}mg/m\u00b3"
            co2_message = f"CO2: {co2} ppm"
            temp_message = f"Temperature: {temp} C"
            pressure_message = f"Pressure: {pressure}"
            humidity_message = f"Humidity: {humidity}%"
            time_message = f"Time: {time.strftime('%H:%M')}"
            battery_message = f"Charge level: {pijuice.status.GetChargeLevel()['data']} %"
            if pijuice.status.GetStatus()['data']['battery'] == "NORMAL":
                battery_status_message = f"Status: Discharging"
            elif pijuice.status.GetStatus()['data']['battery'] == "CHARGING_FROM_IN":
                battery_status_message = f"Status: Charging"               
            message_draw.rectangle((10, 5, 296, 128), fill = 255)
            message_draw.text((10, 5), time_message, font = font_small, fill = 0)
            message_draw.text((10, 25), pm10_message, font = font_small, fill = 0)
            message_draw.text((10, 45), pm25_message, font = font_small, fill = 0)
            message_draw.text((10, 65), co2_message, font = font_small, fill = 0)
            message_draw.text((10, 85), temp_message, font = font_small, fill = 0)
            message_draw.text((10, 105), humidity_message, font = font_small, fill = 0)
            message_draw.text((148, 5), "Battery", font = font_small, fill = 0)
            message_draw.text((148, 25), battery_message, font = font_small, fill = 0)
            message_draw.text((148, 45), battery_status_message, font = font_small, fill = 0)
            newimage = message_image.crop([10, 10, 120, 50])
            message_image.paste(newimage, (10,10))  
            display_obj.display_Partial(epd.getbuffer(message_image))
            num += 1
            logging.info(f"Display iteration number {num}, queue size: {queue.qsize()}")
        display_obj.init()
        display_obj.Clear(0xFF)

    logging.info("Consumer received event. Exiting")

    logging.info("Clear...")
    epd.init()
    epd.Clear(0xFF)
    
    logging.info("Goto Sleep...")
    epd.sleep()

##Create serial object
ser = serial.Serial(
        port='/dev/ttyS0',
        baudrate = 9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=20
)

if __name__ == "__main__":

    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")

    pipeline = queue.Queue(maxsize=10)
    event = threading.Event()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(serial_reader, pipeline, event, ser)
        executor.submit(consumer, pipeline, event, epd)

        time.sleep(300)
        logging.info("Main: about to set event")
        event.set()


