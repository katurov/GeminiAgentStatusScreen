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

# Import quota functions from our new script
import monitor_sessions

load_dotenv()

R_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
R_PORT = int(os.getenv('REDIS_PORT', 6379))
R_QUEUE = os.getenv('REDIS_QUEUE', 'gemini_events')
SERIAL_PORT = os.getenv('SERIAL_PORT', "/dev/cu.usbserial-01EEA79E")
BAUD_RATE = int(os.getenv('BAUD_RATE', 115200))
PID_FILE = "bridge.pid"

# Quota state
last_quota_update = 0
QUOTA_INTERVAL = 120 # 2 minutes

ppid_to_letter = {} 
alphabet = [c for c in string.ascii_uppercase if c != 'G']

def send_quota(ser, projects_map, token):
    try:
        if not token:
            return

        # Get active projects from sessions
        sessions = monitor_sessions.get_active_sessions(projects_map)
        unique_projects = {s['project_id'] for s in sessions if s['project_id'] != "unknown"}
        
        # If no active sessions, fall back to the first available project to show some status
        if not unique_projects:
            first_proj = next((pid for pid in projects_map.values() if pid != "unknown"), None)
            if first_proj:
                unique_projects = {first_proj}
        
        if not unique_projects:
            return

        max_qL = 0; max_qF = 0; max_qP = 0
        
        for project_id in unique_projects:
            q_data = monitor_sessions.fetch_quota(project_id, token)
            if q_data and "buckets" in q_data:
                for b in q_data["buckets"]:
                    m_id = b['modelId'].lower()
                    used = round((1 - b.get('remainingFraction', 1.0)) * 100)
                    if "flash-lite" in m_id: max_qL = max(max_qL, used)
                    elif "flash" in m_id: max_qF = max(max_qF, used)
                    elif "pro" in m_id: max_qP = max(max_qP, used)
        
        msg = f"@Q:{max_qL}:{max_qF}:{max_qP}#"
        ser.write((msg + "\n").encode('utf-8'))
        ser.flush()
        print(f"[{time.strftime('%H:%M:%S')}] Quota sent: {msg} (Projects: {', '.join(unique_projects)})", flush=True)
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Quota error: {e}", flush=True)

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

def get_info_for_ppid(ppid, cwd=None, create_if_missing=True, projects_map=None):
    if ppid is None: 
        return "A", "unknown"
    
    if ppid not in ppid_to_letter:
        if not create_if_missing:
            return None, None
            
        used_letters = {val[0] for val in ppid_to_letter.values()}
        letter = "A"
        for char in alphabet:
            if char not in used_letters:
                letter = char
                break
        
        # Resolve folder name
        folder = "unknown"
        if cwd:
            if projects_map and cwd in projects_map:
                folder = projects_map[cwd]
            else:
                folder = os.path.basename(cwd)
        
        # Fallback to psutil if cwd not provided or unknown
        if folder == "unknown":
            try:
                p = psutil.Process(ppid)
                p_cwd = p.cwd()
                if projects_map and p_cwd in projects_map:
                    folder = projects_map[p_cwd]
                else:
                    folder = os.path.basename(p_cwd)
            except:
                pass
                
        ppid_to_letter[ppid] = (letter, folder)
        
    return ppid_to_letter[ppid]

def process_event(ser, data, projects_map):
    event_name = data.get("hook_event_name")
    ppid = data.get("_ppid")
    cwd = data.get("cwd")
    
    is_exit_event = event_name in ["AfterAll", "SessionEnd"]
    letter, folder = get_info_for_ppid(ppid, cwd=cwd, create_if_missing=not is_exit_event, projects_map=projects_map)
    
    if letter is None:
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
    elif event_name == "AfterModel" or event_name == "AfterAgent":
        color_code = "G"
    elif event_name == "Notification" and data.get("notification_type") == "ToolPermission":
        color_code = "R"
        status_text = "Permission"

    if color_code:
        full_msg = f"@{letter}:{color_code}:{folder}:{status_text}#"
        try:
            ser.write((full_msg + "\n").encode('utf-8'))
            ser.flush()
            # print(f"Sent: {full_msg}", flush=True)
            if should_clear_ppid and ppid in ppid_to_letter:
                del ppid_to_letter[ppid]
        except Exception as e:
            # print(f"Error: {e}", flush=True)
            return False
    return True

def main():
    check_pid()
    # print("Bridge (Session Lifecycle Mode) starting...", flush=True)
    r = redis.Redis(host=R_HOST, port=R_PORT, decode_responses=True)
    ser = None
    
    projects_map, token = monitor_sessions.get_gemini_config()
    last_quota_update = 0

    try:
        while True:
            if ser is None:
                try:
                    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                    time.sleep(2)
                    send_quota(ser, projects_map, token)
                    last_quota_update = time.time()
                except:
                    time.sleep(5)
                    continue
            try:
                if time.time() - last_quota_update > QUOTA_INTERVAL:
                    send_quota(ser, projects_map, token)
                    last_quota_update = time.time()

                result = r.brpop(R_QUEUE, timeout=1)
                if result:
                    _, item = result
                    data = json.loads(item)
                    if not process_event(ser, data, projects_map):
                        ser.close()
                        ser = None
            except Exception as e:
                # print(f"Loop error: {e}", flush=True)
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nBridge stopped by user.", flush=True)
    finally:
        if ser:
            ser.close()

if __name__ == "__main__":
    main()
