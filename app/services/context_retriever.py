import logging
import json
import requests
import os
from app.config import Config

class ContextRetriever:
    """
    An AI-powered service to find relevant files based on a user query.
    Combines fuzzy text search (pre-filtering) with LLM ranking.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.host = Config.OLLAMA_HOST
        self.model = Config.MODEL_CHAT

    def find_relevant_files(self, query: str, file_list: list[str]) -> list[str]:
        """
        Uses a hybrid approach:
        1. Fuzzy string matching to find obvious candidates (e.g. user types "unit.h").
        2. LLM selection to pick semantically relevant files from the top candidates.
        """
        if not file_list:
            return []

        # 1. Pre-filter: Don't send 10,000 files to the LLM. 
        # Identify top candidates based on simple string matching.
        candidates = self._hybrid_search(query, file_list)
        
        # If we found exact basename matches (e.g. user asked for "unit.h" and we have "src/unit.h"),
        # we trust those implicitly and prioritize them.
        priority_files = candidates.get('exact', [])
        broad_files = candidates.get('fuzzy', [])
        
        # Combine list, keeping priority files first. limit to 50 for LLM context window safety.
        combined_list = (priority_files + broad_files)[:50]
        
        if not combined_list:
            return []

        # 2. Use LLM to refine the selection from the candidates
        return self._ask_llm_to_select(query, combined_list)

    def _hybrid_search(self, query: str, all_files: list[str]) -> dict:
        """
        Scans file list for direct matches to the query terms.
        """
        query_terms = [t.lower() for t in query.split()]
        exact_matches = []
        fuzzy_matches = []
        
        for f in all_files:
            basename = os.path.basename(f).lower()
            
            # Priority 1: Exact filename match (e.g. "unit.h" in query matches "unit.h" file)
            # We check if any term in the query IS the filename
            is_exact = False
            for term in query_terms:
                if term == basename:
                    exact_matches.append(f)
                    is_exact = True
                    break
            if is_exact: continue

            # Priority 2: Fuzzy match (filename contains term)
            # e.g. "unit" matches "unit_test.cpp"
            score = 0
            for term in query_terms:
                if len(term) > 2 and term in f.lower():
                    score += 1
            
            if score > 0:
                fuzzy_matches.append((score, f))
        
        # Sort fuzzy matches by relevance (score)
        fuzzy_matches.sort(key=lambda x: x[0], reverse=True)
        sorted_fuzzy = [f for score, f in fuzzy_matches]

        return {"exact": exact_matches, "fuzzy": sorted_fuzzy}

    def _ask_llm_to_select(self, query: str, candidate_files: list[str]) -> list[str]:
        formatted_list = "\n".join(candidate_files)
        
        system_prompt = f"""
You are a code analysis engine. 
User Query: "{query}"

Task: Select the file paths from the list below that are most relevant to the query.
- If the user names a file specifically (e.g. "main.cpp"), YOU MUST select it.
- Return ONLY a JSON object with a key "files" containing the list of strings.
- Do not add explanations.

FILE LIST:
{formatted_list}
"""
        timeout_sec = 30
        try:
            payload = {
                "model": self.model,
                "system": system_prompt,
                "prompt": "Return the JSON.",
                "format": "json",
                "stream": False
            }
            
            response = requests.post(f"{self.host}/api/generate", json=payload, timeout=timeout_sec)
            response.raise_for_status()
            data = json.loads(response.json().get("response", "{}"))
            
            selected = data.get("files", [])
            
            # Validation: Ensure returned files actually exist in our candidate list
            valid_selection = [f for f in selected if f in candidate_files]
            
            # Fallback: If LLM returns nothing but we had exact matches in the pre-filter, use those.
            if not valid_selection:
                query_lower = query.lower()
                for f in candidate_files:
                    if os.path.basename(f).lower() in query_lower:
                        valid_selection.append(f)

            return valid_selection

        except requests.exceptions.ReadTimeout:
            self.logger.error(
                f"Context Retrieval Timeout ({timeout_sec}s). "
                f"The model '{self.model}' is taking too long to rank {len(candidate_files)} files. "
                "Falling back to simple keyword matching."
            )
            return [f for f in candidate_files if os.path.basename(f).lower() in query.lower()]

        except requests.exceptions.ConnectionError:
            self.logger.error(
                f"Context Retrieval Connection Error. Could not connect to Ollama at {self.host}. "
                "Is the service running?"
            )
            return [f for f in candidate_files if os.path.basename(f).lower() in query.lower()]

        except Exception as e:
            self.logger.error(f"Context Retrieval unexpected error: {str(e)}")
            # Fallback to simple string matching
            return [f for f in candidate_files if os.path.basename(f).lower() in query.lower()]