# app/services/analyzers/graph_styler.py
import os
import networkx as nx

def apply_visual_styles(graph: nx.DiGraph):
    """
    Applies visual styling attributes ('group', 'size') to a graph in-place.
    This is used for both interactive rendering and static image generation.

    - Nodes are grouped by directory ("archipelagos").
    - Node size is determined by its degree (number of connections).
    """
    if graph.number_of_nodes() == 0:
        return

    degrees = dict(graph.degree())
    max_deg = max(degrees.values()) if degrees else 0
    min_deg = min(degrees.values()) if degrees else 0

    for node, attrs in graph.nodes(data=True):
        # 1. Assign group based on directory for archipelago coloring
        folder = os.path.dirname(node) if "::" not in node else node.split("::")[0]
        attrs['group'] = folder if folder else "Root"

        # 2. Assign size based on degree
        degree = degrees.get(node, 0)
        if max_deg > min_deg:
            norm_degree = (degree - min_deg) / (max_deg - min_deg)
        else:
            norm_degree = 0
        
        # Base size of 5, up to 50 for the most connected nodes
        attrs['size'] = 5 + (norm_degree * 45)