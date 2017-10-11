# This file is part of Faros Streamer.
#
# Copyright 2015
# Andreas Henelius <andreas.henelius@ttl.fi>,
# Finnish Institute of Occupational Health
#
# This code is released under the MIT License
# http://opensource.org/licenses/mit-license.php
#
# Please see the file LICENSE for details.

from .libfaros import *
import hashlib
from pylsl import StreamInfo, StreamOutlet
import threading
import time
import crc16
import sys

def read_device_list(f):
    """ Read a device from a previous bluetooth scan. """
    device_list = {}
    data = open(f).readlines()

    del(data[0:2])
    del(data[-1])

    for line in data:
        line = line.split("\t")
        device_list[line[0]] = line[1].strip()

    print("-" * 35)
    print("Using the following device list:")
    print("-" * 35)
    print_devices(device_list)
    print("-" * 35)
    print("")
    return(device_list)


def blink_device(socket):
    """ Blink the LEDs of a Faros device. """
    command = "wbaled"
    send_command(socket, command)

    
def configure_device(socket, settings):
    """ Configure a Faros device by sending all settings as one string. """
    ## example : settings = '32100t00'
    command = 'wbasds' + settings
    res = send_command(socket, command, r_length = 7)
    if res == 'wbaack':
        print("Settings successfully stored.")
    else:
        print("Error! Settings not stored.")
    
def print_error(msg):
    """ Print an error message. """
    print("Error!")
    print(msg)

    
def create_lsl_outlet(stream_name, stream_type, channel_count, sampling_rate, channel_format = 'int16'):
    """ Create an LSL outlet. """
    stream_id = hashlib.md5(stream_name.encode("ascii")).hexdigest()[1:10]
    info      = StreamInfo(name           = stream_name,
                           type           = stream_type,
                           channel_count  = channel_count,
                           nominal_srate  = sampling_rate,
                           channel_format = channel_format,
                           source_id      = stream_id)
    return StreamOutlet(info, max_buffered = 1)


class StreamerThread(threading.Thread):
    """ Read data from a Faros device and stream the data using
        the Lab Streaming Layer (LSL).
    """
    def __init__(self, stream_data,
                 faros_socket,
                 packet_size,

                 p_header,
                 p_ecg,
                 p_acc,
                 p_marker,
                 p_rr,
                 p_temp,
                 
                 outlet_ecg,
                 outlet_acc,
                 outlet_marker,
                 outlet_rr,
                 outlet_temp):
        
        threading.Thread.__init__(self)
        self.stream_data  = stream_data
        self.faros_socket = faros_socket
        self.packet_size  = packet_size

        self.p_header     = p_header
        self.p_ecg        = p_ecg
        self.p_acc        = p_acc
        self.p_marker     = p_marker
        self.p_rr         = p_rr
        self.p_temp       = p_temp

        self.outlet_ecg    = outlet_ecg
        self.outlet_acc    = outlet_acc
        self.outlet_marker = outlet_marker
        self.outlet_rr     = outlet_rr
        self.outlet_temp   = outlet_temp

    def run(self):
        self.stream_data = True

        ps        = self.packet_size['ps']
        read_size = 300
        np        = 0
        data      = b''

        command = "wbaoms"
        res     = send_command(self.faros_socket, command, 7)

        command = "wbaom7"
        res     = send_command(self.faros_socket, command, 7)

        p_crc = Struct('crc' /  Array(1, Int16sl))

        self.faros_socket.setblocking(True)

        while (self.stream_data):
            data += self.faros_socket.recv(read_size)
            
            if len(data) >= ps:

                packet    = data[0:ps]
                data      = data[ps:]
                signature = packet[0:3]
                
                try:
                    crc_1     = p_crc.parse(packet[-2:])['crc'][0]
                    crc_2     = crc16.crc16xmodem(packet[:-2])
                except TypeError:
                    crc_1 = 0
                    crc_2 = 1

                if (signature == b'MEP') & (crc_1 == crc_2):

                    unpack_data(packet        = packet,
                                packet_size   = self.packet_size,

                                p_header      = self.p_header,
                                p_ecg         = self.p_ecg,
                                p_acc         = self.p_acc,
                                p_marker      = self.p_marker,
                                p_rr          = self.p_rr,
                                p_temp        = self.p_temp,

                                outlet_ecg    = self.outlet_ecg,
                                outlet_acc    = self.outlet_acc,
                                outlet_marker = self.outlet_marker,
                                outlet_rr     = self.outlet_rr,
                                outlet_temp   = self.outlet_temp)
                    # np += 1
                else:
                    while True:
                        tmp = self.faros_socket.recv(read_size)
                        if tmp[0:3] == b'MEP':
                            data = tmp
                            break


    def stop(self):
        self.stream_data = False
        command = "wbaoms"
        send_command(self.faros_socket, command, 0)
