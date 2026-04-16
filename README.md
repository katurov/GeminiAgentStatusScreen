# 📟 Gemini Agent Monitor (ESP32)

A visual monitoring system for Gemini CLI agents on an external **LilyGo TTGO T-Display** screen.

## Why do you need this?
When running complex tasks, Gemini CLI may spawn sub-agents or perform long-running operations. This system allows you to:
* See the real-time status without checking logs.
* Track multiple agents simultaneously (each with its own widget).
* Identify which folder (project) the action is currently taking place in.
* Instantly recognize tool execution requests (red status for permission).

## How it works
The system uses **Redis** as a broker. This ensures that Gemini is not blocked when sending data to a potentially slow Serial port. A dedicated "bridge" (`bridge.py`) monitors process activity and updates the widgets on the screen.

## Display Logic (LRU Stack)
The ESP32 screen displays up to **4 most recent active sources**:
* If an update comes from an existing source, its widget moves to the **top slot**.
* When a new source appears, it is added to the top, shifting others down. If all slots are full, the oldest (bottom) one is removed.
* Each widget consists of two lines:
  * **Line 1:** `[Source] Folder` (White color).
  * **Line 2:** `Current Status` (Color-coded status).

## Quick Start
1. **Hardware:** Connect your ESP32 via USB. The firmware is located in `src/main.cpp`. Build and upload it using PlatformIO.
2. **Docker:** Start Redis: `docker run -d --name gemini-redis -p 6379:6379 redis:alpine`.
3. **Bridge:** Start the background process: `python3 scripts/bridge.py`.
   * *Note:* PID protection is implemented via `bridge.pid`. If another instance is running, the script will show an error.
4. **Configuration:** Add the hooks to your Gemini settings (see below).

## Hooks Installation
To enable monitoring, you need to register the `hook.py` script in your Gemini CLI configuration. Open `~/.gemini/settings.json` and add the following configuration:

```json
{
  "hooksConfig": {
    "enabled": true,
    "notifications": true
  },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/username/AgentStatuser/scripts/hook.py"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/username/AgentStatuser/scripts/hook.py"
          }
        ]
      }
    ],
    "BeforeModel": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/username/AgentStatuser/scripts/hook.py"
          }
        ]
      }
    ],
    "AfterModel": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/username/AgentStatuser/scripts/hook.py"
          }
        ]
      }
    ],
    "BeforeToolSelection": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/username/AgentStatuser/scripts/hook.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/username/AgentStatuser/scripts/hook.py"
          }
        ]
      }
    ]
  }
}
```

## Color Indication
* 🟦 **Blue (Ready):** Agent is started and waiting.
* 🟨 **Yellow (Working):** Agent is thinking or calling a tool.
* 🟩 **Green (Success):** Response received.
* 🟥 **Red (Wait):** Tool execution permission is required.
* ⬛ **OFF:** Widget is removed from the screen when the session ends.
