# Mochi Desktop Pet Performance Benchmarks

This file tracks the baseline performance measurements for Mochi's hybrid AI assistant architecture.

## System Footprint
* **Memory Usage (RSS):** 28.09 MB
* **Idle CPU Usage (Process):** 0.00%

## Capability Latencies

| Capability / Flow | Type | Iterations | Avg Latency (ms) | Notes |
|---|---|---|---|---|
| **DateTime** | Local | 50 | 0.01 ms | Pure python datetime fetching |
| **Battery Status** | Local | 50 | 8.71 ms | Local pmset parsing & psutil fallback |
| **Clipboard** | Local | 50 | 9.16 ms | Reads macOS pbpaste |
| **Calculator** | Local | 50 | 0.02 ms | Evaluates sandboxed math expressions |
| **App Launcher** | Local | 50 | 0.00 ms | Launches desktop applications (mocked) |
| **Weather** | Network | 5 | 1413.97 ms | Open-Meteo API (success: 5/5) |
| **DuckDuckGo Search** | Network | 5 | 535.84 ms | DuckDuckGo search library (success: 5/5) |
| **Ollama Fallback** | AI Model | 1 | 15035.20 ms | Status: Success |

*Generated at 2026-06-28T08:00:00Z*
