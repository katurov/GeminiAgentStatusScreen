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

    int y_start = i * (16 * 2 + 1); // 2 строки по 16px + 1px разделитель
    
    // Строка 1: Буква + Папка
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    String header = String(widgets[i].letter) + ":[" + widgets[i].folder + "]";
    if (header.length() > 20) header = header.substring(0, 19) + "]";
    tft.drawString(header, 0, y_start);
    
    // Строка 2: Статус (цветной)
    tft.setTextColor(widgets[i].color, TFT_BLACK);
    String statusText = widgets[i].status;
    if (statusText.length() > 20) statusText = statusText.substring(0, 20);
    tft.drawString(statusText, 0, y_start + 16);
    
    // Разделительная линия (опционально, 1 пиксель пропуска)
    if (i < MAX_WIDGETS - 1) {
       tft.drawFastHLine(0, y_start + 32, 240, 0x1082); // Темно-серый разделитель
    }
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
    // Сдвигаем все виджеты до найденного вниз
    for (int i = foundIdx; i > 0; i--) {
      widgets[i] = widgets[i - 1];
    }
  } else {
    // Если новый агент — сдвигаем все вниз, вытесняя последнего
    for (int i = MAX_WIDGETS - 1; i > 0; i--) {
      widgets[i] = widgets[i - 1];
    }
  }
  // Ставим обновленный/новый на первое место
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
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input.length() > 5) {
      // Формат: Letter:C:Status:Folder
      // Пример: A:G:AfterModel:AgentStatuser
      int firstColon = input.indexOf(':');
      int secondColon = input.indexOf(':', firstColon + 1);
      int thirdColon = input.indexOf(':', secondColon + 1);
      
      if (firstColon != -1 && secondColon != -1 && thirdColon != -1) {
        char letter = input[0];
        char colorCode = input[firstColon + 1];
        String status = input.substring(secondColon + 1, thirdColon);
        String folder = input.substring(thirdColon + 1);
        
        uint16_t color = TFT_WHITE;
        if (colorCode == 'Y') color = TFT_YELLOW;
        else if (colorCode == 'G') color = TFT_GREEN;
        else if (colorCode == 'R') color = TFT_RED;
        
        updateAgent(letter, color, status, folder);
      }
    }
  }
}
