# 🐾 Mochi (DeskMate) — The Intelligent AI Desktop Pet

Mochi (DeskMate) is a cute, interactive, and highly intelligent virtual desktop pet for macOS (and other platforms). Built on top of **PyQt5** and integrated with a local **Ollama** AI backend, Mochi sits at the bottom-right corner of your desktop, looking around at your cursor, reacting to your activity, managing memory of your accomplishments, and helping you with various system tasks through tool execution.

---

## ✨ Features

- **Transparent Desktop Overlay**: Borderless, translucent PyQt5 window that smoothly stays on top of other applications at the bottom-right corner.
- **Dynamic Animations**: Hand-crafted frame animations for different states: `idle`, `walk`, `sleep`, `typing` (thinking), `eating`, `fall`, and `lie`.
- **Global Input Listener**: Uses `pynput` to listen to global mouse and keyboard activity to track when you are active. 
- **Attention Tracking & Hysteresis-based Head Movement**: Mochi actively tracks the mouse cursor and looks towards it, using a 30px deadband hysteresis threshold to prevent jitter.
- **Smart AI Chat Assistant**: Tap Mochi to open a lovely warm-rose/cream chat drawer. Chat runs token-by-token streaming from a local **Ollama** model.
- **Intelligent Assistant Router & Tool Capabilities**:
  Instead of sending everything to the LLM, Mochi contains an input router that parses queries to execute local tools:
  - 🛠️ **System & Apps**: Launch local applications.
  - 🔋 **Battery Info**: Access system battery level and charging status.
  - 🧮 **Calculator**: Solve mathematical equations.
  - 📋 **Clipboard Manager**: Read/Write to the system clipboard.
  - 📅 **DateTime**: Provide local date/time information.
  - 📁 **File Actions**: Read, search, and list local files.
  - 🧠 **Memory Query**: Query stored personal facts.
  - ⏰ **Reminders**: Schedule alarms and timer alerts.
  - 🔍 **Web Search**: Query DuckDuckGo on-the-fly for real-time information.
  - ☀️ **Weather**: Check local weather details.
- **Hierarchical Memory Engine**:
  - **Working Memory**: Maintains recent chat history.
  - **Semantic Memory**: Analyzes inputs using a policy engine to learn key-value facts about you (e.g. "I love coffee") and saves them.
  - **Episodic Memory**: Automatically tracks your achievements and milestones in a local SQLite database (`mochi_memory.db`).
- **Collapsible Developer Diagnostics**:
  - Press `Ctrl + Shift + D` (or `Cmd + Shift + D` on macOS) in the chat window to toggle a dark-mode developer drawer.
  - View real-time state trees, last route telemetry (latencies, timeline steps), cache hit rate, and UI rendering performance (repaints coalesced, dropped duplicate events).

---

## 🛠️ Installation & Setup

### 1. Clone & Prerequisites

Ensure you have Python 3.8+ and **Ollama** installed on your system. 

If you do not have Ollama installed, download it from [ollama.com](https://ollama.com) and run a model (e.g. `llama3` or `mistral`):
```bash
ollama run llama3
```

### 2. Install Dependencies

Install the required Python libraries using the project's [requirements.txt](file:///Users/aayush/.gemini/antigravity-ide/scratch/desktop_pet/requirements.txt):

```bash
pip install -r requirements.txt
```

### 3. Run Mochi

Start Mochi by running the main entrypoint:

```bash
python main.py
```

*Note: On macOS, Mochi programmatically hides its dock icon so it runs purely as a desktop accessory.*

---

## 📂 Project Architecture

The project is structured modularly:

- [main.py](file:///Users/aayush/.gemini/antigravity-ide/scratch/desktop_pet/main.py): Entrypoint. Initializes the application and applies Cocoa activation policies.
- [pet.py](file:///Users/aayush/.gemini/antigravity-ide/scratch/desktop_pet/pet.py): The visual PyQt5 widget containing animations, physics, global listener integration, and chat window layout.
- [ai_backend.py](file:///Users/aayush/.gemini/antigravity-ide/scratch/desktop_pet/ai_backend.py): AI worker executing asynchronous threads for memory analysis and Ollama streaming.
- [assets.py](file:///Users/aayush/.gemini/antigravity-ide/scratch/desktop_pet/assets.py): Image asset loader and animation metadata parser.
- [listener.py](file:///Users/aayush/.gemini/antigravity-ide/scratch/desktop_pet/listener.py): Manages the global hook for mouse/keyboard inputs via `pynput`.
- [tools.py](file:///Users/aayush/.gemini/antigravity-ide/scratch/desktop_pet/tools.py): Helper scripts and system tools.
- `backends/`: Houses LLM backend wrappers (e.g., local Ollama wrapper).
- `capabilities/`: Subfolders implementing specific tools (Apps, Battery, Reminders, Search, etc.).
- `config/`: Application settings, directories, and logger configuration.
- `database/`: Coordinates connection management for the SQLite memory database.
- `events/`: Implements the attention tracker, behavior engine, and central event bus.
- `memory/`: Houses policies, episodic/semantic memory savers, and relevance scorers.
- `notifications/`: Manages system alerts and alarms.
- `tests/`: Automated unit and integration test suite.

---

## ⚙️ Config & Customization

You can inspect and customize Mochi's settings inside `config/settings.py`. 

- **Animations**: Add custom PNG frames inside `assets/` and update animation configuration.
- **Ollama settings**: Configure Ollama server ports or models if not using the default setup.

---

## 🧪 Tests

To verify stability and routing, run the test suite:

```bash
pytest tests/
```

---

## 📜 License

MIT License. Feel free to customize and expand Mochi as you see fit! 🐾
