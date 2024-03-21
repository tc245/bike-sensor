from waveshare_epd import epd2in9_V2

epd = epd2in9_V2.EPD()

epd.init()
epd.Clear(0xFF)
epd.sleep()