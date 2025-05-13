import time
import sys
import os
import serial
import serial.tools.list_ports
from xmodem import XMODEM


def setDTRState(serialPort, state):
    serialPort.setDTR(state)

def setRTSState(serialPort, state):
    serialPort.setRTS(state)
    serialPort.setDTR(serialPort.dtr)

def enterBoot(serialPort):
    setDTRState(serialPort, False)
    setRTSState(serialPort, True)
    time.sleep(0.1)
    setDTRState(serialPort, True)
    setRTSState(serialPort, False)
    time.sleep(1)

def exitBoot(serialPort):
    setRTSState(serialPort, True)
    try:
        serialPort.write(b'2\r\n')
    except Exception as e:
        print(f"Error exiting: {e}")
    time.sleep(0.1)  
    setRTSState(serialPort, False)
    time.sleep(0.1)  
    print("Boot mode exited.")


def upload_firmware(port, filename):
    boot_prompt_detected = False
    buffer = ""
    timeout = time.time() + 10
    while time.time() < timeout:
        if port.in_waiting:
            data = port.read(port.in_waiting).decode(errors='ignore')
            buffer += data
            if "BL >" in buffer:
                boot_prompt_detected = True
                break
        time.sleep(0.1)
    if not boot_prompt_detected:
        print("Bootloader menu not detected!")
        return False
    port.reset_input_buffer()
    port.reset_output_buffer()
    time.sleep(1)
    port.write(b'1\r\n')
    time.sleep(2)
    timeout = time.time() + 10
    while time.time() < timeout:
        if port.in_waiting:
            c = port.read(1)
            if c == b'C':
                break
        time.sleep(0.1)
    else:
        print("Did not entered in upload mode.")
        return False


    time.sleep(1)
    def getc(size, timeout=1):
        time.sleep(0.025)
        return port.read(size) or None
    def putc(data, timeout=5):
        port.reset_output_buffer()
        return port.write(data)
    modem = XMODEM(getc, putc)
    with open(filename, 'rb') as file:
        total_size = file.seek(0, 2)
        file.seek(0)
        sent = [0]
        def progress(total_packets, success_count, error_count):
            sent[0] = success_count * 128
            percent = int((sent[0] / total_size) * 100)
            if(percent>0):
                print(f"\rUploading... {percent}%", end='', flush=True)
        sys.stderr = open(os.devnull, 'w')
        status = modem.send(file, callback=progress)
        sys.stderr = sys.__stderr__ 

        print("\nUpload successful!" if status else "\nUpload failed!")
        return status

if __name__ == "__main__":
    print("Available ports:")
    ports = serial.tools.list_ports.comports()
    port_name = None

    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device} - {port.description}")
        if "Silicon Labs CP210x" in port.description or "Zigbee" in port.description:
            port_name = port.device
    if port_name:
        print(f"\nSelected port: {port_name}")
    else:
        print("\nNo device with matching description found.")
        exit()

    firmware_file = "7-4-4.gbl"
    try:
        ser = serial.Serial(port_name, 115200, xonxoff=True, rtscts=False, dsrdtr=False, timeout=10)
        print(f"Connected to {port_name}")
        print("Entering boot mode...")
        enterBoot(ser)
        if upload_firmware(ser, firmware_file):
            print("Exiting boot mode...")
            exitBoot(ser)
        else:
            print("Failed to upload firmware.")
        ser.close()
    except Exception as e:
        print(f"Error: {e}")
