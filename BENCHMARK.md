# Mochi Desktop Pet Performance Benchmarks
110: 
111: This file tracks the baseline performance measurements for Mochi's hybrid AI assistant architecture.
112: 
113: ## System Footprint
114: * **Memory Usage (RSS):** 28.44 MB
115: * **Idle CPU Usage (Process):** 0.00%
116: 
117: ## Capability Latencies
118: 
119: | Capability / Flow | Type | Iterations | Avg Latency (ms) | Notes |
120: |---|---|---|---|---|
121: | **DateTime** | Local | 50 | 0.05 ms | Pure python datetime fetching |
122: | **Battery Status** | Local | 50 | 9.69 ms | Local pmset parsing & psutil fallback |
123: | **Clipboard** | Local | 50 | 9.75 ms | Reads macOS pbpaste |
124: | **Calculator** | Local | 50 | 0.07 ms | Evaluates sandboxed math expressions |
125: | **App Launcher** | Local | 50 | 0.00 ms | Launches desktop applications (mocked) |
126: | **Weather** | Network | 5 | 1286.51 ms | Open-Meteo API (success: 5/5) |
127: | **DuckDuckGo Search** | Network | 5 | 623.55 ms | DuckDuckGo search library (success: 5/5) |
128: | **Ollama Fallback** | AI Model | 1 | 4.12 ms | Status: Success |
129: 
130: *Generated at 2026-06-28T08:00:00Z*
131: 