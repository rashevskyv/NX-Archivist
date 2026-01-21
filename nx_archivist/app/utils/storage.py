import shutil
import os
import platform
import logging

logger = logging.getLogger(__name__)

def get_best_storage_path(base_subdir: str = "nx_archivist_data") -> str:
    """
    Finds the drive/mount point with the most free space and returns a path for data storage.
    """
    best_path = None
    max_free = 0
    checked_mounts = []

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
                free_gb = free / (1024**3)
                checked_mounts.append(f"{drive} ({free_gb:.1f} GB free)")
                if free > max_free:
                    max_free = free
                    best_path = os.path.join(drive, base_subdir)
            except OSError:
                continue
    else:
        # For Linux, try to get all mount points
        mounts = set(["/mnt", "/media", "/var/lib", os.path.expanduser("~"), "."])
        if os.path.exists("/proc/mounts"):
            try:
                with open("/proc/mounts", "r") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            mount_point = parts[1]
                            if mount_point.startswith(("/", "/mnt", "/media")):
                                mounts.add(mount_point)
            except Exception:
                pass

        for mount in sorted(list(mounts)):
            if os.path.exists(mount) and os.access(mount, os.W_OK):
                try:
                    total, used, free = shutil.disk_usage(mount)
                    free_gb = free / (1024**3)
                    # Avoid duplicates or nested mounts showing same stats
                    checked_mounts.append(f"{mount} ({free_gb:.1f} GB free)")
                    if free > max_free:
                        max_free = free
                        best_path = os.path.join(mount, base_subdir)
                except OSError:
                    continue

    logger.info(f"Checking storage locations: {', '.join(checked_mounts)}")

    if not best_path:
        best_path = os.path.abspath("data")
        logger.warning(f"No suitable external storage found. Falling back to: {best_path}")
    else:
        logger.info(f"Selected best storage: {best_path} ({max_free / (1024**3):.1f} GB free)")
        
    try:
        os.makedirs(best_path, exist_ok=True)
    except PermissionError:
        best_path = os.path.abspath("data")
        logger.error(f"Permission denied at selected path. Final fallback to: {best_path}")
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
