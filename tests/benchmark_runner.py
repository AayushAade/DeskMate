import os
import time
import psutil
from assistant.router.router import AssistantRouter
from capabilities.base_capability import Intent
from services import app_service

def run_benchmarks():
    print("==================================================")
    print("           MOCHI SYSTEM BENCHMARKS                ")
    print("==================================================")
    
    p = psutil.Process(os.getpid())
    
    # 1. Measure Memory Usage
    mem_rss = p.memory_info().rss / (1024 * 1024)  # Convert to MB
    print(f"Memory Usage (RSS): {mem_rss:.2f} MB")
    
    # 2. Measure Idle CPU Usage (sampled over 1 second)
    p.cpu_percent(interval=None) # priming
    time.sleep(1.0)
    cpu_usage = p.cpu_percent(interval=None)
    print(f"Idle CPU Usage (Process): {cpu_usage:.2f}%")
    
    router = AssistantRouter()
    
    # 3. Benchmark Calculator (50 iterations)
    start_time = time.time()
    calc_cap = router.capabilities[6]  # CalculatorCapability
    for _ in range(50):
        calc_cap.execute({"expression": "47*92 + sqrt(144)"})
    calc_avg = ((time.time() - start_time) / 50) * 1000  # ms
    print(f"Calculator Avg Latency (Local): {calc_avg:.2f} ms")
    
    # 4. Benchmark App Launcher (50 iterations - Mocked)
    original_launch = app_service.launch_app
    app_service.launch_app = lambda name: (True, "Visual Studio Code", "mock success")
    
    start_time = time.time()
    apps_cap = router.capabilities[7]  # AppsCapability
    for _ in range(50):
        apps_cap.execute({"app_name": "vs code"})
    apps_avg = ((time.time() - start_time) / 50) * 1000  # ms
    app_service.launch_app = original_launch
    print(f"App Launcher Avg Latency (Local): {apps_avg:.2f} ms")
    
    # 5. Benchmark DateTime (50 iterations)
    start_time = time.time()
    dt_cap = router.capabilities[0]  # DateTimeCapability
    for _ in range(50):
        dt_cap.execute({})
    dt_avg = ((time.time() - start_time) / 50) * 1000  # ms
    print(f"DateTime Avg Latency (Local): {dt_avg:.2f} ms")
    
    # 6. Benchmark Battery Status (50 iterations)
    start_time = time.time()
    batt_cap = router.capabilities[1]  # BatteryCapability
    for _ in range(50):
        batt_cap.execute({})
    batt_avg = ((time.time() - start_time) / 50) * 1000  # ms
    print(f"Battery Status Avg Latency (Local): {batt_avg:.2f} ms")
    
    # 7. Benchmark Clipboard (50 iterations)
    start_time = time.time()
    clip_cap = router.capabilities[2]  # ClipboardCapability
    for _ in range(50):
        clip_cap.execute({})
    clip_avg = ((time.time() - start_time) / 50) * 1000  # ms
    print(f"Clipboard Avg Latency (Local): {clip_avg:.2f} ms")
    
    # 8. Benchmark Weather (5 iterations - Real Network Calls)
    start_time = time.time()
    weather_cap = router.capabilities[4]  # WeatherCapability
    weather_success = 0
    for _ in range(5):
        res = weather_cap.execute({"city": "San Francisco"})
        if res.success:
            weather_success += 1
    weather_avg = ((time.time() - start_time) / 5) * 1000  # ms
    print(f"Weather API Avg Latency (Network): {weather_avg:.2f} ms (Success rate: {weather_success}/5)")
    
    # 9. Benchmark Search (5 iterations - Real Network Calls)
    start_time = time.time()
    search_cap = router.capabilities[5]  # SearchCapability
    search_success = 0
    for _ in range(5):
        res = search_cap.execute({"query": "AI news"})
        if res.success:
            search_success += 1
    search_avg = ((time.time() - start_time) / 5) * 1000  # ms
    print(f"DuckDuckGo Search Avg Latency (Network): {search_avg:.2f} ms (Success rate: {search_success}/5)")
    
    # 10. Benchmark Ollama / LLM Fallback (1 iteration)
    start_time = time.time()
    ollama_status = "Success"
    ollama_latency = 0.0
    try:
        # We perform a route that falls back to LLM (no matching capability)
        # Note: if Ollama is not running, we catch the exception and print connection error latency
        res = router.route_and_execute("Explain neural networks in one sentence", [])
        ollama_latency = (time.time() - start_time) * 1000
        print(f"Ollama Fallback Latency: {ollama_latency:.2f} ms")
    except Exception as e:
        ollama_latency = (time.time() - start_time) * 1000
        ollama_status = f"Offline / Failed ({e})"
        print(f"Ollama Fallback Latency (Failed): {ollama_latency:.2f} ms (Status: {ollama_status})")
        
    # Write to BENCHMARK.md
    benchmark_md = f"""# Mochi Desktop Pet Performance Benchmarks

This file tracks the baseline performance measurements for Mochi's hybrid AI assistant architecture.

## System Footprint
* **Memory Usage (RSS):** {mem_rss:.2f} MB
* **Idle CPU Usage (Process):** {cpu_usage:.2f}%

## Capability Latencies

| Capability / Flow | Type | Iterations | Avg Latency (ms) | Notes |
|---|---|---|---|---|
| **DateTime** | Local | 50 | {dt_avg:.2f} ms | Pure python datetime fetching |
| **Battery Status** | Local | 50 | {batt_avg:.2f} ms | Local pmset parsing & psutil fallback |
| **Clipboard** | Local | 50 | {clip_avg:.2f} ms | Reads macOS pbpaste |
| **Calculator** | Local | 50 | {calc_avg:.2f} ms | Evaluates sandboxed math expressions |
| **App Launcher** | Local | 50 | {apps_avg:.2f} ms | Launches desktop applications (mocked) |
| **Weather** | Network | 5 | {weather_avg:.2f} ms | Open-Meteo API (success: {weather_success}/5) |
| **DuckDuckGo Search** | Network | 5 | {search_avg:.2f} ms | DuckDuckGo search library (success: {search_success}/5) |
| **Ollama Fallback** | AI Model | 1 | {ollama_latency:.2f} ms | Status: {ollama_status} |

*Generated at 2026-06-28T08:00:00Z*
"""
    
    with open("BENCHMARK.md", "w") as f:
        f.write(benchmark_md)
        
    print("\nBenchmarks saved to BENCHMARK.md successfully!")

if __name__ == "__main__":
    run_benchmarks()
