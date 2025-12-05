import os
import pickle
import logging
import networkx as nx
from concurrent.futures import ProcessPoolExecutor, as_completed
from app.config import Config
from app.parsers.tree_sitter_adapter import PolyglotParser
from app.services.analyzers.file_graph import FileGraphBuilder
from app.services.static_graph_generator import StaticGraphGenerator
from app.services.analyzers.dependency_resolver import DependencyResolver

def parse_worker(file_info):
    file_path, project_root = file_info
    rel_path = os.path.relpath(file_path, project_root)
    result = {"rel_path": rel_path, "imports": [], "error": None}
    try:
        parser = PolyglotParser()
        parse_result = parser.parse_file(file_path, detailed=False)
        if parse_result.error:
            result['error'] = parse_result.error
        else:
            result['imports'] = list(parse_result.imports)
    except Exception as e:
        result['error'] = str(e)
    return result

class LogicGraphBuilder:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def build(self, project_root: str, callback=None):
        if callback: callback(0, 1, "Scanning project structure...")
        
        target_files = self._collect_target_files(project_root)
        if not target_files: 
            self.logger.warning("No target files found to analyze.")
            return

        dependency_data = self._parse_files_concurrently(target_files, project_root, callback)
        self._create_graph_variant('full', project_root, dependency_data, callback)
        self._create_graph_variant('simple', project_root, dependency_data, callback)
        
        if callback: callback(len(target_files), len(target_files), "Logic analysis complete.")

    def _create_graph_variant(self, mode: str, project_root: str, dep_data: dict, callback):
        if callback: callback(0, 1, f"Constructing {mode} logic graph...")
        
        base_graph_path = Config.GRAPHS_DIR / f"file_graph_{mode}.pkl"
        if not base_graph_path.exists():
            FileGraphBuilder().build(project_root, None)
        
        try:
            with open(base_graph_path, 'rb') as f: data = pickle.load(f)
            base_graph = data.get("graph")
            base_positions = data.get("positions")
        except Exception as e:
            self.logger.error(f"Failed to load base graph: {e}"); return

        logic_graph = base_graph.copy()
        logic_graph.remove_edges_from(list(logic_graph.edges()))
        
        existing_nodes = set(logic_graph.nodes())
        resolver = DependencyResolver(existing_nodes)
        
        edge_count = 0
        total_imports = sum(len(x['imports']) for x in dep_data.values())
        
        for source, info in dep_data.items():
            if source not in existing_nodes: continue
            
            for imp in info.get('imports', []):
                target = resolver.resolve(source, imp)
                if target and target != source and target in existing_nodes:
                    logic_graph.add_edge(source, target, type="include")
                    edge_count += 1
        
        self.logger.info(f"Built {mode} logic graph: {edge_count} edges from {total_imports} raw imports.")

        output_path = Config.GRAPHS_DIR / f"logic_graph_{mode}.pkl"
        with open(output_path, 'wb') as f:
            pickle.dump({"graph": logic_graph, "positions": base_positions, "metadata": dep_data}, f)

        if mode == 'full' and logic_graph.number_of_nodes() > Config.STATIC_RENDER_THRESHOLD:
            static_gen = StaticGraphGenerator()
            static_gen.generate(logic_graph, 'logic_graph_full', fixed_pos=base_positions)

    def _parse_files_concurrently(self, files, project_root, callback):
        results = {}
        with ProcessPoolExecutor(max_workers=Config.NUM_WORKERS) as executor:
            future_to_file = {executor.submit(parse_worker, (f, project_root)): f for f in files}
            
            completed = 0
            for future in as_completed(future_to_file):
                completed += 1
                if callback and completed % 20 == 0: 
                    callback(completed, len(files), f"Parsing imports {completed}/{len(files)}")
                
                try:
                    res = future.result()
                    results[res['rel_path']] = res
                except Exception as e:
                    self.logger.error(f"Worker failed: {e}")
        return results

    def _collect_target_files(self, project_root):
        targets = []
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in Config.IGNORE_DIRS]
            for file in files:
                if os.path.splitext(file)[1] in Config.ALLOWED_EXTENSIONS:
                    targets.append(os.path.join(root, file))
        return targets