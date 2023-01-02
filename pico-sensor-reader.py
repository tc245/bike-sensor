import time
from breakout_bme68x import BreakoutBME68X, STATUS_HEATER_STABLE
from pimoroni_i2c import PimoroniI2C
import time
from pms5003 import PMS5003
from breakout_sgp30 import BreakoutSGP30
from machine import UART, Pin

PINS_BREAKOUT_GARDEN = {"sda": 4, "scl": 5}

i2c = PimoroniI2C(**PINS_BREAKOUT_GARDEN)

# Configure the PMS5003 for Enviro+
pms5003 = PMS5003(
    uart=machine.UART(1, tx=machine.Pin(8), rx=machine.Pin(9), baudrate=9600),
    pin_enable=machine.Pin(3),
    pin_reset=machine.Pin(2),
    mode="passive"
)

bmp = BreakoutBME68X(i2c)
# If this gives an error, try the alternative address
# bmp = BreakoutBME68X(i2c, 0x77)

sgp30 = BreakoutSGP30(i2c)
sgp30.start_measurement(False)

uart0 = UART(0, baudrate=9600, bits=8, parity=None, stop=1, timeout=300000)


while True:
    try:
        print("waiting for message...")
        message = str(uart0.readline(), 'UTF-8').strip("\n")
        print(message)

        if message == "start":
            temperature, pressure, humidity, gas, status, _, _ = bmp.read()
            data = pms5003.read()
            heater = "Stable" if status & STATUS_HEATER_STABLE else "Unstable"
            air_quality = sgp30.get_air_quality()
            eCO2 = air_quality[BreakoutSGP30.ECO2]
            TVOC = air_quality[BreakoutSGP30.TVOC]
            pm10 = data.pm_ug_per_m3(10)
            pm25 = data.pm_ug_per_m3(2.5)
            pm1 = data.pm_ug_per_m3(1)
            data = ("PM10: {}, PM2.5: {}, PM1: {}, CO2: {}, Temp: {}, Pressure: {}, Humidity: {}, Gas: {}\n".format(pm10, pm25, pm1, eCO2, temperature, (pressure/100), humidity, gas))
            print(data)
            uart0.write(data)        

        elif message == "stop":
            print("stopping...")
            pass
        
        else:
            print("no message received...")
            
    except TypeError as e:
        print(e)