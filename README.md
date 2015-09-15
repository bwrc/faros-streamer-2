Faros Streamer Overview
------------------------
Faros Streamer is a command-line application for streaming online data from a Mega Electronics Ltd. [Faros device](http://www.megaemg.com/products/faros/) using the [Lab Streaming Layer](https://github.com/sccn/labstreaminglayer/tree/master/LSL/liblsl).


Installation Instructions
-------------------------
Please note that Faros Stremaer requires Python 3.

Using [PIP](https://github.com/pypa/pip) you can directly install the latest version of Faros Stramer
```
   pip install git+https://github.com/bwrc/faros-streamer-2/
```
Faros Streamer is tested on GNU/Linux.


Using Faros Streamer
--------------------
First set the Faros device into Online mode using [Faros Manager](http://www.megaemg.com/support/unrestricted-downloads/) (in Windows)
Below are listed some common tasks. Please use
```
   faros_streamer --help
```
to see all available command line options.


### Search for available device
* Search for available Faros devices by typing
```
   faros_streamer --scan
```
and the response will be something like:
```
   Scanning for available devices.
   Found the following devices:
   AATOS-0001     AA:BB:CC:11:22:33
```
Here `AATOS-0001` is the name of the device and `AA:BB:CC:11:22:33` is the Bluetooth MAC address of the device.

### Blink the lights of a device
```
   faros_streamer --blink --mac AA:BB:CC:11:22:33
```

### Check the settings of a device
```
   faros_streamer --mac AA:BB:CC:11:22:33 --show-settings
```

### Configuring a device
```
   faros_streamer --mac AA:BB:CC:11:22:33 --ecg-n 1 --ecg-fs 250  --acc-fs 20 --rr 0 --temp 0 --configure
```

After this you should again check the settings to verify that the device was correctly configured.
Use `faros_streamer --help" to see all command line options.

### Stream data from the device
Once the device is configured, you can now stream data as follows:
```
   faros_streamer --mac AA:BB:CC:11:22:33  --stream
```

### Chaining multiple commands
It is also possible to chain multiple commands, e.g., configuring the device and directly starting the LSL streaming:
```
   faros_streamer --mac AA:BB:CC:11:22:33 --ecg-n 1 --ecg-fs 250  --acc-fs 20 --rr 0 --temp 0 --configure --stream
```

### Blink the lights of the device
The lights of the device can be blinked, which is useful if you have multiple devices and need to locate one of them:
```
   faros_streamer --mac AA:BB:CC:11:22:33 --blink
```

### Storing a device configuration
If you have multiple Faros devices it is possible to store the name-MAC pairs of the devices into a file. As an example, you can create a file called `device_list.txt` with the contents
```
Scanning for available devices.
Found the following devices:
AATOS-0001     AA:BB:CC:11:22:33
AATOS-0002     AA:BB:CC:11:22:44
AATOS-0003     AA:BB:CC:11:22:55
```

This file can be directly created by running
```
   faros_streamer --scan > device_list.txt
```

With this file, you can use, e.g.,  `--name AATOS-0001` instead of `--mac AA:BB:CC:11:22:33`:
```
   faros_streamer --device-list device_list.txt --name AATOS-0001 --blink
```
