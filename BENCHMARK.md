# Mochi Desktop Pet Performance Benchmarks

This file tracks the baseline performance measurements for Mochi's hybrid AI assistant architecture.

## System Footprint
* **Memory Usage (RSS):** 29.91 MB
* **Idle CPU Usage (Process):** 0.00%

## Capability Latencies

| Capability / Flow | Type | Iterations | Avg Latency (ms) | Notes |
|---|---|---|---|---|
| **DateTime** | Local | 50 | 0.00 ms | Pure python datetime fetching |
| **Battery Status** | Local | 50 | 0.01 ms | Local pmset parsing & psutil fallback |
| **Clipboard** | Local | 50 | 9.25 ms | Reads macOS pbpaste |
| **Calculator** | Local | 50 | 0.00 ms | Evaluates sandboxed math expressions |
| **App Launcher** | Local | 50 | 0.24 ms | Launches desktop applications (mocked) |
| **Weather** | Network | 5 | 0.00 ms | Open-Meteo API (success: 0/5) |
| **DuckDuckGo Search** | Network | 5 | 910.47 ms | DuckDuckGo search library (success: 5/5) |
| **Ollama Fallback** | AI Model | 1 | 14035.07 ms | Status: Success |

*Generated at 2026-06-28T08:00:00Z*
