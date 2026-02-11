# Smart TCP File Transfer System with Delta Synchronization

## 1. Project Overview
This project is a sophisticated file transfer application built typically for Operating Systems or Networking coursework. It implements a robust **Client-Server Architecture** using TCP sockets. The core innovation is the **Delta Synchronization** (Delta Sync) feature, which minimizes bandwidth usage by transmitting only the modified parts of a file.

The system also includes a multi-threaded server, a GUI client, and a real-time web-based monitoring dashboard.

## 2. Key Features
- **Reliable File Transfer**: Supports full file uploads and downloads over TCP.
- **Delta Synchronization**: Implements "rsync-style" differential updates. If a file exists on the server, only changed blocks are sent.
- **Graphical User Interface (GUI)**: A modern Tkinter-based client for easy operation.
- **Web Dashboard**: A real-time monitoring panel (Flask + Chart.js) displaying active transfers, connected clients, and bandwidth savings.
- **Concurrency**: The server handles multiple clients simultaneously using Python `threading`.

## 3. System Architecture
The system consists of three main components:

### 3.1. Server (`server.py`)
- **Role**: Central repository and coordinator.
- **Responsibilities**:
  - Listens on Port 5001.
  - Spawns a new thread for each client connection.
  - manages file storage in `files/` directory.
  - Orchestrates Delta Sync comparison logic.
  - Hosts the Flask Dashboard on Port 8000 (background thread).

### 3.2. Client (`client.py` / `client_gui.py`)
- **Role**: End-user interface to transfer files.
- **Responsibilities**:
  - Connects to Server.
  - Generates block-level hashes for local files.
  - Sends commands (`UPLOAD`, `DOWNLOAD`, `UPLOAD_DELTA`).
  - Displays progress and logs.

### 3.3. Web Dashboard (`dashboard.py` + `templates/dashboard.html`)
- **Role**: Visualization and Monitoring.
- **Responsibilities**:
  - Fetches real-time state from `monitor.py` (Shared State).
  - Renders live graphs for bandwidth savings and transfer progress.

## 4. Technical Implementation Details

### 4.1. Delta Synchronization Algorithm
The most critical part of the project is the bandwidth-saving algorithm:

1.  **Chunking**: The file is split into fixed-size blocks (Default: **4096 bytes**).
2.  **Hashing**: The client computes the **SHA-256** hash for each block (`utils.py`).
3.  **Handshake**:
    - Client sends `UPLOAD_DELTA filename`.
    - Client sends the list of all block hashes.
4.  **Comparison (Server-Side)**:
    - Server computes hashes for its existing version of the file.
    - Server compares Client Hashes vs. Server Hashes.
    - Server identifies indices where hashes simply do not match.
5.  **Selective Transfer**:
    - Server responds with `MISSING_BLOCKS` (a list of indices).
    - Client sends **only** the data for these specific blocks.
6.  **Reconstruction**:
    - Server creates a temporary copy of the file.
    - Server overwrites the specific blocks with new data.
    - **Integrity Check**: Server re-hashes the new file and verifies it matches the Client's full file hash.

### 4.2. Communication Protocol
The system uses a custom text/binary hybrid protocol over TCP.

| Command | Direction | Description |
| :--- | :--- | :--- |
| `UPLOAD <filename>` | C -> S | Initiates full file upload. |
| `UPLOAD_DELTA <filename>` | C -> S | Initiates smart sync. |
| `LIST` | C -> S | Requests list of files. |
| `DOWNLOAD <filename>` | C -> S | Requests file download. |
| `ACK`, `OK` | S -> C | Acknowledgments. |
| `MISSING_BLOCKS` | S -> C | JSON list of blocks needed. |
| `INTEGRITY_OK` | S -> C | Final success confirmation. |

### 4.3. Code Structure
- **`server.py`**: Main server entry point.
- **`client_gui.py`**: GUI Client entry point.
- **`utils.py`**: Shared logic for file chunking and hashing.
- **`monitor.py`**: Thread-safe state management for statistics.
- **`dashboard.py`**: Flask application for the web interface.

## 5. Performance & Impact
- **Scenario**: Modifying 1 small part of a large file (e.g., 10MB).
- **Without Delta Sync**: Re-uploading takes 10MB.
- **With Delta Sync**: Only the changed 4KB block is sent.
- **Result**: **>99% Bandwidth Saving**.

## 6. Libraries Used
- **Socket**: Core networking.
- **Threading**: Concurrency.
- **Hashlib**: SHA-256 hashing.
- **Tkinter**: GUI.
- **Flask**: Web Server.
- **JSON**: Data serialization.
