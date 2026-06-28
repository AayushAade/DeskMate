# Mochi Desktop Pet Performance Benchmarks

This file tracks the baseline performance measurements for Mochi's hybrid AI assistant architecture.

## System Footprint
* **Memory Usage (RSS):** 29.31 MB
* **Idle CPU Usage (Process):** 0.00%

## Capability Latencies

| Capability / Flow | Type | Iterations | Avg Latency (ms) | Notes |
|---|---|---|---|---|
| **DateTime** | Local | 50 | 0.01 ms | Pure python datetime fetching |
| **Battery Status** | Local | 50 | 8.91 ms | Local pmset parsing & psutil fallback |
| **Clipboard** | Local | 50 | 8.71 ms | Reads macOS pbpaste |
| **Calculator** | Local | 50 | 0.08 ms | Evaluates sandboxed math expressions |
| **App Launcher** | Local | 50 | 0.01 ms | Launches desktop applications (mocked) |
| **Weather** | Network | 5 | 1256.43 ms | Open-Meteo API (success: 5/5) |
| **DuckDuckGo Search** | Network | 5 | 688.12 ms | DuckDuckGo search library (success: 5/5) |
| **Ollama Fallback** | AI Model | 1 | 22602.39 ms | Status: Success |

*Generated at 2026-06-28T08:00:00Z*
