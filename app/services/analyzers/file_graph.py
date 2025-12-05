import os
import networkx as nx
import pickle
import time
import logging
from app.config import Config
from app.services.static_graph_generator import StaticGraphGenerator
from app.services.analyzers.graph_styler import apply_visual_styles

class FileGraphBuilder:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def build(self, project_root: str, callback=None):
        graph = nx.DiGraph()
        
        # ... (Graph construction logic is unchanged) ...
        ignore_set = Config.IGNORE_DIRS
        root_name = os.path.basename(project_root)
        graph.add_node(root_name, type="directory", label=root_name)
        count = 0
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in ignore_set]
            rel_root = os.path.relpath(root, project_root)
            parent_node = root_name if rel_root == "." else rel_root
            if rel_root != ".": graph.add_node(parent_node, type="directory", label=os.path.basename(parent_node))
            for d in dirs: graph.add_edge(parent_node, os.path.join(rel_root, d) if rel_root != "." else d)
            for f in files:
                rel_path = os.path.join(rel_root, f) if rel_root != "." else f
                graph.add_node(rel_path, type="file", label=f)
                graph.add_edge(parent_node, rel_path)
                count += 1
        
        if callback: callback(count, count, f"File Scan Complete. Found {count} items.")
        self._save_graphs(graph, project_root)
        return graph

    def _save_graphs(self, full_graph, root):
        """
        Definitive workflow: Style, save full, generate image, then create and save simple.
        """
        # 1. Apply visual styles (colors, groups, sizes) to the full graph.
        apply_visual_styles(full_graph)

        # 2. Calculate and save the layout positions for the full graph.
        self.logger.info("Calculating initial layout positions for file graph...")
        k_val = 0.8 / (full_graph.number_of_nodes()**0.5) if full_graph.number_of_nodes() > 0 else 1
        positions = nx.spring_layout(full_graph, seed=42, k=k_val)
        
        # 3. Save the styled full graph and its positions to file.
        full_path = Config.GRAPHS_DIR / "file_graph_full.pkl"
        with open(full_path, 'wb') as f:
            pickle.dump({"graph": full_graph, "positions": positions, "root": root}, f)
        
        # 4. Generate the static image from the styled full graph if it's large.
        if full_graph.number_of_nodes() > Config.STATIC_RENDER_THRESHOLD:
            self.logger.info("Full file graph is large. Generating static image.")
            static_gen = StaticGraphGenerator()
            static_gen.generate(full_graph, 'file_graph_full', fixed_pos=positions)

        # 5. Create the simple graph by taking a subgraph of the styled full graph.
        if full_graph.number_of_nodes() > 2000:
            degrees = dict(full_graph.degree())
            top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:2000]
            # .copy() is essential to get a new graph object with inherited styles
            simple_graph = full_graph.subgraph(top_nodes).copy()
        else:
            simple_graph = full_graph
        
        # 6. Save the simple graph.
        simple_path = Config.GRAPHS_DIR / "file_graph_simple.pkl"
        with open(simple_path, 'wb') as f:
            # Simple graph does not need saved positions as it's interactive
            pickle.dump({"graph": simple_graph, "root": root}, f)
        
        self.logger.info("Finished saving all file graph variants.")