# Проект AgentStatuser: Система мониторинга Gemini CLI на ESP32

## Архитектура решения
Система построена на событийно-ориентированной модели (Producer-Consumer) для исключения блокировок основного процесса Gemini:
1. **Hooks (Producer):** Gemini CLI вызывает `scripts/hook.py` при наступлении событий.
2. **Broker (Redis):** Docker-контейнер `gemini-redis` (порт 6379) принимает JSON-события через очередь `gemini_events`.
3. **Bridge (Consumer):** Фоновый процесс `scripts/bridge.py` читает Redis, определяет проектную папку по PPID и пересылает данные в Serial.
4. **Display (ESP32):** Плата LilyGo TTGO T-Display отображает до 4-х виджетов (по 2 строки на агента).

## Протокол передачи (Serial)
Данные передаются в формате: `@L:C:Folder:Status#`
- **Маркеры:** `@` (старт), `#` (конец).
- **L (Letter):** Идентификатор агента (A, B, C...). Буква `G` зарезервирована.
- **C (Color Code):**
  - `B` (Blue): Ready / SessionStart.
  - `Y` (Yellow): BeforeModel / BeforeTool.
  - `G` (Green): AfterModel.
  - `R` (Red): ToolPermission / Errors.
  - `K` (Kill): Удаление виджета (SessionEnd).
- **Folder:** Имя рабочей директории процесса.
- **Status:** Текст события.

## Файловая структура
- `src/main.cpp`: Прошивка (Arduino/C++). Логика статических виджетов.
- `scripts/hook.py`: Оптимизированный хук (Raw Socket RESP).
- `scripts/bridge.py`: Python-мост с дедупликацией и маппингом PPID.
- `platformio.ini`: Настройки сборки и пинов TFT_eSPI.

## Правила работы
1. При изменении прошивки всегда сохранять обратную совместимость с протоколом `@L:C:Folder:Status#`.
2. Перед обновлением `bridge.py` убивать старый процесс через `pkill -f bridge.py`.
3. Всегда проверять наличие запущенного контейнера Redis: `docker ps`.
