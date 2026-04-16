import redis
import serial
import json
import time
import sys
import string
import os
import psutil

# Redis setup
R_HOST = '127.0.0.1'
R_PORT = 6379
R_QUEUE = 'gemini_events'

# Serial setup
SERIAL_PORT = "/dev/cu.usbserial-01EEA79E"
BAUD_RATE = 115200

# State for PPID mapping
ppid_info = {} # ppid -> (letter, folder_name)
alphabet = string.ascii_uppercase

def get_info_for_ppid(ppid):
    if ppid is None: return "A", "unknown"
    if ppid not in ppid_info:
        idx = len(ppid_info) % len(alphabet)
        letter = alphabet[idx]
        try:
            p = psutil.Process(ppid)
            cwd = p.cwd()
            folder = os.path.basename(cwd)
        except:
            folder = "unknown"
        ppid_info[ppid] = (letter, folder)
    return ppid_info[ppid]

def get_serial():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        return ser
    except Exception as e:
        print(f"Error opening serial: {e}", flush=True)
        return None

def process_event(ser, data):
    event_name = data.get("hook_event_name")
    ppid = data.get("_ppid")
    
    letter, folder = get_info_for_ppid(ppid)
    
    color_code = ""
    status_text = event_name
    
    if event_name in ["BeforeModel", "BeforeTool"]:
        color_code = "Y"
    elif event_name == "AfterModel":
        color_code = "G"
    elif event_name == "Notification" and data.get("notification_type") == "ToolPermission":
        color_code = "R"
        status_text = "ToolPermission"

    if color_code:
        # Новый формат: Letter:ColorCode:Status:Folder
        full_msg = f"{letter}:{color_code}:{status_text}:{folder}"
        try:
            ser.write((full_msg + "\n").encode('utf-8'))
            ser.flush()
            print(f"Sent: {full_msg}", flush=True)
        except Exception as e:
            print(f"Error writing to serial: {e}", flush=True)
            return False
    return True

def main():
    try:
        r = redis.Redis(host=R_HOST, port=R_PORT, decode_responses=True)
        ser = None
        print("Bridge started (Widget Mode). Waiting for events...", flush=True)
        
        while True:
            if ser is None:
                ser = get_serial()
                if ser is None:
                    time.sleep(5)
                    continue
            try:
                result = r.brpop(R_QUEUE, timeout=5)
                if result:
                    _, item = result
                    data = json.loads(item)
                    if not process_event(ser, data):
                        ser.close()
                        ser = None
            except Exception as e:
                print(f"Loop error: {e}", flush=True)
                time.sleep(1)
    except KeyboardInterrupt:
        if ser: ser.close()
        print("\nBridge stopped.", flush=True)

if __name__ == "__main__":
    main()
