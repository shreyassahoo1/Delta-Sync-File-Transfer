# 🚀 Advanced TCP File Transfer System

A robust, multi-threaded client-server application for file management, featuring **Delta Synchronization**, **Real-time Web Dashboard**, **Resumable Downloads**, and **On-the-fly Compression**.

---

## 🌟 Key Features

### 1. **Core Functionality**
- **Robust Upload/Download**: Reliable TCP file transfer protocol with strict handshakes.
- **Multi-Client Support**: Server handles multiple clients simultaneously using threading.
- **Graphical User Interface (GUI)**: Modern `tkinter` interface for easy file management.

### 2. **Innovative Features**
- **⚡ Delta Synchronization** (`rsync`-style):
    - **Smart Sync**: Only transfers modified parts of a file.
    - **Bandwidth Saving**: Can reduce data transfer by **>99%** for small edits to large files.
    - **Toggleable**: Enable/Disable via GUI checkbox.
- **📊 Real-Time Web Dashboard**:
    - **Live Monitoring**: View connected clients and server status at `http://localhost:8000`.
    - **Statistics**: Track total data sent and bandwidth saved by Delta Sync.
- **�️ Secure File Deletion**:
    - **Password Protected**: Deleting files from the server requires admin authentication (Default: `admin`).
    - **Safe**: Prevents accidental or unauthorized removals.

---

## 🛠️ Project Structure

```
OS EL/
├── server.py              # Central Server (TCP + Flask Dashboard via Threading)
├── client_gui.py          # Modern GUI Client (Recommended)
├── client.py              # Legacy CLI Client
├── dashboard.py           # Flask Backend for Web Monitor
├── monitor.py             # Shared State Manager
├── utils.py               # Hashing & Chunking Logic
├── templates/             # HTML Templates
│   └── dashboard.html     # Dashboard Frontend
└── files/                 # Server Storage
```

---

## 🚀 How to Run

### Prerequisites
- Python 3.6+
- Libraries: `flask` (install via `pip install flask`)

### Step 1: Start the Server
First, launch the server. It will create the `files/` directory and start the Web Dashboard.
```powershell
python server.py
```
> Output:
> `[+] Server is listening on port 5001...`
> `[+] Dashboard running on http://localhost:8000`

### Step 2: Open the Web Dashboard
Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

### Step 3: Run the Client
Open a new terminal to run the GUI client.
```powershell
python client_gui.py
```

---

## 📚 Feature Usage Guide

### ⚡ Using Delta Sync
1.  Connect to the server.
2.  Ensure "Delta Sync" checkbox is **checked**.
3.  Select a file that already exists on the server (but has local changes).
4.  Click **Upload**.
5.  Watch the logs! You'll see "Bandwidth saved: 99.5%" instead of a full re-upload.

### 🗑️ Deleting Files
1.  Select a file from the server list.
2.  Click **Delete Selected**.
3.  Enter the admin password: **`admin`**.
4.  The file is securely removed.

---

## ⚙️ Technical Details
- **Protocol**: Custom binary protocol with `CMD -> ACK -> SIZE -> ACK -> DATA` handshake.
- **Delta Algorithm**: Block-level SHA-256 hashing (4KB chunks).
- **Web Stack**: Flask (Backend) + Vanilla JS/HTML (Frontend) + Chart.js.
- **Port**: 5001 (TCP), 8000 (HTTP).

---
*Created for OS/Networks Project*
