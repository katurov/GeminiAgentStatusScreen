#include <SPI.h>
#include <TFT_eSPI.h>

#define MAX_WIDGETS 4

struct AgentWidget {
  char source = ' ';
  String location = "";
  String event = "";
  uint16_t color = TFT_WHITE;
  bool active = false;
  uint32_t lastUpdate = 0;
};

AgentWidget widgets[MAX_WIDGETS];
TFT_eSPI tft = TFT_eSPI();
uint8_t rotation = 1;

#define BTN_1 35
#define BTN_2 0

uint16_t getColor(char code) {
  switch (code) {
    case 'G': return TFT_GREEN;
    case 'B': return TFT_BLUE;
    case 'R': return TFT_RED;
    case 'Y': return TFT_YELLOW;
    case 'K': return TFT_BLACK;
    default: return TFT_WHITE;
  }
}

void drawInterface() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextSize(2);

  bool anyActive = false;
  for (int i = 0; i < MAX_WIDGETS; i++) {
    if (widgets[i].active) {
      anyActive = true;
      break;
    }
  }

  if (!anyActive) {
    tft.setTextColor(TFT_GREEN);
    tft.setCursor(0, 0);
    tft.println("AgentStatuser Ready");
    return;
  }

  // The screen height is 135, width 240 (Rotation 1 or 3)
  int widgetHeight = 33;

  for (int i = 0; i < MAX_WIDGETS; i++) {
    if (!widgets[i].active) continue;

    int y_start = i * widgetHeight;
    
    // Row 1: [Source] Location (White)
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    String line1 = "[" + String(widgets[i].source) + "] " + widgets[i].location;
    if (line1.length() > 20) line1 = line1.substring(0, 19) + ".";
    tft.drawString(line1, 4, y_start);
    
    // Row 2: Event (Specific Color)
    tft.setTextColor(widgets[i].color, TFT_BLACK);
    String line2 = widgets[i].event;
    if (line2.length() > 20) line2 = line2.substring(0, 20);
    tft.drawString(line2, 4, y_start + 16);
    
    // Separator
    if (i < MAX_WIDGETS - 1) {
       tft.drawFastHLine(0, y_start + 32, 240, 0x1082); // Dark grey line
    }
  }
}

void removeWidget(char source) {
  int foundIdx = -1;
  for (int i = 0; i < MAX_WIDGETS; i++) {
    if (widgets[i].active && widgets[i].source == source) {
      foundIdx = i;
      break;
    }
  }

  if (foundIdx != -1) {
    // Shift others up
    for (int i = foundIdx; i < MAX_WIDGETS - 1; i++) {
      widgets[i] = widgets[i + 1];
    }
    widgets[MAX_WIDGETS - 1].active = false;
    drawInterface();
  }
}

void updateWidget(char source, uint16_t color, String location, String event) {
  int foundIdx = -1;
  for (int i = 0; i < MAX_WIDGETS; i++) {
    if (widgets[i].active && widgets[i].source == source) {
      foundIdx = i;
      break;
    }
  }

  AgentWidget newWidget;
  newWidget.source = source;
  newWidget.location = location;
  newWidget.event = event;
  newWidget.color = color;
  newWidget.active = true;
  newWidget.lastUpdate = millis();

  if (foundIdx != -1) {
    // Move existing to top: shift widgets above it down
    for (int i = foundIdx; i > 0; i--) {
      widgets[i] = widgets[i - 1];
    }
    widgets[0] = newWidget;
  } else {
    // New source: shift everything down, dropping the last if necessary
    for (int i = MAX_WIDGETS - 1; i > 0; i--) {
      widgets[i] = widgets[i - 1];
    }
    widgets[0] = newWidget;
  }

  drawInterface();
}

void setup() {
  Serial.begin(115200);
  
  pinMode(BTN_1, INPUT_PULLUP);
  pinMode(BTN_2, INPUT_PULLUP);
  
  tft.init();
  tft.setRotation(rotation);
  tft.fillScreen(TFT_BLACK);
  
  // Backlight for TTGO T-Display
  pinMode(4, OUTPUT);
  digitalWrite(4, HIGH);
  
  tft.setTextSize(2);
  tft.setTextColor(TFT_GREEN);
  tft.setCursor(0, 0);
  tft.println("AgentStatuser Ready");
}

void loop() {
  // Check buttons for rotation
  if (digitalRead(BTN_1) == LOW) {
    if (rotation != 1) {
      rotation = 1;
      tft.setRotation(rotation);
      drawInterface();
      delay(200); // Debounce
    }
  }
  
  if (digitalRead(BTN_2) == LOW) {
    if (rotation != 3) {
      rotation = 3;
      tft.setRotation(rotation);
      drawInterface();
      delay(200); // Debounce
    }
  }

  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    int start = input.indexOf('@');
    int end = input.indexOf('#');
    
    if (start != -1 && end != -1 && end > start) {
      String payload = input.substring(start + 1, end);
      // Expected format: Source:ColorCode:Location:Event
      // Example: B:Y:GenWineDesc:BeforeTool
      
      int c1 = payload.indexOf(':');
      if (c1 == -1) return;
      
      int c2 = payload.indexOf(':', c1 + 1);
      if (c2 == -1) return;
      
      int c3 = payload.indexOf(':', c2 + 1);
      if (c3 == -1) return;
      
      char source = payload.substring(0, c1)[0];
      char colorCode = payload.substring(c1 + 1, c2)[0];
      String location = payload.substring(c2 + 1, c3);
      String event = payload.substring(c3 + 1);
      
      if (colorCode == 'K') {
        removeWidget(source);
      } else {
        updateWidget(source, getColor(colorCode), location, event);
      }
    }
  }
}
