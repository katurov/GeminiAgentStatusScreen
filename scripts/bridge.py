import redis
import serial
import json
import time
import sys
import string
import os
import psutil

R_HOST = '127.0.0.1'
R_PORT = 6379
R_QUEUE = 'gemini_events'
SERIAL_PORT = "/dev/cu.usbserial-01EEA79E"
BAUD_RATE = 115200

ppid_to_letter = {} 
alphabet = [c for c in string.ascii_uppercase if c != 'G']

def get_info_for_ppid(ppid):
    if ppid is None: return "A", "unknown"
    if ppid not in ppid_to_letter:
        idx = len(ppid_to_letter) % len(alphabet)
        letter = alphabet[idx]
        try:
            p = psutil.Process(ppid)
            folder = os.path.basename(p.cwd())
        except:
            folder = "unknown"
        ppid_to_letter[ppid] = (letter, folder)
    return ppid_to_letter[ppid]

def process_event(ser, data):
    event_name = data.get("hook_event_name")
    ppid = data.get("_ppid")
    
    letter, folder = get_info_for_ppid(ppid)
    
    color_code = ""
    status_text = event_name
    should_clear_ppid = False

    if event_name == "BeforeAll":
        color_code = "B"
        status_text = "Ready"
    elif event_name == "AfterAll":
        color_code = "K"
        status_text = "OFF"
        should_clear_ppid = True
    elif event_name in ["BeforeModel", "BeforeTool"]:
        color_code = "Y"
    elif event_name == "AfterModel":
        color_code = "G"
    elif event_name == "Notification" and data.get("notification_type") == "ToolPermission":
        color_code = "R"
        status_text = "Permission"

    if color_code:
        full_msg = f"@{letter}:{color_code}:{folder}:{status_text}#"
        try:
            ser.write((full_msg + "\n").encode('utf-8'))
            ser.flush()
            print(f"Sent: {full_msg}", flush=True)
            if should_clear_ppid and ppid in ppid_to_letter:
                del ppid_to_letter[ppid]
        except Exception as e:
            print(f"Error: {e}", flush=True)
            return False
    return True

def main():
    print("Bridge (Lifecycle Mode) starting...", flush=True)
    r = redis.Redis(host=R_HOST, port=R_PORT, decode_responses=True)
    ser = None
    
    while True:
        if ser is None:
            try:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                time.sleep(2)
            except:
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

if __name__ == "__main__":
    main()
