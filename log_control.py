import sys
import time
import csv
import os
import logging

# Disable background logging to prevent file locks with the GUI
logging.disable(logging.CRITICAL)

sys.path.insert(0, "linien-client")
from linien_client.device import Device
from linien_client.connection import LinienClient

print("Connecting to Red Pitaya at 192.168.100.2...", flush=True)

device = Device(host="192.168.100.2")
client = LinienClient(device)
client.connect(autostart_server=False, use_parameter_cache=False)

temp_file = "_temp_recording.csv"
poll_interval = 0.5

print("Connected successfully!", flush=True)
print("Recording live data...")
print("Press Ctrl+C when done to stop and name your file.\n", flush=True)

seen_timestamps = set()
total_written = 0
t_zero = None  # Will be set to the very first timestamp from the Red Pitaya
last_status = 0
t_start_local = time.time()

with open(temp_file, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["time /s", "control_signal /s", "is_locked"])
    
    try:
        initial_hist = client.parameters.control_signal_history.value
        seen_timestamps = set(initial_hist.get("times", []))  # Ignore old points already in memory
        while True:
            is_locked = int(bool(client.parameters.lock.value))
            
            hist = client.parameters.control_signal_history.value
            times = hist.get("times", [])
            values = hist.get("values", [])
            
            batch_count = 0
            for t_pt, v_pt in zip(times, values):
                if t_pt not in seen_timestamps:
                    seen_timestamps.add(t_pt)
                    
                    # Establish t = 0 based strictly on the Red Pitaya's own clock
                    if t_zero is None:
                        t_zero = t_pt
                        
                    rel_time = t_pt - t_zero
                    v_volts = v_pt / 8192.0  # Or apply your specific calibration factor
                    writer.writerow([f"{rel_time:.3f}", f"{v_volts:.4f}", is_locked])
                    batch_count += 1
            
            if batch_count > 0:
                f.flush()
                total_written += batch_count
            
            elapsed = time.time() - t_start_local
            if elapsed - last_status >= 2.0:
                state_str = "LOCKED" if is_locked else "UNLOCKED"
                print(f"Elapsed: {elapsed:6.1f} s | Total Points: {total_written:6d} | Loop: {state_str}", flush=True)
                last_status = elapsed
                
            time.sleep(poll_interval)
            
    except KeyboardInterrupt:
        print("\n\nRecording stopped!")

if total_written == 0:
    print("No data points were recorded.")
    if os.path.exists(temp_file):
        os.remove(temp_file)
else:
    default_name = f"control_trace_{int(time.time())}.csv"
    user_name = input(f"Enter filename to save [default: {default_name}]: ").strip()
    
    if not user_name:
        final_filename = default_name
    else:
        final_filename = user_name if user_name.lower().endswith(".csv") else f"{user_name}.csv"
        
    if os.path.exists(final_filename):
        overwrite = input(f"'{final_filename}' already exists. Overwrite? (y/n): ").strip().lower()
        if overwrite != "y":
            final_filename = f"copy_{final_filename}"
            
    os.replace(temp_file, final_filename)
    print(f"Successfully saved {total_written} points to '{final_filename}'.")