# 🐾 DeskMate

> An open-source AI desktop companion with local LLM support, memory, behaviors, animations, and desktop automation.

---

## 🎨 Hero & Demo

![DeskMate Demo](docs/images/demo.gif)
*Placeholder: Demo GIF showing DeskMate sitting on the desktop, walking, and reacting to user interaction.*

![DeskMate Desktop UI](docs/images/screenshot.png)
*Placeholder: Screenshot of the DeskMate character and the chat drawer interface overlay.*

---

## 🛡️ Badges

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey?logo=apple)
![AI: Local LLM](https://img.shields.io/badge/AI-Local%20LLM-blueviolet?logo=ollama)
![Open Source](https://img.shields.io/badge/Open%20Source-%E2%9D%A4-orange)

---

## 📝 Overview

DeskMate is an intelligent desktop companion designed to bring context-aware, local-first utility to your screen. By integrating a background input listener and local AI routing with lightweight PyQt5 interface rendering, DeskMate stays top-of-mind and contextually aware without violating user privacy. 

DeskMate brings together:
*   **Local-First AI**: Zero dependency on external cloud APIs; runs completely on device.
*   **Contextual Memory**: Remembers personal details, milestones, and daily accomplishments.
*   **Proactive Companionship**: Dynamically changes behavior states (such as falling asleep or looking around) based on what you are doing.
*   **System Integration**: Functions as a voice or keyboard command dashboard, executing local utilities like app launches, web searches, reminders, and weather queries.

---

## 🚀 Features

| Core Component | Feature | Current Capability |
| :--- | :--- | :--- |
| **Local LLM Integration** | Offline Assistant | Integrates with local Ollama instances (defaulting to models like `llama3` or `mistral` on port `11434`) for private, local-first chat processing. |
| **Memory System** | Working Memory | Retains the sliding history of the last 20 conversational exchanges to ensure consistent dialogue flow. |
| | Semantic Memory | Dynamically parses queries via a policy engine to extract and persist key-value facts about the user. |
| | Episodic Memory | Logs user accomplishments and notable life events in a dedicated SQLite database (`mochi_memory.db`). |
| **Local Capabilities** | Weather Integration | Resolves queries regarding current and upcoming weather reports dynamically. |
| | Calculator Tool | Safely parses and evaluates mathematical expressions. |
| | Web Search | Queries DuckDuckGo on-the-fly for real-time information. |
| | Clipboard Manager | Programmatically copies responses or reads current system clipboard data. |
| | App Launcher | Launches system applications directly from conversational request matching. |
| | Battery Checker | Reads platform-level battery health, percentage, and charging state. |
| **Reminder System** | Scheduler & Alerts | Schedules specific tasks, alarms, and custom time-based push notifications. |
| **Notification Engine** | Non-Intrusive Overlays | Displays rich, custom styled dialog notifications directly next to the pet. |
| **Response Streaming** | Chunk-by-Chunk Delivery | Streams tokens from Ollama on-the-fly, displaying text in real-time. |
| **Cursor Awareness** | Attention Tracker | Utilizes coordinates to direct the pet's gaze, with deadband hysteresis to keep tracking smooth. |
| **Living Behaviors** | Behavior Engine | Triggers animated states (`idle`, `walk`, `sleep`, `typing`, `eating`, `fall`, `lie`) based on interactive inputs or long idle periods. |
| | Focus Mode | Mutes proactive notifications automatically when the user is actively working/typing. |
| **Diagnostics Panel** | Real-Time Telemetry | Expands into a side drawer (`Ctrl + Shift + D` / `Cmd + Shift + D`) revealing mood, latency breakdown, timeline logs, cache hits, and frame-rate stats. |
| **Response Cache** | Local Latency Buffer | Caches repeated conversational routes and results to execute instantaneous local replies. |
| **Plugin Architecture** | Capability System | Standardized capability base class, allowing swift additions of custom modular tools. |

---

## 🏗️ Architecture

```
User
│
▼
Assistant Router
│
├── Local Capabilities
├── Memory
├── Scheduler
├── Event Bus
└── Ollama Backend
```

The system coordinates background threads (`QThread`) with main thread PyQt5 components. When the user sends a message or triggers an input event, the **Assistant Router** classifies the intent, evaluates whether the query can be resolved locally by any registered **Local Capability** (e.g. system tool or cache lookup), or sends the query to the local **Ollama Backend**. The **Event Bus** manages real-time signals, dispatching behavior transitions and rendering animations to the graphical viewport.

---

## 📂 Folder Structure

```
DeskMate/
├── main.py                 # Application entrypoint & Cocoa setup
├── pet.py                  # PyQt5 widget, animation handling & chat overlay UI
├── ai_backend.py           # Background QThread worker for Ollama integration & memory extraction
├── assets.py               # Image asset manager & animation framework loader
├── listener.py             # Global input event hooking via pynput
├── tools.py                # System utilities and tool helper definitions
├── assistant/              # Core assistant logic
│   ├── router/             # Input classifier, query normalizer/rewriter, and cache
│   ├── session/            # Context resolver and conversation session management
│   ├── state/              # Core state tracking and telemetry channels
│   └── personality/        # Character behavior and text-to-speech placeholders
├── backends/               # LLM connection layers (Local Ollama wrapper)
├── capabilities/           # Modular tool execution units (Weather, Battery, Search, etc.)
├── config/                 # User settings and logging configurations
├── database/               # Local connection pools for SQLite databases
├── events/                 # Attention tracking and behavior scheduler engines
├── memory/                 # Episodic, semantic, working, and policy memory layers
├── notifications/          # Alerts, reminders, and notifications dispatcher
└── services/               # Background task scheduler and telemetry analytics service
```

---

## 📷 Screenshots

### Desktop Pet
![Desktop Pet Placement](docs/images/screenshot_pet.png)
*Placeholder: Visualizing DeskMate anchored to the screen corner.*

### Chat Window
![Chat Interface](docs/images/screenshot_chat.png)
*Placeholder: Chat overlay with customized message bubble styling.*

### Diagnostics Panel
![Developer Diagnostics drawer](docs/images/screenshot_diagnostics.png)
*Placeholder: Split view showing state logs, latency breakdowns, and caching logs.*

### Animation Preview
![Animations List](docs/images/screenshot_animations.png)
*Placeholder: Preview sheets of character frames.*

---

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/AayushAade/DeskMate.git
cd DeskMate
```

### 2. Install Python Dependencies
Install required packages using pip:
```bash
pip install -r requirements.txt
```

### 3. Set Up Ollama
1. Download and install Ollama from [ollama.com](https://ollama.com).
2. Start the Ollama background service.
3. Pull your model of choice (e.g., `llama3` or `mistral`):
   ```bash
   ollama run llama3
   ```

### 4. Run the Application
```bash
python main.py
```

---

## 💻 Requirements

*   **Operating System**: macOS 10.15+ (Darwin-based styling/dock options built-in).
*   **Python Version**: Python 3.8 or higher.
*   **Main Dependencies**:
    *   `PyQt5>=5.15.0`
    *   `pynput>=1.7.6`
    *   `duckduckgo-search>=6.1.7`
*   **Local AI Service**: Ollama running locally at `localhost:11434`.

---

## 🗺️ Roadmap

We are working towards making DeskMate an even more interactive and comprehensive workspace companion:

- [ ] **Cross-Platform Compatibility**: Native support configurations for Windows and Linux.
- [ ] **Expanded Sprite/Animation Sets**: More expressive behaviors, transitions, and interactable states.
- [ ] **Voice Interaction**: Local speech-to-text (STT) and text-to-speech (TTS) pipelines.
- [ ] **Multi-Character Library**: Switch profiles to different pets with unique personalities.
- [ ] **Plugin Marketplace**: Community capabilities and automated tool extensions.
- [ ] **Vision Support**: Enabling DeskMate to analyze active display viewports.
- [ ] **Sound Effects**: Optional spatial audios linked to character behaviors.

---

## 🤝 Contributing

Contributions make the open-source community an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. **Fork** the Project
2. Create your **Feature Branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit** your Changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the Branch (`git push origin feature/AmazingFeature`)
5. Open a **Pull Request**

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 💖 Acknowledgements

*   Inspiration from classic 90s desktop companions and virtual pets.
*   The open-source community for local-first AI wrappers and tool environments.

---

DeskMate is an evolving open-source project focused on building expressive AI desktop companions that feel alive while respecting user privacy through local-first intelligence.
