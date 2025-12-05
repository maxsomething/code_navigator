import logging
import os
import networkx as nx
import matplotlib
matplotlib.use('Agg') # Headless mode
import matplotlib.pyplot as plt
from app.config import Config

class StaticGraphGenerator:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_dir = Config.GRAPHS_DIR
        self.output_dir.mkdir(exist_ok=True)

    def generate(self, graph: nx.DiGraph, graph_name: str, fixed_pos: dict | None = None):
        if not graph or graph.number_of_nodes() == 0:
            return ""
            
        self.logger.info(f"Rendering high-res static graph: {graph_name}...")
        try:
            plt.style.use('dark_background')
            
            # Massive canvas: 100x100 inches @ 120 DPI = 12,000 x 12,000 pixels
            fig, ax = plt.subplots(figsize=(100, 100))

            # Styles
            groups = set(nx.get_node_attributes(graph, 'group').values())
            node_colors = self._get_node_colors(graph, groups)
            # Standard multiplier for "ideal" size relative to nodes
            node_sizes = [data.get('size', 5) * 10 for _, data in graph.nodes(data=True)]

            # Layout Strategy
            if fixed_pos:
                self.logger.info("Using inherited layout positions.")
                pos = fixed_pos
            else:
                self.logger.info("Computing new spring layout...")
                k_val = 5.0 / (graph.number_of_nodes()**0.5) if graph.number_of_nodes() > 0 else 1.0
                pos = nx.spring_layout(graph, iterations=60, seed=42, k=k_val)

            # Draw Nodes
            nx.draw_networkx_nodes(graph, pos, node_size=node_sizes, node_color=node_colors, 
                                 alpha=0.9, ax=ax, linewidths=0)
            
            # Draw Edges (Brighter and more opaque)
            nx.draw_networkx_edges(graph, pos, width=0.4, edge_color="#999", 
                                 alpha=0.4, arrows=False, ax=ax)
            
            # Draw Labels (Small font size 6)
            labels = {node: os.path.basename(node) for node in graph.nodes()}
            nx.draw_networkx_labels(graph, pos, labels=labels, font_size=6, 
                                  font_color='#e0e0e0', alpha=0.9)

            ax.set_title(f"{graph_name} ({graph.number_of_nodes()} nodes)", 
                       color="#555", fontsize=60, loc='left')
            ax.axis('off')
            
            output_path = self.output_dir / f"static_{graph_name}.png"
            
            plt.savefig(output_path, dpi=120, bbox_inches='tight', pad_inches=0.2)
            plt.close('all')
            
            self.logger.info(f"Saved static graph: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Static generation failed: {e}", exc_info=True)
            return ""
        finally:
            plt.close('all')

    def _get_node_colors(self, graph, groups):
        # Generate distinct colors for folder groups
        color_palette = plt.cm.get_cmap('tab20c', max(1, len(groups)))
        group_to_color = {group: color_palette(i) for i, group in enumerate(groups)}
        return [group_to_color.get(data.get('group', ''), '#555') for _, data in graph.nodes(data=True)]