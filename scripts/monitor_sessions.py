import os
import json
import psutil
import urllib.request
from datetime import datetime

def get_gemini_config():
    base_dir = os.path.expanduser("~/.gemini")
    
    # Load projects
    projects_path = os.path.join(base_dir, "projects.json")
    projects = {}
    if os.path.exists(projects_path):
        with open(projects_path, "r") as f:
            projects = json.load(f).get("projects", {})
            
    # Load credentials
    creds_path = os.path.join(base_dir, "oauth_creds.json")
    token = None
    if os.path.exists(creds_path):
        with open(creds_path, "r") as f:
            token = json.load(f).get("access_token")
            
    return projects, token

def fetch_quota(project_id, token):
    if not token:
        return None
    url = "https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota"
    req_data = json.dumps({"project": project_id}).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

def get_active_sessions(projects_map):
    active = []
    for proc in psutil.process_iter(['pid', 'ppid', 'cmdline', 'cwd']):
        try:
            cmdline = proc.info['cmdline']
            if not cmdline: continue
            
            is_gemini = any('gemini' in arg for arg in cmdline)
            if is_gemini and 'node' in cmdline[0]:
                cwd = proc.info['cwd']
                if not cwd: continue
                
                env = proc.environ()
                if env.get('GEMINI_CLI_NO_RELAUNCH') != 'true':
                    continue

                session_id = "new/unknown"
                for i, arg in enumerate(cmdline):
                    if arg == '--resume' and i + 1 < len(cmdline):
                        session_id = cmdline[i+1]
                    elif arg == '--session-id' and i + 1 < len(cmdline):
                        session_id = cmdline[i+1]

                project_id = projects_map.get(cwd, "unknown")
                active.append({
                    "pid": proc.info['pid'],
                    "cwd": cwd,
                    "project_id": project_id,
                    "session_id": session_id
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return active

def main():
    projects_map, token = get_gemini_config()
    sessions = get_active_sessions(projects_map)
    
    if not sessions:
        print(json.dumps({"SESSIONS": [], "LIMITS": "No active sessions found"}, indent=2))
        return

    # Group by project
    project_quotas = {}
    unique_projects = {s['project_id'] for s in sessions if s['project_id'] != "unknown"}
    
    for pid in unique_projects:
        project_quotas[pid] = fetch_quota(pid, token)

    # Prepare output structure
    output = {
        "SESSIONS": [],
        "LIMITS": {}
    }

    for s in sessions:
        output["SESSIONS"].append({
            s['pid']: s['project_id']
        })

    grouped_limits = {}
    for proj_id, q_data in project_quotas.items():
        if q_data and "buckets" in q_data:
            for b in q_data["buckets"]:
                m_id = b['modelId'].lower()
                frac = b.get('remainingFraction', 1.0)
                used = round((1 - frac) * 100, 1)
                
                # Determine group
                if "flash-lite" in m_id:
                    group = "Flash-Lite"
                elif "flash" in m_id:
                    group = "Flash"
                elif "pro" in m_id:
                    group = "Pro"
                else:
                    group = m_id # Keep original if not matched
                
                # Keep the maximum usage found for this group
                if group not in grouped_limits or used > grouped_limits[group]:
                    grouped_limits[group] = used

    output["LIMITS"] = grouped_limits
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
