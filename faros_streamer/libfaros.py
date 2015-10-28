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

import bluetooth
from construct import *
from collections import OrderedDict
import struct
import crc16
import time

# -------------------------------------------------------------------------------
# Functions for printing
# -------------------------------------------------------------------------------

def print_devices(x):
    """ Helper function for printing device list. """
    for i in x:
        print(i + "\t" + x[i])


def sync_time(s):
    print("-" * 45)
    print("Synchronising time")
    print("-" * 45)
    print_kv("Old time", get_device_time(s))
    set_device_time(s)
    print_kv("New time", get_device_time(s))
    print("-" * 45)
    print("")

def get_devices():
    """ Search for bluetooth devices and return
        a dictionary with the names and bluetooth addresses
        of the found devices.
    """
    print("Scanning for available devices.")
    nearby_devices = bluetooth.discover_devices()
    out = {}
    for bdaddr in nearby_devices:
        name = bluetooth.lookup_name(bdaddr)
        out[name] = bdaddr
    if out is not None:
        print("Found the following devices:")
        print_devices(out)
        print("")
    else:
        print("Found no devices.")
    return(out)


def print_kv(k, v, pad = 25, pc = " "):
    """ Print key-value pairs with padding. """
    print(k.ljust(pad, pc), v)

    
def print_header(x, pad = 25, pc = " "):
    """ Print table headers with padding. """
    str = ''
    for i in x:
        str += i.ljust(pad, pc)
    print(str)


def print_properties(x):
    """ Print a formatted list of the settings
        of a Faros device.
    """
    settings = unpack_settings(x['settings'])

    print("-" * 45)
    print("Device settings")
    print("-" * 45)
    print_kv("Name", x['name'])
    print_kv("Firmware version", x['firmware-version'])
    print_kv("Firmware build date", x['firmware-build'])
    print("")
    print_kv("No. of ECG channels", settings['n_ecg'])
    print_kv("ECG sampling rate", settings['ecg_fs'])
    print_kv("ECG resolution (uV)", settings['ecg_res'])
    print_kv("ECG highpass filter (Hz)", settings['ecg_hp'])
    print_kv("RR interval recording", settings['ecg_rr'])
    print("")
    print_kv("Acc sampling rate", settings['acc_fs'])
    print_kv("Acc resolution (uV)", settings['acc_res'])
    print("")
    print_kv("Temperature recording", settings['temperature'])
    print("")
    print_kv("Device time:", binary_time_to_str(x['device_time']))
    print("-" * 45)
    print("")

# -------------------------------------------------------------------------------
# Functions for getting and manipulating device properties (settings)
# -------------------------------------------------------------------------------

def get_properties(s):
    """ Get properties (name, firmware veersion and build date, and settings)
        of a Faros device connected to socket s.
    """
    properties = ['name', 'firmware-version', 'firmware-build', 'device_time', 'settings']
    out = {}
    for p in properties:
        out[p] = get_property(s, p)

    return(out)


def get_ecg_str_fs(s = None):
    """ Return ECG sampling rate given character. """
    x =  {'0' : 0,
          '1' : 1000,
          '2' : 500,
          '4' : 250,
          '8' : 125,
          't' : 100}
    if s is None:
        return x
    else:
        return x[str(s)]

    
def get_ecg_str_res(s = None):
    """ Return ECG resolution given character. """
    x = {'0' : 0.25, '1' : 1}
    if s is None:
        return x
    else:
        return x[str(s)]

def get_ecg_str_hp(s = None):
    """ Get ECG high-pass filter given character. """
    x = {'0' : 1, '1' : 10}
    if s is None:
        return x
    else:
        return x[str(s)]
    

def get_ecg_str_rr(s = None):
    """ Are RR-intervals recorded or not (given string). """
    x = {'0' : 'off', '1' : 'on'}
    if s is None:
         return x
    else:
        return x[str(s)]


def get_acc_str_fs(s = None):
    """ Get accelerometer sampling rate given character. """
    x = {'0' : 0,
         '1' : 100,
         '2' : 50,
         '3' : 40,
         '4' : 25,
         't' : 20}
    if s is None:
        return x
    else:
        return x[str(s)]

    
def get_acc_str_res(s = None):
    """ Get accelerometer resolution given character. """
    x = {'0' : 0.25, '1' : 1}
    if s is None:
        return x
    else:
        return x[str(s)]
    

def get_temp_str(s):
    """ Is temperature recorded or not (given string). """
    return {'0' : 'off', '1' : 'on'}[s]


def get_packet_size(settings):
    """ Return the packet size given the settings of the device. """
    n_ecg_s = int(settings['ecg_fs']) / 5
    n_acc_s = int(settings['acc_fs']) / 5

    ecg_s   = 2 * int(settings['n_ecg']) * n_ecg_s
    acc_s   = 6 *n_acc_s
    
    ps = 26
    ps += ecg_s
    ps += acc_s

    if settings['ecg_rr'] == 'on':
        ps += 2
        n_rr_s = 1
    else:
        n_rr_s = 0

    if settings['temperature'] == 'on':
        ps += 2
        n_temp_s = 1
    else:
        n_temp_s = 0

    # make frame length divisible by 4
    if (ps % 4) != 0:
        ps += 2
        n_padd = 1
    else:
        n_padd = 0

    out = {'ps'       : int(ps),
           'ecg_ps'   : int(ecg_s),
           'acc_ps'   : int(acc_s),
           'n_ecg_c'  : int(settings['n_ecg']),
           'n_ecg_s'  : int(n_ecg_s),
           'n_acc_s'  : int(n_acc_s),
           'n_rr_s'   : int(n_rr_s),
           'n_temp_s' : int(n_temp_s),
           'n_padd'   : int(n_padd)}
        
    return(out)
    

def inv_lookup(d, v):
    """ Helper function for performing a reverse dictionary lookup. """
    invd = {str(v): str(k) for k, v in d.items()}
    return invd[str(v)]

    
def mode_to_str(ecg_n   = '1',
                ecg_fs  = '100',
                ecg_res = '1',
                ecg_hp  = '0',
                rr      = '0',
                acc_fs  = '20',
                acc_res = '1',
                temp    = '0'):
    """ Given settings (sampling rates, resolutions etc), Return the settings
        of a Faros device as a string.
    """
    ecg_fs  = inv_lookup(get_ecg_str_fs(), ecg_fs)
    ecg_res = inv_lookup(get_ecg_str_res(), ecg_res)
    ecg_hp  = inv_lookup(get_ecg_str_hp(), ecg_hp)

    acc_fs  = inv_lookup(get_acc_str_fs(), acc_fs)
    acc_res = inv_lookup(get_acc_str_res(), acc_res)
    
    vals = [ecg_n, ecg_fs, ecg_res, ecg_hp, rr, acc_fs, acc_res, temp]
    res  = ''.join([str(i) for i in vals])

    return(res)


def unpack_settings(s):
    """ Unpack the settings as one 8-character
        string.
    """
    s = s[3:]
    out = {'n_ecg'       : s[0],
           'ecg_fs'      : get_ecg_str_fs(s[1]),
           'ecg_res'     : get_ecg_str_res(s[2]),
           'ecg_hp'      : get_ecg_str_hp(s[3]),
           'ecg_rr'      : get_ecg_str_rr(s[4]),
           
           'acc_fs'      : get_acc_str_fs(s[5]),
           'acc_res'     : get_acc_str_res(s[6]),
           
           'temperature' : get_temp_str(s[7])}
    return(out)


# -------------------------------------------------------------------------------
# Functions for communicating with the Faros device
# -------------------------------------------------------------------------------

def connect(addr):
    """ Connect to a device using the bluetooth address addr. """
    port = 1
    s = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    s.connect((addr, port))

    return(s)


def disconnect(s):
    """ Disconnect from socket s. """
    s.close()

    
def send_command(s, command, r_length = 0, decode = True):
    """ Send a command to a Faros device.

        s        : the socket to send to
        command  : the command to send
        r_length : response length (if any). Default is 0 (no response)
        decode   : should the response data be decoded to ASCII
    """
    data = None
    s.send(command + '\r')

    if r_length:
        data = s.recv(r_length)
        if decode:
            try:
                data = data.decode("UTF-8").strip()
            except UnicodeDecodeError:
                data = None
    return(data)


def get_property(s, p):
    """ Get property p from socket s.
        p can be 'firmware-version', 'firmware'build', 'name'
        or 'settings'.
    """
    prop_map = {'firmware-version': ['wbainf', 9, True],
                'firmware-build': ['wbaind', 9, True],
                'name' : ['wbawho', 12, True],
                'device_time' : ['wbagdt', 8, False],
                'settings' : ['wbagds', 12, True]}
    if p in prop_map.keys():
        res = send_command(s, prop_map[p][0], prop_map[p][1], prop_map[p][2])
        return res
    else:
        return None

def set_device_time(s):
    """ Set current device time. """
    current_time = int(time.time())
    current_time += (-time.timezone)

    ct_bytes = struct.pack('i', current_time)

    s.send('wbasdt')
    s.send(ct_bytes)
    s.send('\r')

    data = s.recv(7)
    return data

def binary_time_to_unix_time(x):
    """ Convert Faros binary time to UNIX time. """
    device_time_bytes = x[3:].strip()
    return float(struct.unpack("<L", device_time_bytes)[0])

def unix_time_to_ts(x):
    """ Return the current time as a string. """
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(x))

def binary_time_to_str(x):
    """ Convert Faros binary time to a string. """
    return unix_time_to_ts(binary_time_to_unix_time(x))

def get_device_time(s):
    """ Get current device time. """
    s.send('wbagdt' + '\r')
    data = s.recv(8)
    
    return binary_time_to_str(data)
    

# -------------------------------------------------------------------------------
# Unpack the data received from a Faros device
# -------------------------------------------------------------------------------

def unpack_data(packet,
                packet_size,
                p_header,

                p_ecg         = None,
                p_acc         = None,
                p_marker      = None,
                p_rr          = None,
                p_temp        = None,
          
                outlet_ecg    = None,
                outlet_acc    = None,
                outlet_marker = None,
                outlet_rr     = None,
                outlet_temp   = None):
    """ Unpack data read from a Faros device and
        stream the data over the Lab Streaming Layer
        (LSL).
    """
    
    # (0) ----- Header -----
    header = p_header.parse(packet[0:8])

    # (1) ----- ECG -----
    if p_ecg is not None:
        ecg = p_ecg.parse(packet[8:(8 + packet_size['ecg_ps'])])['ecg']

        if int(packet_size['n_ecg_c']) > 1:
            ecg = [ecg[i::packet_size['n_ecg_s']] for i in range(packet_size['n_ecg_s'])]
        

    if outlet_ecg is not None:
        outlet_ecg.push_chunk(ecg)

    # (2) ----- Accelerometer -----
    if p_acc is not None:
        acc = p_acc.parse(packet[(8 + packet_size['ecg_ps']):(8 + packet_size['ecg_ps'] + packet_size['acc_ps'])])['acc']
        acc = [acc[i::packet_size['n_acc_s']] for i in range(packet_size['n_acc_s'])]

    if outlet_acc is not None:
        outlet_acc.push_chunk(acc)

    # (3) ----- Marker -----
    b1 = 8 + packet_size['ecg_ps'] + packet_size['acc_ps']
    b2 = b1 + 2
    marker = p_marker.parse(packet[b1:b2])['marker']
    if marker[0] > 0:
        outlet_marker.push_sample([1])

    # (4) ----- RR -----
    if p_rr is not None:
        b1 = 10 + packet_size['ecg_ps'] + packet_size['acc_ps']
        b2 = b1 + 2
        rr = p_rr.parse(packet[b1:b2])['rr'][0]
        if header['flag']['rr_in_packet']:
            outlet_rr.push_sample([rr])
        
    # (5) ----- Temperature -----
    if p_temp is not None:
        b1 = 10 + packet_size['ecg_ps'] + packet_size['acc_ps'] + 2 * packet_size['n_rr_s']
        b2 = b1 + 2
        temp = p_temp.parse(packet[b1:b2])['temp'][0]
        # convert raw ADC values to degrees Celsius
        temp = temp * (-(158.3488 + 53.3361)/4095) + 158.3488
        outlet_temp.push_sample([temp])

    # (6) ----- The packet checksum -----
    #
    # p_crc = Struct('packet_format', Array(1, ULInt16('crc')))
    # crc   = p_crc.parse(packet[-2:])['crc'][0]
    # crc2  = crc16.crc16xmodem(packet[:-2])
    # print(crc - crc2)
    
    
# -------------------------------------------------------------------------------
# Define Faros packet formats
# -------------------------------------------------------------------------------

def get_packet_header():
    
    packet_header = Struct('packet_format',
                             Bytes('sig_1', 1),
                             Bytes('sig_2', 1),
                             Bytes('sig_3', 1),
                             BitStruct("flag",
                                  BitField("battery_h", 1),
                                  BitField("battery_l", 1),
                                  BitField("rr_error", 1),
                                  BitField("dummy_4", 1),
                                  BitField("dummy_3", 1),
                                  BitField("dummy_2", 1),
                                  BitField("dummy_1", 1),
                                  BitField("rr_in_packet", 1)),
                             BitStruct("packet_number",
                                  BitField("pn", 32, swapped = True)))
    
    return packet_header


def get_data_packet(N, name):
    return Struct('packet_format', Array(N, SLInt16(name)))
