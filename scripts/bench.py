import time
import subprocess
import os

mock_json = '{"event": "test", "data": "mock_data", "timestamp": "2026-05-16T12:00:00Z"}'
script_dir = os.path.dirname(os.path.abspath(__file__))
py_hook = os.path.join(script_dir, "hook.py")
rust_hook = os.path.join(script_dir, "rust_hook", "target", "release", "rust_hook")

def benchmark(cmd, n=200):
    start = time.time()
    for _ in range(n):
        # Запускаем скрипт, передавая mock_json через stdin
        subprocess.run(cmd, input=mock_json, text=True, capture_output=True)
    end = time.time()
    return end - start

print("Starting Benchmark: Python vs Rust Hook")
print("=" * 40)
print(f"Mock Data: {mock_json}")
print(f"Iterations: 200")
print("-" * 40)

print(f"Benchmarking Python hook...")
py_time = benchmark(["python3", py_hook])

print(f"Benchmarking Rust hook...")
rust_time = benchmark([rust_hook])

print("=" * 40)
print("RESULTS:")
print(f"Python hook (200 runs): {py_time:.4f} seconds ({py_time/200*1000:.2f} ms/run)")
print(f"Rust hook (200 runs):   {rust_time:.4f} seconds ({rust_time/200*1000:.2f} ms/run)")
if rust_time > 0:
    print(f"Performance Gain:       Rust is {py_time/rust_time:.2f}x faster!")
print("=" * 40)
