import redis
import serial
import json
import time
import sys
import string

# Redis setup
R_HOST = '127.0.0.1'
R_PORT = 6379
R_QUEUE = 'gemini_events'

# Serial setup
SERIAL_PORT = "/dev/cu.usbserial-01EEA79E"
BAUD_RATE = 115200

# State for deduplication and PPID mapping
last_sent_msg = None
ppid_to_letter = {}
alphabet = string.ascii_uppercase # A, B, C...

def get_letter_for_ppid(ppid):
    if ppid is None: return "?"
    if ppid not in ppid_to_letter:
        # Assign next letter
        idx = len(ppid_to_letter) % len(alphabet)
        ppid_to_letter[ppid] = alphabet[idx]
    return ppid_to_letter[ppid]

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
    agent_id = get_letter_for_ppid(ppid)
    
    msg_prefix = ""
    text = f"{agent_id}:{event_name}"
    
    if event_name in ["BeforeModel", "BeforeTool"]:
        msg_prefix = "Y:"
    elif event_name == "AfterModel":
        msg_prefix = "G:"
    elif event_name == "Notification" and data.get("notification_type") == "ToolPermission":
        msg_prefix = "R:"
        text = f"{agent_id}:ToolPermission"

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
        print("Bridge started (with PPID mapping). Waiting for events...", flush=True)
        
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
