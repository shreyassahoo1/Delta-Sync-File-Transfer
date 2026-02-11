import socket
import os
import zlib
import json
import utils

client = socket.socket()
client.connect(("127.0.0.1", 5001))

while True:
    cmd = input("Enter command (UPLOAD filename / DOWNLOAD filename / LIST / EXIT): ")
    parts = cmd.split()

    # ----- EXIT -----
    if parts[0] == "EXIT":
        client.send(cmd.encode())
        break

    # ----- LIST -----
    elif parts[0] == "LIST":
        client.send(cmd.encode())
        response = client.recv(4096).decode()
        print("Server:\n", response)


    # ----- UPLOAD -----
    elif parts[0] == "UPLOAD":
        if len(parts) < 2:
            print("Usage: UPLOAD filename")
            continue
        filename = parts[1]
        if not os.path.exists(filename):
            print("File not found!")
            continue

        client.send(cmd.encode())  # send "UPLOAD filename"
        
        # Wait for server acknowledgment/readiness
        ack = client.recv(1024).decode()
        if ack != "OK":
            print(f"[-] Server Error: {ack}")
            continue

        with open(filename, "rb") as f:
            data = f.read()
        
        client.send(str(len(data)).encode())  # send file size
        
        ack = client.recv(1024).decode()  # wait for OK for size
        if ack != "OK":
            print(f"[-] Server Error: {ack}")
            continue
            
        client.send(data)  # send file
        print("[+] File uploaded.")

    # ----- UPLOAD_DELTA -----
    elif parts[0] == "UPLOAD_DELTA":
        if len(parts) < 2:
            print("Usage: UPLOAD_DELTA filename")
            continue
        filename = parts[1]
        if not os.path.exists(filename):
            print("File not found!")
            continue

        # 1. Send Command
        client.send(cmd.encode())

        # 2. Check Server Response
        response = client.recv(1024).decode()
        if response == "FULL_UPLOAD_REQUIRED":
            print("[-] File not found on server. Full upload required.")
            print("[-] Use 'UPLOAD' command instead.")
            continue
        elif response != "ACK":
            print(f"[-] Server Error: {response}")
            continue

        # 3. Compute Hashes
        print("[Delta Sync] Computing file hashes...")
        total_blocks, block_hashes, file_hash = utils.get_file_block_hashes(filename)
        
        start_msg = {
            "total_blocks": total_blocks,
            "hashes": block_hashes,
            "file_hash": file_hash
        }
        json_data = json.dumps(start_msg).encode()
        
        # 4. Send Hash List
        client.send(str(len(json_data)).encode().ljust(10)) # Send size fixed width
        
        ack = client.recv(1024).decode()
        if ack != "OK":
             print(f"[-] Server Error waiting for json: {ack}")
             continue
             
        client.send(json_data)
        
        # 5. Receive Missing Blocks List
        # Read size first (fixed 10 bytes)
        resp_len_data = client.recv(10).decode().strip()
        try:
            resp_len = int(resp_len_data)
            
            resp_data = b""
            while len(resp_data) < resp_len:
                chunk = client.recv(min(4096, resp_len - len(resp_data)))
                if not chunk: break
                resp_data += chunk
            
            missing_blocks = json.loads(resp_data.decode())["missing"]
            
            # LOGGING
            print(f"[Delta Sync] Total Blocks: {total_blocks}")
            print(f"[Delta Sync] Blocks already on server: {total_blocks - len(missing_blocks)}")
            saved_size_est = (total_blocks - len(missing_blocks)) * utils.BLOCK_SIZE
            total_size_est = total_blocks * utils.BLOCK_SIZE # Approx
            if total_size_est > 0:
                 print(f"[Delta Sync] Uploading only {len(missing_blocks)} blocks ({(len(missing_blocks)*utils.BLOCK_SIZE)/1024:.2f} KB instead of {total_size_est/1024:.2f} KB)")
                 print(f"[Delta Sync] Bandwidth saved: {100 * (1 - len(missing_blocks)/total_blocks):.1f}%")
            
            # 6. Send Missing Blocks
            with open(filename, "rb") as f:
                for idx in missing_blocks:
                    # Read block
                    f.seek(idx * utils.BLOCK_SIZE)
                    block_data = f.read(utils.BLOCK_SIZE)
                    
                    # Send Header: Index (4) + Len (4)
                    header = idx.to_bytes(4, 'big') + len(block_data).to_bytes(4, 'big')
                    client.send(header)
                    client.send(block_data)
                    
                    # Wait for ACK per block
                    ack = client.recv(1024).decode()
                    if ack != "ACK":
                        print(f"[-] Block {idx} upload failed")
                        break
                        
            # 7. Final Integrity Check
            final_status = client.recv(1024).decode()
            if final_status == "INTEGRITY_OK":
                print("[+] Delta Sync Successful! File updated on server.")
            else:
                print("[-] Integrity Check Failed on Server.")

        except ValueError as e:
            print(f"[-] Error processing server response: {e}")


    # ----- DOWNLOAD -----
    elif parts[0] == "DOWNLOAD":
        if len(parts) < 2:
            print("Usage: DOWNLOAD filename")
            continue

        filename = parts[1]
        offset = 0
        mode = "wb"
        use_compression = False
        
        # Check for partial file
        if os.path.exists(filename):
            local_size = os.path.getsize(filename)
            choice = input(f"[-] Found partial file '{filename}' ({local_size} bytes). Resume? (y/n): ")
            if choice.lower() == 'y':
                offset = local_size
                cmd = f"DOWNLOAD {filename} OFFSET={offset}"
                mode = "ab" # Append mode
                print(f"[*] Resuming from byte {offset}...")
            else:
                cmd = f"DOWNLOAD {filename}"
        else:
             cmd = f"DOWNLOAD {filename}"
             
        # Ask for compression (Optional, but let's enable it by default for "Innovation" or ask user?)
        # For this demo, let's just enable it if it's a fresh download or if the user wants "Turbo Mode".
        # Prompt user:
        comp_choice = input("Enable Compression? (y/n): ")
        if comp_choice.lower() == 'y':
            cmd += " COMPRESS"
            use_compression = True
        
        client.send(cmd.encode())  # send request

        response = client.recv(1024).decode()
        if response == "NOT_FOUND":
            print("[-] File does not exist on server.")
            continue
            
        is_compressed = False
        filesize = 0
        
        if response.startswith("COMPRESSED_"):
            is_compressed = True
            try:
                filesize = int(response.split("_")[1])
            except:
                filesize = 0
        else:
            try:
                filesize = int(response)
            except ValueError:
                print(f"[-] Error: Server sent invalid size: {response}")
                continue

        if filesize == 0 and offset > 0 and not is_compressed: # If compressed, 0 might mean unknown? No, I sent remaining_size.
            if filesize == 0:
                print("[+] File already fully downloaded.")
                continue

        client.send(b"OK")  # acknowledge to start transfer

        with open(filename, mode) as f:
            if is_compressed:
                print("[*] Receiving Compressed Stream...")
                decompressor = zlib.decompressobj()
                while True:
                    # Read Chunk Length (4 bytes)
                    len_bytes = client.recv(4)
                    if not len_bytes:
                        break
                    chunk_len = int.from_bytes(len_bytes, byteorder='big')
                    
                    if chunk_len == 0:
                        break # EOF
                    
                    # Read Chunk Data
                    compressed_data = b""
                    while len(compressed_data) < chunk_len:
                        packet = client.recv(chunk_len - len(compressed_data))
                        if not packet:
                            break
                        compressed_data += packet
                        
                    # Decompress
                    decompressed = decompressor.decompress(compressed_data)
                    f.write(decompressed)
                
                # Flush
                f.write(decompressor.flush())
            
            else:
                # Normal Transfer
                bytes_received = 0
                while bytes_received < filesize:
                    chunk_size = 4096
                    remaining = filesize - bytes_received
                    if remaining < chunk_size:
                        chunk_size = remaining
                    
                    data = client.recv(chunk_size)
                    if not data:
                        break
                    f.write(data)
                    bytes_received += len(data)

        print(f"[+] Download complete. Saved as {filename}")


client.close()
