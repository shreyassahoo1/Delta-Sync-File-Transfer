# 🏗️ System Architecture

## 1. Overview

The Smart TCP File Transfer System follows a modular client–server architecture with delta synchronization optimization.

The system consists of:

- Multi-threaded TCP Server
- GUI / CLI Client
- Delta Sync Engine
- Monitoring Module
- Web Dashboard (Flask)

---

## 2. High-Level Architecture

Client (GUI / CLI)
│
▼
TCP Socket Communication
│
▼
Multi-threaded Server
│
├── Full File Transfer Handler
├── Delta Sync Engine
├── Integrity Validator
└── Monitoring Module
│
▼
Flask Dashboard (Port 8000)

---

## 3. Component Breakdown

### 3.1 Server (`server.py`)

- Listens on TCP Port 5000
- Spawns new thread per client
- Manages file storage in `files/`
- Handles commands:
  - UPLOAD
  - DOWNLOAD
  - UPLOAD_DELTA
  - LIST
- Coordinates delta comparison

Concurrency Model:
Each client connection is handled in a separate thread to ensure scalability.

---

### 3.2 Client (`client_gui.py`)

- Connects to server via TCP
- Generates block hashes
- Sends synchronization commands
- Displays transfer progress

---

### 3.3 Delta Sync Engine

Core Optimization Logic:

- File chunked into 4096-byte blocks
- SHA-256 hash computed per block
- Server compares hash lists
- Only mismatched blocks are transferred
- File reconstructed server-side

---

### 3.4 Monitoring Module (`monitor.py`)

- Thread-safe shared state
- Tracks:
  - Active clients
  - Data transferred
  - Bandwidth saved
- Supplies data to Flask dashboard

---

### 3.5 Web Dashboard (`dashboard.py`)

- Flask-based web server
- Visualizes:
  - Active transfers
  - Client connections
  - Bandwidth savings
- Real-time stats display

---

## 4. Design Principles

- Modularity
- Separation of concerns
- Concurrency support
- Bandwidth efficiency
- Integrity verification
- Observability (dashboard)

---

## 5. Scalability Considerations

- Thread-based concurrency
- Optimized delta transfer
- Minimal redundant data transmission
- Extendable to SSL/TLS encryption

---

## 6. Future Architecture Improvements

- AsyncIO-based concurrency
- Encrypted file transfer (SSL)
- Cloud-based deployment
- Persistent metadata storage
