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
    
    // Строка 1: Буква + Папка (Белый)
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    char buf[21];
    snprintf(buf, 21, "%c:[%s]", widgets[i].letter, widgets[i].folder.substring(0, 16).c_str());
    tft.drawString(buf, 0, y_start);
    
    // Строка 2: Статус (Цветной)
    tft.setTextColor(widgets[i].color, TFT_BLACK);
    String st = widgets[i].status.substring(0, 20);
    tft.drawString(st, 0, y_start + 16);
    
    // Разделительная линия
    tft.drawFastHLine(0, y_start + 32, 240, 0x1082); 
  }
}

void updateAgent(char letter, uint16_t color, String status, String folder) {
  int foundIdx = -1;
  for (int i = 0; i < MAX_WIDGETS; i++) {
    if (widgets[i].active && widgets[i].letter == letter) {
      foundIdx = i;
      break;
    }
  }

  AgentWidget updated;
  updated.letter = letter;
  updated.color = color;
  updated.status = status;
  updated.folder = folder;
  updated.active = true;

  if (foundIdx != -1) {
    // Двигаем все вниз до найденного
    for (int j = foundIdx; j > 0; j--) {
      widgets[j] = widgets[j-1];
    }
  } else {
    // Новый: двигаем все вниз, вытесняя последнего
    for (int j = MAX_WIDGETS - 1; j > 0; j--) {
      widgets[j] = widgets[j-1];
    }
  }
  
  widgets[0] = updated;
  drawInterface();
}

void setup() {
  Serial.begin(115200);
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  pinMode(4, OUTPUT);
  digitalWrite(4, HIGH);
  Serial.println("ESP32 Status Monitor Started");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input.length() > 5) {
      // Формат: Letter:ColorCode:Status:Folder
      // Пример: A:G:AfterModel:Folder
      int c1 = input.indexOf(':');
      int c2 = input.indexOf(':', c1 + 1);
      int c3 = input.indexOf(':', c2 + 1);
      
      if (c1 == 1 && c2 != -1 && c3 != -1) {
        char letter = input[0];
        char colorCode = input[c1 + 1];
        String status = input.substring(c2 + 1, c3);
        String folder = input.substring(c3 + 1);
        
        uint16_t color = TFT_WHITE;
        if (colorCode == 'Y') color = TFT_YELLOW;
        else if (colorCode == 'G') color = TFT_GREEN;
        else if (colorCode == 'R') color = TFT_RED;
        else if (colorCode == 'B') color = TFT_BLUE;

        updateAgent(letter, color, status, folder);
      }
    }
  }
}
