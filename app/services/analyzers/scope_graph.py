import os
import networkx as nx
import pickle
import logging
from app.config import Config
from app.parsers.tree_sitter_adapter import PolyglotParser
from app.services.embedding_engine import EmbeddingEngine
from app.services.static_graph_generator import StaticGraphGenerator

class ScopeGraphBuilder:
    def __init__(self):
        self.parser = PolyglotParser()
        self.embedder = EmbeddingEngine()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.static_gen = StaticGraphGenerator()
        
        # Paths
        self.master_graph_path = Config.GRAPHS_DIR / "scope_graph_full.pkl"
        self.simple_graph_path = Config.GRAPHS_DIR / "scope_graph_simple.pkl"
        self.logic_graph_path = Config.GRAPHS_DIR / "logic_graph_full.pkl"

    def build(self, project_root: str, callback=None):
        # 1. Load Logic Graph (for inheritance & connectivity)
        logic_graph = self._load_logic_graph()
        
        # 2. Identify Scope
        files_in_scope = self._get_scope_files()
        
        if not files_in_scope:
            if callback: callback(0, 0, "Scope is empty. Clearing graphs.")
            # Create/Overwrite with empty graph
            empty_graph = nx.DiGraph()
            self._save_graph(empty_graph, self.master_graph_path)
            self._save_graph(empty_graph, self.simple_graph_path)
            return empty_graph

        # 3. Initialize Scope Graph
        scope_graph = nx.DiGraph()

        # 4. Add Files & Inherit Styles
        if callback: callback(0, len(files_in_scope), "Adding files and inheriting styles...")
        
        for file_path in files_in_scope:
            attrs = {"type": "file", "label": os.path.basename(file_path)}
            
            # Inherit visual attributes from Logic Graph if available
            if logic_graph.has_node(file_path):
                logic_attrs = logic_graph.nodes[file_path]
                attrs['group'] = logic_attrs.get('group', 'Default')
                attrs['color'] = logic_attrs.get('color', '#999')
            else:
                attrs['group'] = os.path.dirname(file_path) or "Root"
            
            scope_graph.add_node(file_path, **attrs)

        # 5. Calculate Edges between Files (Direct & Indirect)
        if callback: callback(1, len(files_in_scope), "Mapping scope dependencies...")
        
        scope_list = list(files_in_scope)
        for i, source in enumerate(scope_list):
            for target in scope_list:
                if source == target: continue
                
                has_connection = False
                if logic_graph.has_node(source) and logic_graph.has_node(target):
                    if logic_graph.has_edge(source, target):
                        has_connection = True
                    elif nx.has_path(logic_graph, source, target):
                        has_connection = True
                
                if has_connection:
                    scope_graph.add_edge(source, target, type="dependency", style="dashed", color="#555", arrows="to")

        # 6. Parse Internal Structure (Detailed Mode) & Build Rich Tooltips
        if callback: callback(2, len(files_in_scope), "Parsing internal structure...")
        
        for i, file_path in enumerate(files_in_scope):
            full_path = os.path.join(project_root, file_path)
            if not os.path.exists(full_path): continue
            
            res = self.parser.parse_file(full_path, detailed=True)
            parent_group = scope_graph.nodes[file_path].get('group', 'Default')

            # --- Rich Tooltip Construction (HTML Table) ---
            # We build an HTML string that Vis.js will render on hover.
            tooltip_rows = []
            
            for d in res.definitions:
                def_id = f"{file_path}::{d.name}"
                
                # Clean signature for display (first line, html safe)
                raw_sig = d.content.split('\n')[0].strip().rstrip('{').strip()
                safe_sig = raw_sig.replace('<', '&lt;').replace('>', '&gt;')
                
                if len(safe_sig) > 60: safe_sig = safe_sig[:57] + "..."
                
                # Visual hints for type
                type_style = "color:#e06c75; font-weight:bold;" if d.type == 'function' else "color:#e5c07b; font-weight:bold;"
                tooltip_rows.append(
                    f"<tr><td style='{type_style} padding-right:8px;'>{d.type[0].upper()}</td>"
                    f"<td style='font-family:monospace; color:#ccc;'>{safe_sig}</td></tr>"
                )

                # Add Definition Node (For Full Graph)
                scope_graph.add_node(def_id, 
                                     type=d.type, 
                                     label=d.name,
                                     shape='dot', 
                                     size=10, 
                                     group=parent_group, 
                                     content=d.content, 
                                     calls=d.calls,
                                     # Tooltip for the dot itself
                                     title=f"<b>{d.name}</b><br><pre>{safe_sig}</pre>") 
                
                # Link File -> Definition
                scope_graph.add_edge(file_path, def_id, type="defines", color="#61afef", width=2)

            # Assign aggregated tooltip to the File Node
            if tooltip_rows:
                # Limit to first 20 items to prevent screen overflow
                display_rows = tooltip_rows[:20]
                if len(tooltip_rows) > 20:
                    display_rows.append("<tr><td colspan='2'><i>...and more...</i></td></tr>")
                
                table_html = "<table style='border-spacing:0; font-size:11px;'>" + "".join(display_rows) + "</table>"
                header = f"<div style='font-weight:bold; border-bottom:1px solid #555; margin-bottom:4px; font-size:12px;'>{os.path.basename(file_path)}</div>"
                
                # This 'title' attribute is what Vis.js displays on hover
                scope_graph.nodes[file_path]['title'] = f"<div style='text-align:left;'>{header}{table_html}</div>"
            else:
                scope_graph.nodes[file_path]['title'] = f"<b>{os.path.basename(file_path)}</b><br><i style='font-size:10px; color:#888'>No structures found</i>"

        # 7. Rebuild Call Edges (Def -> Def)
        if callback: callback(3, len(files_in_scope), "Linking function calls...")
        self._link_function_calls(scope_graph)

        # 8. Save & Render
        if callback: callback(len(files_in_scope), len(files_in_scope), "Rendering scope visualization...")
        
        # Save Master
        self._save_graph(scope_graph, self.master_graph_path)
        
        # Generate Static Image for the detailed view
        static_path = self.static_gen.generate(scope_graph, "scope_graph_full")
        scope_graph.graph['static_image_path'] = static_path
        
        # Create Simple View (Files only) - This will now include the rich tooltips we created
        simple_graph = self._create_simple_view(scope_graph)
        self._save_graph(simple_graph, self.simple_graph_path)

        if callback: callback(len(files_in_scope), len(files_in_scope), "Scope processing complete.")
        return scope_graph

    def _link_function_calls(self, graph):
        name_map = {}
        for node, data in graph.nodes(data=True):
            if "::" in node:
                short_name = node.split("::")[-1]
                if short_name not in name_map: name_map[short_name] = []
                name_map[short_name].append(node)

        for node, data in graph.nodes(data=True):
            if "::" in node and 'calls' in data:
                file_origin = node.split("::")[0]
                for called_name in data['calls']:
                    candidates = name_map.get(called_name, [])
                    target = None
                    if not candidates: continue
                    for c in candidates:
                        if c.startswith(file_origin): target = c; break
                    if not target: target = candidates[0]
                    
                    if target and target != node:
                        graph.add_edge(node, target, type="calls", color="#e5c07b", arrows="to")

    def _create_simple_view(self, full_graph):
        """Returns a graph with only File nodes, but preserving dependency edges AND tooltips."""
        simple = nx.DiGraph()
        # Copy file nodes
        for n, d in full_graph.nodes(data=True):
            if d.get('type') == 'file':
                # We copy ALL data, which includes the 'title' (tooltip) we just built
                simple.add_node(n, **d)
        
        # Copy dependency edges
        for u, v, d in full_graph.edges(data=True):
            if d.get('type') == 'dependency':
                simple.add_edge(u, v, **d)
                
        return simple

    def _load_logic_graph(self):
        if self.logic_graph_path.exists():
            try:
                with open(self.logic_graph_path, 'rb') as f:
                    return pickle.load(f).get("graph", nx.DiGraph())
            except Exception: pass
        return nx.DiGraph()

    def _get_scope_files(self):
        scope_file = Config.OUTPUTS_DIR / "scope.txt"
        if not scope_file.exists(): return set()
        
        files = set()
        with open(scope_file, 'r') as f:
            for line in f:
                stripped = line.strip()
                if stripped: files.add(stripped)
        return files

    def _save_graph(self, graph, path):
        try:
            with open(path, 'wb') as f:
                pickle.dump({"graph": graph}, f)
        except Exception as e:
            self.logger.error(f"Failed to save graph to {path}: {e}")