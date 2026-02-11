import hashlib
import os

BLOCK_SIZE = 4096

def get_file_block_hashes(file_path):
    """
    Reads a file and returns:
    - total_blocks (int)
    - block_hashes (list of hex strings)
    - full_file_hash (hex string)
    """
    block_hashes = []
    hasher = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(BLOCK_SIZE)
            if not chunk:
                break
            
            # Hash for this block
            block_sha = hashlib.sha256(chunk).hexdigest()
            block_hashes.append(block_sha)
            
            # Update full file hash
            hasher.update(chunk)
            
    return len(block_hashes), block_hashes, hasher.hexdigest()

def get_file_block(file_path, block_index):
    """
    Reads and returns the raw data for a specific block index.
    """
    with open(file_path, "rb") as f:
        f.seek(block_index * BLOCK_SIZE)
        return f.read(BLOCK_SIZE)
