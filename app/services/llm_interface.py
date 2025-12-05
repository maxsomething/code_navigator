import logging
import requests
import json
import re
import pickle
import os
import networkx as nx
from app.config import Config
from app.services.context_retriever import ContextRetriever

class LLMInterface:
    def __init__(self):
        self.logger = logging.getLogger("LLMInterface")
        self.host = Config.OLLAMA_HOST
        self.model = Config.MODEL_CHAT
        self.analyzer = None 
        self.retriever = ContextRetriever()
        
        # Performance Settings
        self.MAX_CONTEXT_FILES = 5
        self.MAX_LINES_PER_FILE = 100

    def bind_analyzer(self, analyzer):
        self.analyzer = analyzer

    def process_user_query(self, user_prompt: str, use_file=True, use_logic=True, use_scope=True) -> dict:
        """
        Processes the query with selectable context modules to prevent token overload.
        """
        if not self.analyzer:
            return {"answer": "Error: Analyzer not bound to LLM service."}

        context_parts = []
        relevant_files = []

        # --- 1. File Context (Standard RAG) ---
        if use_file:
            all_files = self.analyzer.get_all_project_files()
            relevant_files = self.retriever.find_relevant_files(user_prompt, all_files)
            
            # MITIGATION: Cap file count
            if len(relevant_files) > self.MAX_CONTEXT_FILES:
                relevant_files = relevant_files[:self.MAX_CONTEXT_FILES]

            if relevant_files:
                content_map = self.analyzer.get_files_content(relevant_files)
                context_parts.append("### AVAILABLE FILES (Truncated)\n")
                for path, content in content_map.items():
                    # MITIGATION: Cap lines per file
                    lines = content.split('\n')
                    if len(lines) > self.MAX_LINES_PER_FILE:
                        content = "\n".join(lines[:self.MAX_LINES_PER_FILE]) + f"\n...[Truncated: {len(lines)} lines total]..."
                    
                    context_parts.append(f"FILE: {path}\nContent:\n{content}\n--- END FILE ---\n")
            else:
                context_parts.append("(No relevant source files found via search.)")

        # --- 2. Logic Context (High-Level Topology) ---
        if use_logic:
            logic_summary = self._get_logic_summary(relevant_files)
            if logic_summary:
                context_parts.append("### LOGIC DEPENDENCY CONTEXT (Architecture)")
                context_parts.append("The following outlines how relevant files connect (Imports/Includes):")
                context_parts.append(logic_summary)
                context_parts.append("\n")

        # --- 3. Scope Context (Detailed Internal Structure) ---
        if use_scope:
            # Explicitly check if scope.txt is valid before processing
            scope_path = Config.OUTPUTS_DIR / "scope.txt"
            is_scope_empty = not scope_path.exists() or scope_path.stat().st_size == 0

            if is_scope_empty:
                context_parts.append("### ACTIVE SCOPE CONTEXT")
                context_parts.append("The user's active scope is currently EMPTY. No internal structure available.")
                context_parts.append("\n")
            else:
                scope_summary = self._get_scope_summary()
                if scope_summary:
                    context_parts.append("### ACTIVE SCOPE CONTEXT (Internal Structure)")
                    context_parts.append("The following details the internal definitions (functions/classes) of the Active Scope:")
                    context_parts.append(scope_summary)
                    context_parts.append("\n")

        # Combine Contexts
        full_context_str = "\n".join(context_parts)

        # Generate Response
        raw_response = self._generate_response(user_prompt, full_context_str, relevant_files)

        # Process Actions (Scope Management)
        clean_response, actions_taken = self._process_actions(raw_response)
        
        if actions_taken:
            clean_response += f"\n\n*{actions_taken}*"

        return {"answer": clean_response}

    def _get_logic_summary(self, focused_files):
        """Extracts simple dependency relationships for the focused files."""
        try:
            path = Config.GRAPHS_DIR / "logic_graph_simple.pkl"
            if not path.exists(): return ""
            
            with open(path, 'rb') as f: 
                data = pickle.load(f)
                graph = data.get("graph")
            
            if not graph: return ""

            lines = []
            # Determine which nodes to describe. If focus is empty, pick top hubs.
            nodes_to_check = focused_files if focused_files else [n for n,d in sorted(graph.degree, key=lambda x: x[1], reverse=True)[:10]]
            
            for node in nodes_to_check:
                if node in graph:
                    succ = list(graph.successors(node))
                    if succ: 
                        # Filter successors to keep context short
                        succ_str = ', '.join([s for s in succ if s in nodes_to_check or len(lines) < 20])
                        if succ_str:
                            lines.append(f"- {node} DEPENDS ON: [{succ_str}]")
            return "\n".join(lines)
        except Exception as e:
            self.logger.error(f"Error building logic summary: {e}")
            return ""

    def _get_scope_summary(self):
        """Extracts function signatures from the detailed Scope Graph."""
        try:
            path = Config.GRAPHS_DIR / "scope_graph_full.pkl"
            if not path.exists(): return ""
            
            with open(path, 'rb') as f: 
                data = pickle.load(f)
                graph = data.get("graph")
            
            if not graph: return "" 

            lines = []
            files_seen = set()
            count = 0
            
            for node, data in graph.nodes(data=True):
                # Hard cap to prevent context explosion
                if count > 40:
                    lines.append("... [Scope definitions truncated] ...")
                    break

                if "::" in node:
                    file_part = node.split("::")[0]
                    if file_part not in files_seen:
                        lines.append(f"File: {file_part}")
                        files_seen.add(file_part)
                    
                    # Extract signature or content snippet
                    content = data.get('content', '')
                    signature = content.split('{')[0].strip() if '{' in content else node.split("::")[-1]
                    lines.append(f"  - Def: {signature}")
                    count += 1
            
            return "\n".join(lines)
        except Exception as e:
            self.logger.error(f"Error building scope summary: {e}")
            return ""

    def _generate_response(self, user_prompt: str, context: str, relevant_files: list) -> str:
        system_prompt = f"""
You are Code_Navigator.
CONTEXT:
{context}

To add files to scope, output: `<<SCOPE_ACTION: {{"action": "add", "files": ["filename"]}}>>`

Answer the user query based on the context.
"""
        timeout_sec = 120
        try:
            payload = {
                "model": self.model,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_ctx": 4096 # Force standard context window size
                }
            }
            resp = requests.post(f"{self.host}/api/generate", json=payload, timeout=timeout_sec)
            resp.raise_for_status()
            return resp.json().get("response", "")

        except requests.exceptions.ReadTimeout:
            self.logger.error(f"LLM Timeout ({timeout_sec}s). Context reduced but still too heavy for {self.model}.")
            return "Error: AI generation timed out. Please reduce scope or focus on fewer files."

        except requests.exceptions.ConnectionError:
            self.logger.error(f"LLM Connection Refused. Is Ollama running at {self.host}?")
            return "Error: Could not connect to AI service. Is Ollama running?"

        except Exception as e:
            self.logger.error(f"LLM generation unexpected error: {str(e)}")
            return f"Error generating response: {str(e)}"

    def _process_actions(self, response_text: str) -> tuple[str, str]:
        """
        Parses the response for <<SCOPE_ACTION: ...>> tags, executes them,
        and removes them from the visible text.
        """
        action_pattern = r"<<SCOPE_ACTION:\s*(\{.*?\})\s*>>"
        match = re.search(action_pattern, response_text, re.DOTALL)
        
        status_msg = ""
        clean_text = response_text
        
        if match:
            json_str = match.group(1)
            # Remove the tag from the user-facing text
            clean_text = re.sub(action_pattern, "", response_text).strip()
            
            try:
                data = json.loads(json_str)
                action = data.get("action")
                files = data.get("files", [])
                
                if action == "add" and files:
                    added = self.analyzer.add_to_scope(files)
                    if added:
                        status_msg = f"Scope Updated: Added {len(added)} files ({', '.join([f.split('/')[-1] for f in added])})."
                    else:
                        status_msg = "Scope Update: Files were already in scope."
                        
            except json.JSONDecodeError:
                self.logger.error(f"Failed to decode scope action JSON: {json_str}")
            except Exception as e:
                self.logger.error(f"Error executing scope action: {e}")

        return clean_text, status_msg