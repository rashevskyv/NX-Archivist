import shutil
import os
import platform

def get_best_storage_path(base_subdir: str = "nx_archivist_data") -> str:
    """
    Finds the drive/mount point with the most free space and returns a path for data storage.
    """
    best_path = None
    max_free = 0

    if platform.system() == "Windows":
        import ctypes
        import string
        
        drives = []
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(f"{letter}:\\")
            bitmask >>= 1
            
        for drive in drives:
            try:
                total, used, free = shutil.disk_usage(drive)
                if free > max_free:
                    max_free = free
                    best_path = os.path.join(drive, base_subdir)
            except OSError:
                continue
    else:
        # For Linux, check common mount points
        mounts = ["/mnt", "/media", "/var/lib", os.path.expanduser("~"), "."]
        for mount in mounts:
            if os.path.exists(mount) and os.access(mount, os.W_OK):
                try:
                    total, used, free = shutil.disk_usage(mount)
                    if free > max_free:
                        max_free = free
                        best_path = os.path.join(mount, base_subdir)
                except OSError:
                    continue

    if not best_path:
        # Fallback to local data directory in the project root
        best_path = os.path.abspath("data")
        
    try:
        os.makedirs(best_path, exist_ok=True)
    except PermissionError:
        # Final fallback to local data if even the "best" path failed
        best_path = os.path.abspath("data")
        os.makedirs(best_path, exist_ok=True)
        
    return best_path

def check_storage_limit(path: str, limit_gb: int) -> bool:
    """
    Checks if the current usage of the path exceeds the limit in GB.
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
            
    return (total_size / (1024**3)) < limit_gb
