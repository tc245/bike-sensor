# bike-sensor
## Pi-based personal air quality monitor
This repository contains all files required to build the pi-based personal and portable air quality monitor including STL files for the 3d printed enclosure, all python code and build instructions.

To do:

- [ ] Sensor reader that saves periodically to a json file on the device
- [ ] Program that writes that file to influxdb
- [ ] Check when connected to internet
- [ ] Turn wifi on when at home and off when out (based on GPS coordinates or even when wifi is in or out of range e.g. using [this]([url](https://pypi.org/project/wifi/))!).
- [ ] Figure out onboarding (captive portal to input wifi details and enter home gps coordinates).
- [ ] Set up influxdb and grafana instances
- [ ] Set up neopixel indicator
- [ ] Set up pijuice
- [ ] Investigate threading for all the tasks (wifi state checker, gps home checker, sensor reader etc). 
