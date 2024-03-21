#!/usr/bin/env python
import sys
sys.path.append('/home/pi/bike-sensor/e-Paper/RaspberryPi_JetsonNano/python/lib')
import socket
#from waveshare_epd import epd2in9_V2
from waveshare_epd import epd2in9_V2 
from PIL import Image,ImageDraw,ImageFont
import time

#Set up the display and fonts and stuff

epd = epd2in9_V2.EPD()
epd.init()
epd.Clear(0xFF)

#fonts
font_size = 90
font = ImageFont.truetype("/usr/share/fonts/garamond_roman.ttf", font_size)

font_size_small = 30
font_small = ImageFont.truetype("/usr/share/fonts/garamond_roman.ttf", font_size_small)


message_image = Image.new('1', (epd.height, epd.width), 255)
message_draw = ImageDraw.Draw(message_image)
epd.display_Base(epd.getbuffer(message_image))

ip_addr = [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]

message = f"Ip Address:\n{ip_addr}"

message_draw.rectangle((10, 5, 296, 128), fill = 255)
message_draw.text((10, 5), message, font = font_small, fill = 0)


while True:
    epd.display_Partial(epd.getbuffer(message_image))
    time.sleep(60)
    epd.init()
    epd.Clear(0xFF)
    epd.init()
    epd.Clear(0xFF)








