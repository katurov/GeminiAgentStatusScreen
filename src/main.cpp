#include <SPI.h>
#include <TFT_eSPI.h>

#define MAX_LINES 8

struct LogLine {
  String text;
  uint16_t color;
};

LogLine lines[MAX_LINES];
String lastRawMessage = ""; // For deduplication

TFT_eSPI tft = TFT_eSPI();

void drawLines() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextSize(2);
  tft.setTextDatum(TL_DATUM); 
  
  for (int i = 0; i < MAX_LINES; i++) {
    if (lines[i].text.length() > 0) {
      tft.setTextColor(lines[i].color, TFT_BLACK);
      tft.drawString(lines[i].text, 0, i * 16);
    }
  }
}

void setup() {
  Serial.begin(115200);
  
  tft.init();
  tft.setRotation(1); 
  tft.fillScreen(TFT_BLACK);

  pinMode(4, OUTPUT);
  digitalWrite(4, HIGH);

  for (int i = 0; i < MAX_LINES; i++) {
    lines[i].text = "";
    lines[i].color = TFT_WHITE;
  }
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input.length() > 0) {
      // Deduplication: ignore if same as previous message
      if (input == lastRawMessage) {
          return;
      }
      lastRawMessage = input;

      uint16_t color = TFT_WHITE;
      String text = input;
      
      if (input.length() >= 2 && input[1] == ':') {
        char c = input[0];
        text = input.substring(2);
        if (c == 'Y') color = TFT_YELLOW;
        else if (c == 'G') color = TFT_GREEN;
        else if (c == 'R') color = TFT_RED;
      }
      
      for (int i = MAX_LINES - 1; i > 0; i--) {
        lines[i] = lines[i - 1];
      }
      
      lines[0].text = text;
      lines[0].color = color;
      
      drawLines();
    }
  }
}
