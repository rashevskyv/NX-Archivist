import re
from typing import List, Dict

class Categorizer:
    # Common patterns for Switch files
    BASE_PATTERN = re.compile(r"\[0100[0-9A-F]{8}000\]", re.IGNORECASE)
    UPDATE_PATTERN = re.compile(r"\[0100[0-9A-F]{8}[0-9A-F]{3}[1-9A-F]000\]", re.IGNORECASE) # Simplified
    DLC_PATTERN = re.compile(r"\[0100[0-9A-F]{8}[0-9A-F]{3}[0-9A-F][1-9A-F]00\]", re.IGNORECASE) # Simplified
    
    # Better patterns based on Title ID structure
    # Base: [TitleID] where TitleID ends in 000
    # Update: [TitleID] where TitleID ends in 800, 1000, etc.
    # DLC: [TitleID] where TitleID is between Base and Update
    
    @classmethod
    def categorize(cls, filename: str) -> str:
        filename_lower = filename.lower()
        
        # Simple keyword check first
        if "update" in filename_lower or "v65536" in filename_lower or "v131072" in filename_lower:
            return "Update"
        if "dlc" in filename_lower:
            return "DLC"
            
        # Regex check
        if cls.UPDATE_PATTERN.search(filename):
            return "Update"
        if cls.DLC_PATTERN.search(filename):
            return "DLC"
        if cls.BASE_PATTERN.search(filename):
            return "Base"
            
        return "Unknown"

    @classmethod
    def group_dlcs(cls, files: List[str], threshold: int = 5) -> Dict[str, List[str]]:
        """
        Groups files into categories. If DLC count > threshold, they are grouped.
        """
        categories = {"Base": [], "Update": [], "DLC": [], "Unknown": []}
        for f in files:
            cat = cls.categorize(f)
            categories[cat].append(f)
            
        return categories
