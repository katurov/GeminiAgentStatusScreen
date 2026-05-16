#include <SPI.h>
#include <TFT_eSPI.h>
#include "BluetoothSerial.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif

BluetoothSerial SerialBT;

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

// Global quota values
int qL = 0, qF = 0, qP = 0;
bool quotaReceived = false;
bool quotaValid = false;

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

void drawQuota() {
  if (!quotaReceived) return;

  int x_start = 215; // Starting X for quota area
  int y_top = 10;
  int barHeight = 110;
  int barWidth = 5;
  int gap = 3;

  // Clear area
  tft.fillRect(x_start - 2, 0, 240 - x_start + 2, 135, TFT_BLACK);

  if (!quotaValid) {
    tft.setTextSize(1);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    // Draw NA vertically centered in the bars area
    tft.drawString("NA", x_start, y_top + barHeight/2 - 4);
    
    // Still draw outlines
    for (int i = 0; i < 3; i++) {
      int x = x_start + i * (barWidth + gap);
      tft.drawRect(x, y_top, barWidth, barHeight, 0x3186); // Dim grey
    }
    return;
  }

  int values[3] = {qL, qF, qP};
  const char* labels[3] = {"L", "F", "P"};
  uint16_t colors[3] = {TFT_CYAN, TFT_YELLOW, TFT_MAGENTA};

  for (int i = 0; i < 3; i++) {
    int x = x_start + i * (barWidth + gap);
    
    // Draw Label
    tft.setTextSize(1);
    tft.setTextColor(TFT_WHITE);
    tft.drawString(labels[i], x, 0);

    // Draw Abris (Outline)
    tft.drawRect(x, y_top, barWidth, barHeight, TFT_WHITE);

    // Draw Fill
    int fillH = (values[i] * (barHeight - 2)) / 100;
    if (fillH > 0) {
      tft.fillRect(x + 1, y_top + barHeight - 1 - fillH, barWidth - 2, fillH, colors[i]);
    }
  }
}

void drawInterface() {
  tft.fillScreen(TFT_BLACK);
  
  // Always draw quota if we have it
  drawQuota();

  bool anyActive = false;
  for (int i = 0; i < MAX_WIDGETS; i++) {
    if (widgets[i].active) {
      anyActive = true;
      break;
    }
  }

  if (!anyActive) {
    tft.setTextColor(TFT_ORANGE, TFT_BLACK);
    tft.setTextSize(3); 
    String waitMsg = "Waiting";
    
    // Manual centering for TextSize 3 on 240x135 screen
    // TextSize 3 is approx 18x24 pixels per char
    int textW = waitMsg.length() * 18;
    int textH = 24;
    
    int targetX = (240 - textW) / 2;
    int targetY = (135 - textH) / 2;
    
    tft.drawString(waitMsg, targetX, targetY);
    return;
  }

  // The screen height is 135, width 240 (Rotation 1 or 3)
  int widgetHeight = 33;
  int maxWidth = quotaReceived ? 210 : 240;

  for (int i = 0; i < MAX_WIDGETS; i++) {
    if (!widgets[i].active) continue;

    int y_start = i * widgetHeight;
    
    // Row 1: [Source] Location (White)
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.setTextSize(2);
    String line1 = "[" + String(widgets[i].source) + "] " + widgets[i].location;
    
    // Truncate based on maxWidth (No more trailing dot)
    int chars = maxWidth / 12; // Approximation for TextSize 2
    if (line1.length() > chars) line1 = line1.substring(0, chars);
    tft.drawString(line1, 4, y_start);
    
    // Row 2: Event (Specific Color)
    tft.setTextColor(widgets[i].color, TFT_BLACK);
    String line2 = widgets[i].event;
    if (line2.length() > chars) line2 = line2.substring(0, chars);
    tft.drawString(line2, 4, y_start + 16);
    
    // Separator
    if (i < MAX_WIDGETS - 1) {
       tft.drawFastHLine(0, y_start + 32, maxWidth, 0x1082); // Dark grey line
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

void processInput(String input) {
  input.trim();
  if (input.length() == 0) return;
  
  Serial.println("DEBUG: " + input); 
  
  int start = input.indexOf('@');
  int end = input.indexOf('#');
  
  if (start != -1 && end != -1 && end > start) {
    String payload = input.substring(start + 1, end);
    // Expected format: Source:ColorCode:Location:Event
    // Example: B:Y:GenWineDesc:BeforeTool
    
    int c1 = payload.indexOf(':');
    if (c1 == -1) return;
    
    // Handle Quota command @Q:L:F:P# or @Q:NA#
    if (payload.startsWith("Q:")) {
       if (payload == "Q:NA") {
          quotaValid = false;
          quotaReceived = true;
          drawInterface();
          return;
       }

       int q1, q2, q3;
       if (sscanf(payload.c_str(), "Q:%d:%d:%d", &q1, &q2, &q3) == 3) {
          qL = q1; qF = q2; qP = q3;
          quotaValid = true;
          quotaReceived = true;
          drawInterface();
       }
       return;
    }

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

void setup() {
  Serial.begin(115200);
  SerialBT.begin("AgentStatuser"); // Bluetooth device name
  
  pinMode(BTN_1, INPUT_PULLUP);
  pinMode(BTN_2, INPUT_PULLUP);
  
  tft.init();
  tft.setRotation(rotation);
  
  // Backlight for TTGO T-Display
  pinMode(4, OUTPUT);
  digitalWrite(4, HIGH);
  
  // HARDWARE TEST: Draw a red box
  tft.fillScreen(TFT_RED);
  delay(1000);
  tft.fillScreen(TFT_BLACK);
  
  drawInterface();
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
    processInput(Serial.readStringUntil('\n'));
  }
  
  if (SerialBT.available()) {
    processInput(SerialBT.readStringUntil('\n'));
  }
}
