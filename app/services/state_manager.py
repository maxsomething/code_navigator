import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from app.config import Config

class StateManager:
    """
    Manages persistent application state (Recent projects, window settings).
    """
    def __init__(self):
        self.state_file = Config.DATA_DIR / "app_state.json"
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        if not self.state_file.exists():
            return {"projects": [], "last_project": None}
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"projects": [], "last_project": None}

    def add_project(self, path: str):
        """Adds a project to the recent list."""
        if not os.path.exists(path): return

        name = os.path.basename(path)
        # Remove existing if present to move to top
        projects = [p for p in self.state.get("projects", []) if p["path"] != path]
        
        # Insert at top
        projects.insert(0, {"name": name, "path": path})
        
        # Keep max 10
        self.state["projects"] = projects[:10]
        self.state["last_project"] = path
        self._persist()

    def get_recent_projects(self) -> List[Dict]:
        """Returns list of dicts: {'name': str, 'path': str}"""
        # Validate paths exist
        valid = []
        for p in self.state.get("projects", []):
            if os.path.exists(p["path"]):
                valid.append(p)
        return valid

    def get_last_project(self) -> Optional[str]:
        path = self.state.get("last_project")
        if path and os.path.exists(path):
            return path
        return None

    def _persist(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except IOError:
            pass