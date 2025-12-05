import logging
import os
import networkx as nx
import pickle
import shutil
from app.config import Config
from app.services.analyzers.file_graph import FileGraphBuilder
from app.services.analyzers.logic_graph import LogicGraphBuilder
from app.services.analyzers.scope_graph import ScopeGraphBuilder
from app.services.static_graph_generator import StaticGraphGenerator

class ProjectAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger("ProjectAnalyzer")
        self.file_builder = FileGraphBuilder()
        self.logic_builder = LogicGraphBuilder()
        self.scope_builder = ScopeGraphBuilder()
        self.current_graph = nx.DiGraph()
        self.project_root = ""
        self.file_metadata = {}

    def set_project(self, project_path: str):
        self.project_root = project_path
        self.current_graph = nx.DiGraph()
        self.logger.info(f"Project set to: {project_path}")

    def build_file_tree(self, callback=None):
        if not self.project_root: return
        self.file_builder.build(self.project_root, callback)

    def build_logic_graphs(self, callback=None):
        if not self.project_root: return
        self.logic_builder.build(self.project_root, callback)

    def build_scope_graph(self, callback=None):
        if not self.project_root: return
        self.scope_builder.build(self.project_root, callback)

    def load_graph(self, mode: str, is_full_detail: bool):
        suffix = 'full' if is_full_detail else 'simple'
        
        # Dynamic mapping for filenames
        if mode == 'file_tree':
            base = f"file_graph_{suffix}"
        elif mode == 'dependency':
            base = f"logic_graph_{suffix}"
        elif mode == 'scope':
            base = f"scope_graph_{suffix}"
        else:
            self.current_graph = nx.DiGraph(); return

        graph_file_pkl = Config.GRAPHS_DIR / f"{base}.pkl"
        static_image_file = Config.GRAPHS_DIR / f"static_{base}.png"

        # Safe Loading Logic
        loaded_graph = None
        
        # 1. Attempt to load the Pickle data first to check metadata/size
        if graph_file_pkl.exists():
            try:
                with open(graph_file_pkl, 'rb') as f:
                    data = pickle.load(f)
                loaded_graph = data.get("graph", nx.DiGraph())
                self.file_metadata = data.get("metadata", {})
            except Exception as e:
                self.logger.error(f"Failed to load graph {graph_file_pkl}: {e}")
                loaded_graph = nx.DiGraph()
                self.file_metadata = {}
        else:
            loaded_graph = nx.DiGraph()
            self.file_metadata = {}

        # 2. Decision: Static Image vs Interactive Graph
        # If the graph is small (<= 50 nodes), force interactive mode so user can see tooltips.
        if loaded_graph.number_of_nodes() > 0 and loaded_graph.number_of_nodes() <= 50:
            self.current_graph = loaded_graph
            # Ensure static path is cleared so UI renders JS
            if 'static_image_path' in self.current_graph.graph:
                del self.current_graph.graph['static_image_path']
            return

        # 3. If massive and full detail requested, prefer static image
        if is_full_detail and static_image_file.exists():
            self.logger.info(f"Loading pre-generated static image: {static_image_file}")
            self.current_graph = nx.DiGraph()
            self.current_graph.graph['static_image_path'] = str(static_image_file)
            return

        # 4. Fallback to loaded graph (Standard Interactive)
        self.current_graph = loaded_graph

    def get_graph(self):
        return self.current_graph

    def clear_project_cache(self):
        if not self.project_root: return
        folders_to_clear = [Config.GRAPHS_DIR, Config.VECTOR_DIR, Config.OUTPUTS_DIR]
        for folder in folders_to_clear:
            if folder.exists() and folder.is_dir():
                for item in folder.iterdir():
                    try:
                        if item.is_dir(): shutil.rmtree(item)
                        else: item.unlink()
                    except Exception as e: self.logger.error(f"Failed to delete {item}: {e}")
        self.current_graph.clear(); self.file_metadata.clear()
        
    def get_scope_list(self) -> list[str]:
        scope_path = Config.OUTPUTS_DIR / "scope.txt"
        if not scope_path.exists(): return []
        with open(scope_path, 'r', encoding='utf-8') as f: return [line.strip() for line in f if line.strip()]

    def update_scope(self, files_to_add=None, files_to_remove=None):
        current_scope = set(self.get_scope_list())
        if files_to_add: current_scope.update(files_to_add)
        if files_to_remove: current_scope.difference_update(files_to_remove)
        Config.OUTPUTS_DIR.mkdir(exist_ok=True)
        with open(Config.OUTPUTS_DIR / "scope.txt", 'w', encoding='utf-8') as f: f.write("\n".join(sorted(list(current_scope))))

    def add_to_scope(self, files_to_add: list[str]) -> list[str]:
        current_scope = set(self.get_scope_list())
        newly_added = [f for f in files_to_add if f not in current_scope]
        if newly_added:
            current_scope.update(newly_added)
            Config.OUTPUTS_DIR.mkdir(exist_ok=True)
            with open(Config.OUTPUTS_DIR / "scope.txt", 'w', encoding='utf-8') as f: f.write("\n".join(sorted(list(current_scope))))
        return newly_added

    def extrapolate_dependencies(self, file_path: str) -> list[str]:
        """
        Finds all files connected to the given file in the logic graph.
        Returns: [file_path] + [predecessors] + [successors]
        """
        graph = None
        
        # 1. Attempt to use current graph if it looks like a Logic Graph
        if self.current_graph and self.current_graph.number_of_edges() > 0:
            try:
                sample_edge = list(self.current_graph.edges(data=True))[0]
                if sample_edge[2].get('type') == 'include':
                    graph = self.current_graph
            except:
                pass

        # 2. If not, try loading the full logic graph from disk
        if graph is None:
            pkl_path = Config.GRAPHS_DIR / "logic_graph_full.pkl"
            if pkl_path.exists():
                try:
                    with open(pkl_path, 'rb') as f:
                        data = pickle.load(f)
                        graph = data.get("graph")
                except Exception as e:
                    self.logger.error(f"Extrapolation failed to load graph: {e}")
        
        if graph is None:
            self.logger.warning("Extrapolation unavailable: No logic graph found.")
            return []

        if file_path not in graph:
            self.logger.warning(f"Extrapolation failed: File {file_path} not in graph.")
            return []

        # Collect dependencies
        up = list(graph.predecessors(file_path))
        down = list(graph.successors(file_path))
        
        result = list(set(up + down + [file_path]))
        self.logger.info(f"Extrapolated {file_path}: Found {len(up)} callers, {len(down)} callees.")
        return result

    def get_all_project_files(self) -> list[str]:
        if self.file_metadata: 
            return list(self.file_metadata.keys())
        all_files = []
        if not self.project_root: return []
        for root, dirs, files in os.walk(self.project_root):
             dirs[:] = [d for d in dirs if d not in Config.IGNORE_DIRS]
             for file in files:
                 if os.path.splitext(file)[1] in Config.ALLOWED_EXTENSIONS:
                     all_files.append(os.path.relpath(os.path.join(root, file), self.project_root))
        return all_files

    def search_files(self, query: str) -> list[str]:
        all_files = self.get_all_project_files()
        if not query:
            return all_files[:100]
        query = query.lower()
        matches = [f for f in all_files if query in f.lower()]
        matches.sort(key=len)
        return matches[:50]

    def get_files_content(self, relative_paths: list[str]) -> dict:
        content_map = {}
        if not self.project_root: return content_map
        for rel_path in relative_paths:
            full_path = os.path.join(self.project_root, rel_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f: content_map[rel_path] = f.read()
                except Exception as e: self.logger.warning(f"Could not read content of {rel_path}: {e}")
        return content_map