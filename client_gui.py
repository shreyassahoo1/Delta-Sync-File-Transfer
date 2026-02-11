import socket
import threading
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import utils

CHUNK = 64 * 1024  # 64 KB

class FileTransferGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Client File Transfer — GUI Client")
        self.sock = None
        self.connected = False

        # --- Top bar: connection ---
        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Server IP:").pack(side="left")
        self.ip_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(top, textvariable=self.ip_var, width=15).pack(side="left", padx=(4,12))

        ttk.Label(top, text="Port:").pack(side="left")
        self.port_var = tk.StringVar(value="5001")
        ttk.Entry(top, textvariable=self.port_var, width=7).pack(side="left", padx=(4,12))

        self.btn_connect = ttk.Button(top, text="Connect", command=self.connect)
        self.btn_connect.pack(side="left")

        self.btn_refresh = ttk.Button(top, text="Refresh (LIST)", command=self.refresh_list, state="disabled")
        self.btn_refresh.pack(side="left", padx=(10,0))

        # --- Middle: server files list + actions ---
        mid = ttk.Frame(root, padding=(10,0,10,10))
        mid.pack(fill="both", expand=True)

        left = ttk.Frame(mid)
        left.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Files on Server:").pack(anchor="w")
        self.files_list = tk.Listbox(left, height=12)
        self.files_list.pack(fill="both", expand=True)
        self.files_scroll = ttk.Scrollbar(left, orient="vertical", command=self.files_list.yview)
        self.files_list.config(yscrollcommand=self.files_scroll.set)
        self.files_scroll.pack(side="right", fill="y")

        right = ttk.Frame(mid)
        right.pack(side="left", fill="y", padx=(10,0))

        self.btn_upload = ttk.Button(right, text="Upload...", command=self.upload_file, state="disabled", width=18)
        self.btn_upload.pack(pady=(0,8))

        self.btn_download = ttk.Button(right, text="Download Selected...", command=self.download_selected, state="disabled", width=18)
        self.btn_download.pack(pady=(0,8))

        self.btn_delete = ttk.Button(right, text="Delete Selected", command=self.delete_selected, state="disabled", width=18)
        self.btn_delete.pack(pady=(0,8))

        # Delta Sync Toggle
        self.var_delta = tk.BooleanVar(value=True)
        self.chk_delta = ttk.Checkbutton(right, text="Delta Sync", variable=self.var_delta)
        self.chk_delta.pack(pady=(0,8))

        # --- Progress bar ---
        prog = ttk.Frame(root, padding=(10,0,10,10))
        prog.pack(fill="x")
        ttk.Label(prog, text="Transfer Progress:").pack(anchor="w")
        self.progress = ttk.Progressbar(prog, mode="determinate", maximum=100)
        self.progress.pack(fill="x")

        # --- Log panel ---
        logf = ttk.Frame(root, padding=(10,0,10,10))
        logf.pack(fill="both", expand=True)
        ttk.Label(logf, text="Log:").pack(anchor="w")
        self.log = tk.Text(logf, height=8, state="disabled")
        self.log.pack(fill="both", expand=True)

        # Style
        try:
            root.tk.call("source", "azure.tcl")  # if you have a theme, optional
            ttk.Style().theme_use("azure")
        except Exception:
            pass

    # -------- utils --------
    def log_msg(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_connected_ui(self, connected: bool):
        self.connected = connected
        self.btn_connect.config(text="Disconnect" if connected else "Connect")
        for b in (self.btn_refresh, self.btn_upload, self.btn_download, self.btn_delete):
            b.config(state="normal" if connected else "disabled")

    def with_thread(self, target, *args):
        t = threading.Thread(target=target, args=args, daemon=True)
        t.start()

    # -------- networking --------
    def connect(self):
        if self.connected:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
            self.set_connected_ui(False)
            self.log_msg("Disconnected.")
            return

        host = self.ip_var.get().strip()
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be a number.")
            return

        def _do_connect():
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((host, port))
                self.set_connected_ui(True)
                self.log_msg(f"✅ Connected to {host}:{port}")
                self.refresh_list()
            except Exception as e:
                self.set_connected_ui(False)
                self.sock = None
                self.log_msg(f"❌ Connect failed: {e}")
                messagebox.showerror("Connection Error", str(e))

        self.with_thread(_do_connect)

    def send_cmd(self, text: str):
        if not self.connected:
            raise RuntimeError("Not connected")
        self.sock.sendall(text.encode())

    def recv_text(self, n=4096) -> str:
        data = self.sock.recv(n)
        return data.decode()

    # -------- commands --------
    def refresh_list(self):
        if not self.connected:
            return
        def _do_list():
            try:
                self.send_cmd("LIST")
                resp = self.recv_text(65536)
                files = [f for f in resp.splitlines() if f.strip()]
                self.files_list.delete(0, "end")
                for f in files:
                    self.files_list.insert("end", f)
                self.log_msg("📄 LIST updated.")
            except Exception as e:
                self.log_msg(f"❌ LIST failed: {e}")
        self.with_thread(_do_list)

    def upload_file(self):
        if not self.connected:
            return
        path = filedialog.askopenfilename(title="Select a file to upload")
        if not path:
            return
        filename = os.path.basename(path)
        size = os.path.getsize(path)

        def _do_upload():
            try:
                # CHECK DELTA SYNC TOGGLE
                use_delta = self.var_delta.get()
                
                # OPTIMIZATION: Try UPLOAD_DELTA first (ONLY IF ENABLED)
                if use_delta:
                    self.log_msg(f"[*] Attempting Delta Sync for '{filename}'...")
                    
                    # 1) Send UPLOAD_DELTA command
                    self.send_cmd(f"UPLOAD_DELTA {filename}")
                    
                    # 2) Check Response
                    response = self.sock.recv(1024).decode()
                    
                    if response == "ACK":
                         # ... Delta Logic ...
                         # To avoid code duplication and massive nesting, let's keep it here.
                         self.log_msg("[+] Server ready for Delta Sync. Computing hashes...")
                         
                         total_blocks, block_hashes, file_hash = utils.get_file_block_hashes(path)
                         start_msg = {
                            "total_blocks": total_blocks,
                            "hashes": block_hashes,
                            "file_hash": file_hash
                         }
                         json_data = json.dumps(start_msg).encode()
                         
                         self.sock.sendall(str(len(json_data)).encode().ljust(10))
                         if self.recv_text(1024) != "OK":
                              raise RuntimeError("Server error receiving hash list size")
                         
                         self.sock.sendall(json_data)
                         
                         len_data = self.sock.recv(10).decode().strip()
                         resp_len = int(len_data)
                         
                         resp_data = b""
                         while len(resp_data) < resp_len:
                             chunk = self.sock.recv(min(4096, resp_len - len(resp_data)))
                             if not chunk: break
                             resp_data += chunk
                         
                         missing_blocks = json.loads(resp_data.decode())["missing"]
                         
                         saved_blocks = total_blocks - len(missing_blocks)
                         self.log_msg(f"[Delta Sync] Blocks present: {saved_blocks}/{total_blocks}")
                         if total_blocks > 0:
                             saved_pct = (saved_blocks / total_blocks) * 100
                             self.log_msg(f"[Delta Sync] Bandwidth saved: {saved_pct:.1f}%")
                         
                         self.progress["value"] = 0
                         count = 0
                         total_missing = len(missing_blocks)
                         
                         with open(path, "rb") as f:
                             for idx in missing_blocks:
                                 f.seek(idx * utils.BLOCK_SIZE)
                                 block_data = f.read(utils.BLOCK_SIZE)
                                 
                                 header = idx.to_bytes(4, 'big') + len(block_data).to_bytes(4, 'big')
                                 self.sock.sendall(header)
                                 self.sock.sendall(block_data)
                                 
                                 ack = self.recv_text(1024)
                                 if ack != "ACK":
                                     raise RuntimeError(f"Block {idx} failed")
                                 
                                 count += 1
                                 if total_missing > 0:
                                     self.progress["value"] = int((count / total_missing) * 100)
                                     self.root.update_idletasks()
                                     
                         final = self.recv_text(1024)
                         if final == "INTEGRITY_OK":
                             self.log_msg(f"✅ Delta Sync Complete: '{filename}'")
                         else:
                             self.log_msg("❌ Delta Sync Integrity Failed!")
                        
                         self.refresh_list()
                         return # DONE
                    
                    elif response == "FULL_UPLOAD_REQUIRED":
                         self.log_msg("[-] File not on server or Delta disabled. Performing full upload...")
                    else:
                         self.log_msg(f"[-] Server response: {response}. Fallback to normal upload.")

                else:
                    self.log_msg("[*] Delta Sync Disabled. Performing full upload...")

                # --- NORMAL UPLOAD FLOW (Fallback or Forced) ---
                self.send_cmd(f"UPLOAD {filename}")
                if self.recv_text(1024) != "OK":
                     # It's possible we are out of sync if server is waiting for something else?
                     # If we sent UPLOAD_DELTA and got response, we are clean.
                     # If we didn't send UPLOAD_DELTA, we are clean.
                     raise RuntimeError("Server rejected UPLOAD command")
                     
                self.sock.sendall(str(size).encode())
                if self.recv_text(1024) != "OK":
                     raise RuntimeError("Server rejected size")
                     
                sent = 0
                self.progress["value"] = 0
                with open(path, "rb") as f:
                     while True:
                         chunk = f.read(CHUNK)
                         if not chunk: break
                         self.sock.sendall(chunk)
                         sent += len(chunk)
                         pct = int((sent / size) * 100) if size else 100
                         self.progress["value"] = pct
                         self.root.update_idletasks()
                self.log_msg(f"✅ Full Upload Complete: '{filename}'")
                self.refresh_list()
                
            except Exception as e:
                self.log_msg(f"❌ Upload failed: {e}")
                import traceback
                traceback.print_exc() 
                messagebox.showerror("Upload Error", str(e))
            finally:
                self.progress["value"] = 0
        
        self.with_thread(_do_upload)

    def delete_selected(self):
        if not self.connected: 
            return
        selection = self.files_list.curselection()
        if not selection:
            messagebox.showinfo("Delete", "Select a file to delete.")
            return
        filename = self.files_list.get(selection[0])
        
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{filename}'?"):
            return

        # AUTH: Ask for password
        password = simpledialog.askstring("Authorization", "Enter Admin Password:", show='*')
        if not password:
            return

        def _do_delete():
            try:
                self.send_cmd(f"DELETE {filename} {password}")
                resp = self.recv_text(1024)
                if resp.startswith("OK"):
                    self.log_msg(f"🗑️ Deleted '{filename}'")
                    self.refresh_list()
                elif "AUTH_FAILED" in resp:
                    self.log_msg(f"❌ Delete failed: Incorrect Password")
                    messagebox.showerror("Delete Failed", "Incorrect Password")
                else:
                    self.log_msg(f"❌ Delete failed: {resp}")
                    messagebox.showerror("Delete Failed", resp)
            except Exception as e:
                self.log_msg(f"❌ Error deleting: {e}")
        
        self.with_thread(_do_delete)

    def download_selected(self):
        if not self.connected:
            return
        selection = self.files_list.curselection()
        if not selection:
            messagebox.showinfo("Download", "Select a file from the list first.")
            return
        filename = self.files_list.get(selection[0])
        save_path = filedialog.asksaveasfilename(initialfile=filename, title="Save as")
        if not save_path:
            return

        def _do_download():
            try:
                # 1) request
                self.send_cmd(f"DOWNLOAD {filename}")
                # 2) get size or NOT_FOUND
                raw = self.recv_text(1024)
                if raw == "NOT_FOUND":
                    self.log_msg("❌ Server says: file not found.")
                    messagebox.showerror("Download Error", "File not found on server.")
                    return
                try:
                    size = int(raw)
                except ValueError:
                    raise RuntimeError(f"Invalid size from server: {raw!r}")

                # 3) say OK
                self.sock.sendall(b"OK")

                # 4) receive in chunks
                received = 0
                self.progress["value"] = 0
                with open(save_path, "wb") as f:
                    while received < size:
                        chunk = self.sock.recv(min(CHUNK, size - received))
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)
                        pct = int((received / size) * 100) if size else 100
                        self.progress["value"] = pct
                        self.root.update_idletasks()

                if received == size:
                    self.log_msg(f"✅ Downloaded '{filename}' → '{save_path}' ({size} bytes)")
                else:
                    self.log_msg(f"⚠️ Download incomplete: got {received}/{size} bytes")

            except Exception as e:
                self.log_msg(f"❌ Download failed: {e}")
                messagebox.showerror("Download Error", str(e))
            finally:
                self.progress["value"] = 0

        self.with_thread(_do_download)


if __name__ == "__main__":
    root = tk.Tk()
    app = FileTransferGUI(root)
    root.mainloop()
