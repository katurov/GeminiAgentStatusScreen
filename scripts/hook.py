import sys
import json
import os
import socket
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Redis config
R_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
R_PORT = int(os.getenv('REDIS_PORT', 6379))
R_QUEUE = os.getenv('REDIS_QUEUE', 'gemini_events')

def redis_lpush_raw(data_str):
    try:
        cmd = (
            f"*3\r\n$5\r\nLPUSH\r\n"
            f"${len(R_QUEUE)}\r\n{R_QUEUE}\r\n"
            f"${len(data_str)}\r\n{data_str}\r\n"
        ).encode('utf-8')
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.05) 
            s.connect((R_HOST, R_PORT))
            s.sendall(cmd)
            return True
    except Exception:
        return False

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return

        # Добавляем PPID к данным перед отправкой
        try:
            data = json.loads(input_data)
            data['_ppid'] = os.getppid()
            payload = json.dumps(data)
        except:
            payload = input_data

        redis_lpush_raw(payload)

        sys.stdout.write(json.dumps({}))
        sys.stdout.flush()

    except Exception:
        sys.stdout.write(json.dumps({}))
        sys.stdout.flush()

if __name__ == "__main__":
    main()
