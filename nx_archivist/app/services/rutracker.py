import json
import httpx
from typing import List, Dict
from app.core.config import config
import os

class RuTrackerService:
    def __init__(self):
        self.base_url = "https://rutracker.org/forum/"
        self.cookies = self._load_cookies()
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            cookies=self.cookies,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        )

    def _load_cookies(self) -> Dict[str, str]:
        if os.path.exists(config.RUTRACKER_COOKIES_FILE):
            try:
                with open(config.RUTRACKER_COOKIES_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    async def search(self, query: str) -> List[Dict]:
        """
        Search for Nintendo Switch games on RuTracker.
        """
        from bs4 import BeautifulSoup
        
        params = {
            "f": "1605", # Nintendo Switch category ID
            "nm": query
        }
        
        response = await self.client.get("tracker.php", params=params)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, "lxml")
        results = []
        
        # RuTracker tracker.php table parsing logic
        # Find all topic links
        links = soup.find_all("a", class_="tLink")
        
        for link in links:
            # Each link is inside a row
            row = link.find_parent("tr")
            if not row:
                continue
            
            cells = row.find_all("td")
            if len(cells) < 10:
                continue
            
            # Extract ID from data-topic_id or href
            topic_id = link.get("data-topic_id")
            if not topic_id:
                # viewtopic.php?t=6245869
                href = link.get("href", "")
                if "t=" in href:
                    topic_id = href.split("t=")[-1]
                else:
                    continue
                
            results.append({
                "title": link.get_text(strip=True),
                "id": topic_id,
                "size": cells[5].get_text(strip=True).replace("\xa0", " "),
                "seeds": cells[6].get_text(strip=True)
            })
            
        return results

    async def get_torrent_file(self, topic_id: str) -> bytes:
        # forum/dl.php?t=topic_id
        response = await self.client.get(f"dl.php?t={topic_id}")
        return response.content
