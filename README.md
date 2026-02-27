![Python](https://img.shields.io/badge/Python-%3E=3.8-blue)
![License](https://img.shields.io/badge/License-Academic-green)
![Status](https://img.shields.io/badge/Status-Completed-orange)
![Status](https://img.shields.io/badge/Status-Research%20Project-green)

# 📡 Smart TCP File Transfer System with Delta Synchronization

---

## 📌 Overview

This project is a robust client-server file transfer system built using **TCP sockets**, designed as part of Operating Systems / Networking coursework.

The key innovation is **Delta Synchronization (Delta Sync)** — an rsync-style optimization that transmits only the modified blocks of a file instead of re-uploading the entire file.

The system includes:
- Multi-threaded TCP server
- Tkinter-based GUI client
- Real-time Flask monitoring dashboard
- Block-level SHA-256 hashing
- Integrity verification mechanism

---

## 🚀 Key Features

- ✔ Reliable full file upload & download
- ✔ Delta Synchronization (>99% bandwidth savings)
- ✔ Multi-threaded concurrent server
- ✔ Real-time web dashboard (Flask + Chart.js)
- ✔ Block-level integrity validation
- ✔ Custom TCP protocol

---

## 🏗️ System Architecture

Client (GUI / CLI)
↓
TCP Socket Communication
↓
Multi-threaded Server
↓
Delta Comparison Engine
↓
File Reconstruction + Integrity Check
↓
Monitoring Dashboard

---

## 🧠 Delta Synchronization Algorithm

1. File split into 4096-byte blocks  
2. SHA-256 hash computed for each block  
3. Client sends block hashes to server  
4. Server compares against the existing file  
5. Server returns list of missing block indices  
6. Client sends only modified blocks  
7. Server reconstructs the file  
8. Final integrity check using full-file hash  

Result:  
If 4KB changes in 10MB file → only 4KB is transmitted.

---

## 📂 Project Structure

server.py # Main multi-threaded TCP server
client_gui.py # Tkinter-based GUI client
utils.py # Hashing & chunking logic
monitor.py # Thread-safe shared state
dashboard.py # Flask web dashboard
templates/
dashboard.html
files/ # Server storage directory

---

## ⚙️ Technologies Used

- Python
- socket (TCP networking)
- threading (concurrency)
- hashlib (SHA-256 hashing)
- Tkinter (GUI)
- Flask (web dashboard)
- JSON (protocol data)

## 🎓 Academic Context

Developed as part of:
- Operating Systems / Networking coursework
- Client-Server architecture study
- Concurrency & synchronization concepts

## ⚖️ License

This project is intended for academic and educational purposes only.  
See `LICENSE` file for complete terms.
