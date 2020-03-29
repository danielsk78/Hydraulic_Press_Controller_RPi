#!/usr/bin/env python3

import RPi.GPIO as GPIO  # import GPIO
from hx711 import HX711  # import the class HX711
GPIO.setmode(GPIO.BCM) # set GPIO pin mode to BCM numbering

try:
	hx = HX711(dout_pin=21, pd_sck_pin=20)  # create an object
	print(hx.get_raw_data(15))  # get raw data reading from hx711
	GPIO.cleanup()
except:
	GPIO.cleanup()
	print("Not working")