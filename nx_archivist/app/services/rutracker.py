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
        # Torrent rows always have an id starting with 't-' (e.g., id="t-6007033")
        rows = soup.find_all("tr", id=lambda x: x and x.startswith("t-"))
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 10:
                continue
                
            title_cell = row.find("a", class_="tLink")
            if not title_cell:
                continue
                
            results.append({
                "title": title_cell.get_text(strip=True),
                "id": title_cell["href"].split("t=")[-1],
                "size": cells[5].get_text(strip=True).replace("\xa0", " "),
                "seeds": cells[6].get_text(strip=True)
            })
            
        return results

    async def get_torrent_file(self, topic_id: str) -> bytes:
        # forum/dl.php?t=topic_id
        response = await self.client.get(f"dl.php?t={topic_id}")
        return response.content
