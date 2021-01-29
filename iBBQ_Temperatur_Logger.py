#!/usr/bin/env python3
from bluepy import btle
from pprint import pprint
from bluepy.btle import BTLEException
import struct
import time
import sys

FILE_PATH = "temp_log.txt"
DEVICE_MAC = "F8:36:9B:4A:2F:7D"
SET_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
AUTH_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"
RT_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"
SETDATA_UUID = "0000fff5-0000-1000-8000-00805f9b34fb"
HISTORY_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"
NOTIFY = b"\x01\x00"
AUTH_DATA = bytearray(b'\x21\x07\x06\x05\x04\x03\x02\x01\xb8\x22\0\0\0\0\0')
RT_ENABLE = bytearray(b'\x0b\x01\0\0\0\0')
BATTERY_ENABLE = bytearray(b'\x08\x24\0\0\0\0')

output = open(FILE_PATH, "w")

class IbbqDevice():
    # Parameters
    #   device = pointer to bluepy device
    #   characteristics = dictionary of characteristics
    #   connected = boolean indicating connection status
    #   probe1/2 = temperature of corresponding probe
    #   batterylevel = current battery level
    def __init__(self,device,char_dict):
        self.device = device
        self.characteristics = char_dict
        self.connected = True 

    def setTemperature(self,probe1,probe2):
        self.probe1 = probe1
        self.probe2 = probe2

    def setBatteryLevel(self,pct):
        self.batterylevel = pct

    def disconnect(self):
        self.connected = False
        self.device.disconnect()

    def isConnected(self):
        return self.connected

    def getTemperature(self):
        return (self.probe1,self.probe2)

    def getBatteryLevel(self):
        return self.batterylevel

    def getCharacteristics(self):
        return self.characteristics

    def getDevice(self):
        return self.device

class MyDelegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)
        # ... initialise here
    def handleNotification(self, cHandle, data):
        result = list()
        batMin = 0.9
        batMax = 1.5
        if cHandle == 37:
            if data[0] == 0x24:
                currentV = struct.unpack("<H", data[1:3])
                maxV = struct.unpack("<H", data[3:5])
                batteryPct = int(100 *((batMax * currentV[0] / maxV[0] - batMin) / (batMax - batMin)))
                push_battery(batteryPct)
        else:
            while len(data) > 0:
                v, data = data[0:2], data[2:]
                upacked_data = struct.unpack("<H",v)
                raw_data = upacked_data[0] / 10
                result.append(raw_data)
            probe_one_in_celcius = result[0]
            output_text = str(time.ctime()) 
            print(output_text + " Temperatur 1 [°C]: " + str(probe_one_in_celcius))
            output.write(output_text + " Temperatur 1 [°C]: " + str(probe_one_in_celcius) + "\n")
            output.flush()            
def connect():
    for i in range(0,5):
        try:
            ibbq_device = ''
            dev = btle.Peripheral(DEVICE_MAC)
            dev_chars = dict()
            print("Connected to " + str(dev.addr))
            #
            dev_chars["auth"] = dev.getCharacteristics(uuid=AUTH_UUID)[0] # fff2 authentication characteristic
            dev_chars["rt"] = dev.getCharacteristics(uuid=RT_UUID)[0]
            dev_chars["set"] = dev.getCharacteristics(uuid=SET_UUID)[0]
            dev_chars["setD"] = dev.getCharacteristics(uuid=SETDATA_UUID)[0]
            dev_chars["histD"] = dev.getCharacteristics(uuid=HISTORY_UUID)[0]
            ibbq_device = IbbqDevice(dev,dev_chars)
            #
            dev_chars["auth"].write(AUTH_DATA,withResponse=True)
            dev.writeCharacteristic(dev_chars["rt"].getHandle() + 1,NOTIFY)
            dev.writeCharacteristic(dev_chars["set"].getHandle() + 1,NOTIFY)
            dev_chars["setD"].write(RT_ENABLE)
            print("Authenticated successfully!")
        except BTLEException:
            print("Bluepy exception. Retrying connection. Attempt " + str(i) + " of 5")
            continue
        except BrokenPipeError as e:
            print("IO exception. Retrying connection. Attempt " + str(i) + " of 5")
            continue
        except Exception as e:
            print(str(type(e)) + " exception. Retrying connection. Attempt " + str(i) + " of 5")
            continue
        break
    else:
        print("All connection attempts failed.")
        if ibbq_device:
            ibbq_device.disconnect()
    return ibbq_device

def pollData(device_object,ztime):
    dev = device_object.getDevice()
    dev.setDelegate(MyDelegate())
    char = device_object.getCharacteristics()
    counter = 0
    for i in range(0,999999909999):
        try:
            while True:
                if dev.waitForNotifications(1):
                    counter+=1
                    if counter % 50 == 0:
                        char["setD"].write(BATTERY_ENABLE)
                    if counter % 10 == 0:
                        push_time(time.perf_counter()-ztime)
                    continue
        except BTLEException:
            print("Retrying data transfer. Attempt " + str(i) + " of 999999999999")
            continue
        except AttributeError:
            print("Retrying data transfer. Attempt " + str(i) + " of 999999999999")
            continue
        except Exception as e:
            print(str(type(e)) + "Retrying data transfer. Attempt " + str(i) + " of 5") 
            continue
    else:
        print("Data transfer failure.")
        dev.disconnect()

while True:
    time_b = time.perf_counter()
    print("Connecting...")
    my_device = connect()
    if my_device.isConnected() != True:
        continue
    print("Polling data...")
    pollData(my_device,time_b)