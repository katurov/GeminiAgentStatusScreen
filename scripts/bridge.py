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

# State for deduplication and PPID mapping
last_sent_msg = None
ppid_info = {} # ppid -> (letter, folder_name)
alphabet = string.ascii_uppercase

def get_info_for_ppid(ppid):
    if ppid is None: return "?", "?"
    if ppid not in ppid_info:
        # Assign next letter
        idx = len(ppid_info) % len(alphabet)
        letter = alphabet[idx]
        
        # Get CWD of the process
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
    global last_sent_msg
    event_name = data.get("hook_event_name")
    ppid = data.get("_ppid")
    
    letter, folder = get_info_for_ppid(ppid)
    
    msg_prefix = ""
    # Format: A:[Folder]:BeforeModel
    # Note: Using 240px screen, so keep it short
    text = f"{letter}:[{folder}]:{event_name}"
    
    if event_name in ["BeforeModel", "BeforeTool"]:
        msg_prefix = "Y:"
    elif event_name == "AfterModel":
        msg_prefix = "G:"
    elif event_name == "Notification" and data.get("notification_type") == "ToolPermission":
        msg_prefix = "R:"
        text = f"{letter}:[{folder}]:ToolPermission"

    if msg_prefix:
        full_msg = f"{msg_prefix}{text}"
        
        # Deduplication check
        if full_msg == last_sent_msg:
            return True
            
        try:
            ser.write((full_msg + "\n").encode('utf-8'))
            ser.flush()
            last_sent_msg = full_msg
            print(f"Sent: {full_msg}", flush=True)
        except Exception as e:
            print(f"Error writing to serial: {e}", flush=True)
            return False
    return True

def main():
    try:
        r = redis.Redis(host=R_HOST, port=R_PORT, decode_responses=True)
        ser = None
        print("Bridge started (with PPID/CWD mapping). Waiting for events...", flush=True)
        
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
