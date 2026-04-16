#include <SPI.h>
#include <TFT_eSPI.h>

#define MAX_WIDGETS 4

struct AgentWidget {
  char letter = ' ';
  String folder = "";
  String status = "";
  uint16_t color = TFT_WHITE;
  bool active = false;
};

AgentWidget widgets[MAX_WIDGETS];
TFT_eSPI tft = TFT_eSPI();

void drawInterface() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextSize(2);
  
  for (int i = 0; i < MAX_WIDGETS; i++) {
    if (!widgets[i].active) continue;

    int y_start = i * (16 * 2 + 1); 
    
    // Row 1: Letter:[Folder]
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    char buf[25];
    String f = widgets[i].folder;
    if (f.length() > 15) f = f.substring(0, 14) + "..";
    snprintf(buf, 25, "%c:[%s]", widgets[i].letter, f.c_str());
    tft.drawString(buf, 0, y_start);
    
    // Row 2: Status
    tft.setTextColor(widgets[i].color, TFT_BLACK);
    String st = widgets[i].status;
    if (st.length() > 20) st = st.substring(0, 20);
    tft.drawString(st, 0, y_start + 16);
    
    tft.drawFastHLine(0, y_start + 32, 240, 0x1082); 
  }
}

void removeAgent(char letter) {
  for (int i = 0; i < MAX_WIDGETS; i++) {
    if (widgets[i].active && widgets[i].letter == letter) {
      widgets[i].active = false;
      widgets[i].letter = ' ';
      drawInterface();
      return;
    }
  }
}

void updateAgent(char letter, uint16_t color, String folder, String status) {
  int idx = -1;
  for (int i = 0; i < MAX_WIDGETS; i++) {
    if (widgets[i].active && widgets[i].letter == letter) {
      idx = i;
      break;
    }
  }

  if (idx == -1) {
    for (int i = 0; i < MAX_WIDGETS; i++) {
      if (!widgets[i].active) {
        idx = i;
        break;
      }
    }
  }

  if (idx == -1) return; // No free slots

  widgets[idx].letter = letter;
  widgets[idx].color = color;
  widgets[idx].folder = folder;
  widgets[idx].status = status;
  widgets[idx].active = true;

  drawInterface();
}

void setup() {
  Serial.begin(115200);
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  pinMode(4, OUTPUT);
  digitalWrite(4, HIGH);
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    int start = input.indexOf('@');
    int end = input.indexOf('#');
    
    if (start != -1 && end != -1 && end > start) {
      String payload = input.substring(start + 1, end);
      int c1 = payload.indexOf(':');
      int c2 = payload.indexOf(':', c1 + 1);
      int c3 = payload.indexOf(':', c2 + 1);
      
      if (c1 != -1 && c2 != -1 && c3 != -1) {
        char letter = payload[0];
        char colorCode = payload[c1 + 1];
        String folder = payload.substring(c2 + 1, c3);
        String status = payload.substring(c3 + 1);
        
        if (colorCode == 'K') {
           removeAgent(letter);
        } else {
          uint16_t color = TFT_WHITE;
          if (colorCode == 'Y') color = TFT_YELLOW;
          else if (colorCode == 'G') color = TFT_GREEN;
          else if (colorCode == 'R') color = TFT_RED;
          else if (colorCode == 'B') color = TFT_BLUE;

          updateAgent(letter, color, folder, status);
        }
      }
    }
  }
}
