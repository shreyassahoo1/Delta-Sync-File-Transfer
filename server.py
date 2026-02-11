import socket
import threading
import os
import zlib
import json
import shutil
import utils
import monitor

# Prevent Flask from loading .env file to avoid permission errors
os.environ['FLASK_SKIP_DOTENV'] = '1'

import dashboard

def handle_client(client_socket, address):
    print(f"[+] New connection from {address}")
    while True:
        try:
            data = client_socket.recv(1024).decode()
            if not data:
                break

            parts = data.split()
            if not parts:
                continue

            cmd = parts[0]

            # LIST
            if cmd == "LIST":
                files = os.listdir("files")
                client_socket.send(("\n".join(files) if files else "No files found").encode())

            # UPLOAD filename
            elif cmd == "UPLOAD":
                if len(parts) < 2:
                    continue
                filename = parts[1]
                
                # PROTOCOL:
                # 1. Recv UPLOAD filename
                # 2. Send OK
                # 3. Recv Size
                # 4. Send OK
                # 5. Recv Data

                client_socket.send(b"OK")  # ACK the command

                filesize_str = client_socket.recv(1024).decode()
                try:
                    filesize = int(filesize_str)
                    client_socket.send(b"OK") # ACK the size
                    
                    # Receive file data
                    bytes_received = 0
                    file_path = os.path.join("files", filename)
                    with open(file_path, "wb") as f:
                        while bytes_received < filesize:
                            chunk_size = 4096
                            remaining = filesize - bytes_received
                            if remaining < chunk_size:
                                chunk_size = remaining
                            
                            chunk = client_socket.recv(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            bytes_received += len(chunk)
                    
                    print(f"Received file: {filename}")
                    monitor.log_event(f"Recv Complete: {filename}")
                    monitor.finish_transfer(filename, filesize, filesize)
                    
                except ValueError:
                    print("Invalid file size received")
                    client_socket.send(b"ERROR_INVALID_SIZE")

            # UPLOAD_DELTA filename
            elif cmd == "UPLOAD_DELTA":
                if len(parts) < 2:
                    continue
                filename = parts[1]
                file_path = os.path.join("files", filename)
                
                # Check if we have the file
                if not os.path.exists(file_path):
                    client_socket.send(b"FULL_UPLOAD_REQUIRED")
                    continue
                
                client_socket.send(b"ACK") # Ready for hash list
                
                # Recv Hash List (Length prefixed)
                json_len_data = client_socket.recv(10).decode().strip()
                try:
                    json_len = int(json_len_data)
                    client_socket.send(b"OK")
                    
                    json_data = b""
                    while len(json_data) < json_len:
                         chunk = client_socket.recv(min(4096, json_len - len(json_data)))
                         if not chunk: break
                         json_data += chunk
                    
                    client_state = json.loads(json_data.decode())
                    client_total_blocks = client_state["total_blocks"]
                    client_hashes = client_state["hashes"]
                    client_final_hash = client_state["file_hash"]
                    
                    print(f"[Delta Sync] Client wants to sync {filename}")
                    monitor.log_event(f"Delta Sync Request: {filename}")
                    
                    print(f"[Delta Sync] Comparing hashes...")
                    monitor.log_event(f"Comparing hashes for {filename}...")
                    
                    server_total, server_hashes, server_final_hash = utils.get_file_block_hashes(file_path)
                    
                    missing_blocks = []
                    for i in range(client_total_blocks):
                        if i >= len(server_hashes) or server_hashes[i] != client_hashes[i]:
                            missing_blocks.append(i)
                            
                    print(f"[Delta Sync] Need to receive {len(missing_blocks)} blocks")
                    monitor.log_event(f"{filename}: {len(missing_blocks)} blocks missing")
                    
                    # Send MISSING_BLOCKS
                    response = json.dumps({"missing": missing_blocks})
                    response_bytes = response.encode()
                    client_socket.send(str(len(response_bytes)).encode().ljust(10)) 
                    client_socket.send(response_bytes)
                    
                    if not missing_blocks:
                         print("[Delta Sync] No blocks needed. Verifying integrity...")
                         if server_final_hash == client_final_hash:
                              client_socket.send(b"INTEGRITY_OK")
                              print("[Delta Sync] File already up to date and verified.")
                              monitor.log_event(f"{filename} already up to date")
                         else:
                              pass 
                    
                    # Ready to receive blocks
                    temp_path = file_path + ".tmp"
                    shutil.copy2(file_path, temp_path)
                    
                    received_delta_bytes = 0
                    total_missing_bytes = len(missing_blocks) * utils.BLOCK_SIZE # approx
                    
                    with open(temp_path, "r+b") as f:
                        for idx in missing_blocks:
                            # Recv Header: Index (4) + Size (4)
                            header = client_socket.recv(8)
                            if not header or len(header) < 8:
                                break
                            
                            blk_idx = int.from_bytes(header[:4], 'big')
                            blk_len = int.from_bytes(header[4:], 'big')
                            
                            # Recv Data
                            blk_data = b""
                            while len(blk_data) < blk_len:
                                chunk = client_socket.recv(min(4096, blk_len - len(blk_data)))
                                if not chunk: break
                                blk_data += chunk
                            
                            # Write to temp file
                            f.seek(blk_idx * utils.BLOCK_SIZE)
                            f.write(blk_data)
                            
                            received_delta_bytes += blk_len
                            monitor.update_transfer(filename, received_delta_bytes, total_missing_bytes, mode="Delta Sync")
                            
                            # ACK per block
                            client_socket.send(b"ACK")

                    # Integrity Check
                    _, _, new_server_hash = utils.get_file_block_hashes(temp_path)
                    
                    if new_server_hash == client_final_hash:
                        client_socket.send(b"INTEGRITY_OK")
                        print("[Delta Sync] Integrity verification successful.")
                        
                        saved_percent = 100 * (1 - (len(missing_blocks) * utils.BLOCK_SIZE) / (client_total_blocks * utils.BLOCK_SIZE or 1))
                        print(f"[Delta Sync] Bandwidth saved: {saved_percent:.1f}%")
                        
                        shutil.move(temp_path, file_path)
                        
                        monitor.finish_transfer(filename, received_delta_bytes, client_total_blocks * utils.BLOCK_SIZE)
                    else:
                        client_socket.send(b"INTEGRITY_FAIL")
                        monitor.log_event(f"Integrity FAIL: {filename}")
                        print("[Delta Sync] Integrity check failed!")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                except ValueError:
                    print("Error parsing delta metadata")

            # DELETE filename password
            elif cmd == "DELETE":
                try:
                    if len(parts) < 3:
                         client_socket.send(b"ERROR_Usage: DELETE filename password")
                         continue
                    
                    filename = parts[1]
                    password = parts[2]
                    
                    # AUTH CHECK
                    if password != "admin":
                        client_socket.send(b"ERROR_AUTH_FAILED")
                        monitor.log_event(f"Delete failed (Auth): {filename}")
                        continue

                    file_path = os.path.join("files", filename)
                    
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        monitor.log_event(f"Deleted file: {filename}")
                        client_socket.send(b"OK")
                        print(f"[-] Deleted file: {filename}")
                    else:
                        client_socket.send(b"ERROR_NOT_FOUND")
                        
                except Exception as e:
                    print(f"Error deleting file: {e}")
                    client_socket.send(f"ERROR: {e}".encode())

            # DOWNLOAD filename [OFFSET=123]
            elif cmd == "DOWNLOAD":
                if len(parts) < 2:
                    continue
                filename = parts[1]
                offset = 0
                
                # Parse OPTIONS
                use_compression = False
                for part in parts[2:]:
                    if part.startswith("OFFSET="):
                        try:
                            offset = int(part.split("=")[1])
                        except ValueError:
                            pass
                    elif part == "COMPRESS":
                        use_compression = True
                
                file_path = os.path.join("files", filename)
                
                if os.path.exists(file_path):
                    total_size = os.path.getsize(file_path)
                    
                    if offset >= total_size:
                         remaining_size = 0
                    else:
                         remaining_size = total_size - offset
                    
                    # If compressing, we don't know the exact size, but the client expects a number.
                    # We can send "STREAM" to indicate chunked/compressed mode?
                    # Or we just send the original size (remaining_size) so client can show progress,
                    # BUT the client socket loop needs to just read until specific EOF marker or based on chunk headers.
                    # Let's keep it simple: Client asks for compression -> Client expects chunked format.
                    # Server sends "COMPRESSED" instead of size? Or "SIZE|COMPRESSED"?
                    
                    if use_compression:
                        client_socket.send(f"COMPRESSED_{remaining_size}".encode())
                    else:
                        client_socket.send(str(remaining_size).encode())
                    
                    ack = client_socket.recv(1024).decode() # Wait for OK
                    if ack == "OK":
                        with open(file_path, "rb") as f:
                            if offset > 0:
                                f.seek(offset)
                            
                            if use_compression:
                                compressor = zlib.compressobj()
                                while True:
                                    data = f.read(4096)
                                    if not data:
                                        break
                                    compressed = compressor.compress(data)
                                    if compressed:
                                        # Send Length (4 bytes) + Data
                                        client_socket.send(len(compressed).to_bytes(4, byteorder='big'))
                                        client_socket.send(compressed)
                                
                                # Flush remaining
                                remaining = compressor.flush()
                                if remaining:
                                    client_socket.send(len(remaining).to_bytes(4, byteorder='big'))
                                    client_socket.send(remaining)
                                

                                # Send EOF (Length 0)
                                client_socket.send((0).to_bytes(4, byteorder='big'))
                                print(f"Sent file (compressed): {filename}")
                                
                            else:
                                # Normal Transfer
                                while True:
                                    data = f.read(4096)
                                    if not data:
                                        break
                                    client_socket.send(data)
                        print(f"Sent file: {filename}")
                else:
                    client_socket.send(b"NOT_FOUND")

            # EXIT
            elif cmd == "EXIT":
                break
        
        except Exception as e:
            print(f"Error handling client {address}: {e}")
            break

    client_socket.close()
    print(f"[-] Connection closed from {address}")


def start_server():
    # Change to project directory to avoid .env permission issues
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Ensure 'files' directory exists
    if not os.path.exists('files'):
        os.makedirs('files')
        print("Created 'files' directory")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow port reuse to avoid 'Address already in use' errors during testing
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 5001))
    server.listen(5)

    print("[+] Server is listening on port 5001...")
    
    # Start Dashboard
    dash_thread = threading.Thread(target=dashboard.run, daemon=True)
    dash_thread.start()
    
    monitor.log_event("Server started on port 5001")

    while True:
        client_socket, address = server.accept()
        monitor.add_client(address[0])
        thread = threading.Thread(target=handle_client, args=(client_socket, address))
        thread.start()

if __name__ == "__main__":
    start_server()
