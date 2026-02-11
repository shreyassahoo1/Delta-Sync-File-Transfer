import threading
import time
from collections import deque

# Shared State
state_lock = threading.Lock()

connected_clients = {}  # {addr_str: {"status": "Connected", "connected_at": timestamp}}
active_transfers = {}   # {filename: {"progress": 0, "speed": "0 KB/s", "mode": "Normal", "size": 0, "sent": 0}}
global_stats = {
    "total_data_sent": 0,
    "total_original_size": 0,
    "bandwidth_saved_bytes": 0
}
logs = deque(maxlen=50) # Keep last 50 logs

def log_event(msg):
    with state_lock:
        timestamp = time.strftime("%H:%M:%S")
        logs.append(f"[{timestamp}] {msg}")
        print(f"[LOG] {msg}")

def add_client(addr):
    with state_lock:
        connected_clients[str(addr)] = {"status": "Connected", "connected_at": time.time()}
    log_event(f"Client connected: {addr}")

def remove_client(addr):
    with state_lock:
        if str(addr) in connected_clients:
            del connected_clients[str(addr)]
    log_event(f"Client disconnected: {addr}")

def update_transfer(filename, sent_bytes, total_bytes, mode="Normal"):
    with state_lock:
        # Calculate speed (simple moving average could be better, but instantaneous for now)
        # For simplicity, we just update state. Speed calc requires tracking time.
        # We'll let the frontend calc speed or do a simple diff if we stored prev state.
        # Let's just store current progress.
        
        progress = (sent_bytes / total_bytes * 100) if total_bytes > 0 else 0
        
        active_transfers[filename] = {
            "progress": progress,
            "speed": "Calculating...", # We need a way to calc speed.
            "mode": mode,
            "sent": sent_bytes,
            "size": total_bytes,
            "last_update": time.time()
        }

def finish_transfer(filename, sent_bytes, original_size):
    with state_lock:
        if filename in active_transfers:
            del active_transfers[filename]
        
        global_stats["total_data_sent"] += sent_bytes
        global_stats["total_original_size"] += original_size
        global_stats["bandwidth_saved_bytes"] += (original_size - sent_bytes)

    saved = original_size - sent_bytes
    log_event(f"Transfer complete: {filename}. Mode: Delta Sync. Saved: {saved/1024:.2f} KB")

def get_snapshot():
    with state_lock:
        # Calc bandwidth saved %
        total_orig = global_stats["total_original_size"]
        saved_bytes = global_stats["bandwidth_saved_bytes"]
        saved_pct = (saved_bytes / total_orig * 100) if total_orig > 0 else 0.0
        
        return {
            "clients": [{"ip": k, **v} for k, v in connected_clients.items()],
            "transfers": [{"filename": k, **v} for k, v in active_transfers.items()],
            "stats": {
                "total_sent_str": f"{global_stats['total_data_sent']/1024/1024:.2f} MB",
                "original_size_str": f"{global_stats['total_original_size']/1024/1024:.2f} MB",
                "bandwidth_saved_percent": round(saved_pct, 2)
            },
            "logs": list(logs)
        }
