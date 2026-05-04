import redis
import serial
import json
import time
import sys
import string
import os
import psutil
import atexit
from dotenv import load_dotenv

load_dotenv()

R_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
R_PORT = int(os.getenv('REDIS_PORT', 6379))
R_QUEUE = os.getenv('REDIS_QUEUE', 'gemini_events')
SERIAL_PORT = os.getenv('SERIAL_PORT', "/dev/cu.usbserial-01EEA79E")
BAUD_RATE = int(os.getenv('BAUD_RATE', 115200))
PID_FILE = "bridge.pid"

def check_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if psutil.pid_exists(old_pid):
                print(f"\n[!] ERROR: Another instance of bridge.py is already running (PID: {old_pid}).")
                print(f"[!] Please stop it first using: pkill -f bridge.py\n")
                sys.exit(1)
        except (ValueError, OSError):
            pass
    
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def remove_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

atexit.register(remove_pid)

ppid_to_letter = {} 
alphabet = [c for c in string.ascii_uppercase if c != 'G']

def get_info_for_ppid(ppid, create_if_missing=True):
    if ppid is None: 
        return "A", "unknown"
    
    if ppid not in ppid_to_letter:
        if not create_if_missing:
            return None, None
            
        # Находим первую свободную букву, которой нет в текущем словаре
        used_letters = {val[0] for val in ppid_to_letter.values()}
        letter = "A"
        for char in alphabet:
            if char not in used_letters:
                letter = char
                break
        
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
    
    # Для событий завершения не создаем новую запись, если её нет
    is_exit_event = event_name in ["AfterAll", "SessionEnd"]
    letter, folder = get_info_for_ppid(ppid, create_if_missing=not is_exit_event)
    
    if letter is None:
        # Событие завершения для уже удаленного или неизвестного процесса
        return True
    
    color_code = ""
    status_text = event_name
    should_clear_ppid = False

    if event_name in ["BeforeAll", "SessionStart"]:
        color_code = "B"
        status_text = "Ready"
    elif is_exit_event:
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
    check_pid()
    print("Bridge (Session Lifecycle Mode) starting...", flush=True)
    r = redis.Redis(host=R_HOST, port=R_PORT, decode_responses=True)
    ser = None
    
    try:
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
    except KeyboardInterrupt:
        print("\nBridge stopped by user.", flush=True)
    finally:
        if ser:
            ser.close()

if __name__ == "__main__":
    main()
