#!/usr/bin/env python3

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

import sys
import argparse
import time
from .libfaros import *
from .utilities import *
  
def faros_cli():
    parser = argparse.ArgumentParser(description = "Faros Streamer")
    parser.add_argument("--scan", action = "store_true", help="Scan for available Bluetooth devices.")
    parser.add_argument("--blink", action = "store_true", dest = "blink_device", help="Blink the lights of a device.")
    
    parser.add_argument("--device-list", dest = "device_list", help="File containing the names and bluetooth addresses of devices. Create using --scan and pipe the output to a file.")
    parser.add_argument("--mac", dest = "device_mac", help="Bluetooth MAC address.")
    parser.add_argument("--name", dest = "device_name", help="Bluetooth device name.")


    parser.add_argument("--show-settings", action = "store_true", dest = "show_settings", help="Get the settings of a device")
    parser.add_argument("--sync-time", action = "store_true", dest = "sync_time", help="Synchronise device time.")

    parser.add_argument("--configure", action = "store_true", help="Configure the device.")
    parser.add_argument("--ecg-n", dest = "ecg_n", help="Number of ECG channels (1 or 3).", default = 1)
    parser.add_argument("--ecg-fs", dest = "ecg_fs", help="ECG sampling rate in Hz (0, 100, 125, 250, 500, 1000).", default = 250)
    parser.add_argument("--ecg-res", dest = "ecg_res", help="ECG resolution in uV / count (0.25 uV or 1 uV).", default = 1)
    parser.add_argument("--ecg-hp", dest = "ecg_hp", help="ECG highpass filter in Hz (1 Hz or 10 Hz).", default = 1)
    
    parser.add_argument("--acc-fs", dest = "acc_fs", help="Acc sampling rate in Hz (0, 20, 25, 40, 50, 100)", default = 20)
    parser.add_argument("--acc-res", dest = "acc_res", help="Acc resolution in mg / count (0.25 uV or 1 uV)", default = 1)

    parser.add_argument("--rr", dest = "rr", help="Record RR interval (0 = no, 1 = yes)", default = 0)
    parser.add_argument("--temp", dest = "temp", help="Record temperature (0 = no, 1 = yes)", default = 0)


    parser.add_argument("--stream", action = "store_true", dest = "stream", help="Start streaming data.")

    parser.add_argument("--stream-prefix", dest = "stream_prefix",  help="LSL stream name prefix. Default is empty string.", default = "")

    # --------------------------------------------------
    
    args = parser.parse_args()

    # Scan for bluetooth devices
    if args.scan:
        device_list = get_devices()

    # Read device list if given
    if args.device_list is not None:
        device_list = read_device_list(args.device_list)
    else:
        device_list = None

    # (1) a MAC-address was given
    if args.device_mac is not None:
        device_mac = args.device_mac
        print("Using device with MAC address: " + device_mac)
    else:
        device_mac = None

    # (2) A name was given
    if args.device_name is not None:
        device_name = args.device_name
        try:
            if device_list is None:
                print("No device list provided, must scan for devices first.\n")
                device_list = get_devices()
            device_mac = device_list[device_name]
        except KeyError:
            device_mac = None
            print_error("Device not found in list.")
            sys.exit(1)
    else:
        device_name = None
            

    if (device_mac is None) and (device_name is None):
        print("No name or MAC address given. Cannot continue.\n")
        print("Type faros_streamer --help to display usage information.\n")
        sys.exit(1)
    
    # Try to connect to the given device
    try:
        faros_socket = connect(device_mac)
        command = "wbaoms"
        res     = send_command(faros_socket, command, 7)
        print("Connection established.\n")
    except:
        faros_socket = None
        print("Unable to connect to device ({0}).".format(sys.exc_info()[0]))
        sys.exit(1)

    # Set different parameters of the Faros device
    if args.configure:
        settings = mode_to_str(args.ecg_n,
                               args.ecg_fs,
                               args.ecg_res,
                               args.ecg_hp,
                               args.rr,
                               args.acc_fs,
                               args.acc_res,
                               args.temp)

        configure_device(faros_socket, settings)

    # Show device settings    
    if args.show_settings:
        properties = get_properties(faros_socket)
        print_properties(properties)

    # Synchronise the device time
    if args.sync_time:
        sync_time(faros_socket)
        
    # Should the device blink
    if args.blink_device:
        blink_device(faros_socket)

    # Start streaming data
    if args.stream:
        ## get the settings
        properties  = get_properties(faros_socket)
        settings    = unpack_settings(properties['settings'])
        packet_size = get_packet_size(settings)
        
        # Get packet formats and create LSL outlets
        p_header = get_packet_header()

        if args.stream_prefix != '':
            args.stream_prefix += '_'
        
        # (1) ----- ECG -----
        if packet_size['n_ecg_s'] > 0:
            p_ecg            = get_data_packet((packet_size['n_ecg_c'] * packet_size['n_ecg_s']), 'ecg')
            sn               = args.stream_prefix + 'faros_ecg'
            faros_outlet_ecg = create_lsl_outlet(sn, 'ECG', packet_size['n_ecg_c'], settings['ecg_fs'], channel_format = 'int16')
        else:
            p_ecg            = None
            faros_outlet_ecg = None
            
        # (2) ----- Acc -----
        if packet_size['n_acc_s'] > 0:
            p_acc            = get_data_packet(3 * packet_size['n_acc_s'], 'acc')
            sn               = args.stream_prefix + 'faros_acc'
            faros_outlet_acc = create_lsl_outlet(sn, 'Acc', 3, settings['acc_fs'], channel_format = 'int16')
        else:
            p_acc            = None
            faros_outlet_acc = None

        # (3) ----- Marker -----
        p_marker            = get_data_packet(1, 'marker')
        sn                  = args.stream_prefix + 'faros_marker'
        faros_outlet_marker = create_lsl_outlet(sn, "Marker", 1, 0.0, channel_format = 'int16')
 
        # (4) ----- RR -----
        if packet_size['n_rr_s'] > 0:
            p_rr              = get_data_packet(1, 'rr')
            sn                = args.stream_prefix + 'faros_rr'
            faros_outlet_rr   = create_lsl_outlet(sn, "RR", 1, 0.0, channel_format = 'int16')
        else:
            p_rr              = None
            faros_outlet_rr   = None
            
        # (5) ----- Temperature -----
        if packet_size['n_temp_s'] > 0:
            p_temp            = get_data_packet(1, 'temp')
            sn                = args.stream_prefix + 'faros_temp'
            faros_outlet_temp = create_lsl_outlet(sn, "Temp", 1, 5, channel_format = 'float32')
        else:
            p_temp            = None
            faros_outlet_temp = None

        streamer_thread = StreamerThread(stream_data   = False,
                                         faros_socket  = faros_socket,
                                         packet_size   = packet_size,

                                         p_header      = p_header,
                                         p_ecg         = p_ecg,
                                         p_acc         = p_acc,
                                         p_marker      = p_marker,
                                         p_rr          = p_rr,
                                         p_temp        = p_temp,

                                         outlet_ecg    = faros_outlet_ecg,
                                         outlet_acc    = faros_outlet_acc,
                                         outlet_marker = faros_outlet_marker,
                                         outlet_rr     = faros_outlet_rr,
                                         outlet_temp   = faros_outlet_temp)

        # Start the streaming and show a UI
        streamer_thread.start()

        while True:
            try:
                print("Streaming data. Enter 'q' to quit.")
                tmp = input(" > ")
                if tmp == "q":
                    streamer_thread.stop()
                    print("\nStreaming stopped.\n")
                    sys.exit(0)
            except KeyboardInterrupt:
                command = "wbaoms"
                send_command(faros_socket, command, 0)
                sys.exit(0)
                
if __name__ == '__main__':
    faros_streamer()
