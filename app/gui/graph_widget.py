import logging
import json
import networkx as nx
import numpy as np
import os
import base64 
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QComboBox, QHBoxLayout, 
                             QLabel, QMenu, QSlider, QFrame, QCheckBox, QMessageBox)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QAction, QCursor

# Import the template
from .graph_template import GRAPH_HTML_TEMPLATE

# --- Constants ---
INITIAL_LOAD_SIZE = 1500
CHUNK_LOAD_SIZE = 1000

class WebChannelBridge(QObject):
    node_clicked = pyqtSignal(str)
    node_right_clicked = pyqtSignal(str) 

    @pyqtSlot(str)
    def js_callback(self, message): self.node_clicked.emit(message)
    @pyqtSlot(str)
    def js_right_click(self, message): self.node_right_clicked.emit(message)
    @pyqtSlot(str)
    def js_log(self, message): print(f"[Graph Renderer] {message}")

class GraphWidget(QWidget):
    node_selected = pyqtSignal(str)
    mode_changed = pyqtSignal(str)
    add_to_scope_requested = pyqtSignal(str)
    view_detail_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.cached_graph = None
        self.cached_title = ""
        self.displayed_nodes = set()
        self.sorted_nodes_for_loading = []
        self._is_page_loaded = False
        self._pending_chunk_load = False
        self._is_static_mode = False

        # --- Toolbar ---
        self.controls = QHBoxLayout()
        self.controls.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_mode = QLabel("Mode:")
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Dependency (Logic)", "File Tree (Structure)", "Scope (Deep Focus)"])
        self.combo_mode.currentIndexChanged.connect(self._on_mode_combo_index_changed)
        
        self.chk_full = QCheckBox("Full Detail")
        self.chk_full.setToolTip("Checked: View all nodes, loaded in chunks.\nUnchecked: View a simplified overview.")
        self.chk_full.setChecked(False) 
        self.chk_full.toggled.connect(self.view_detail_changed.emit)

        self.lbl_expand = QLabel("Expansion:")
        self.slider_expand = QSlider(Qt.Orientation.Horizontal)
        self.slider_expand.setRange(50, 400); self.slider_expand.setValue(100)
        self.slider_expand.setFixedWidth(120)
        self.slider_expand.valueChanged.connect(self.on_expand_change)
        
        self.controls.addWidget(self.lbl_mode)
        self.controls.addWidget(self.combo_mode)
        self.controls.addWidget(self.chk_full)
        self.controls.addStretch()
        self.controls.addWidget(self.lbl_expand)
        self.controls.addWidget(self.slider_expand)
        self.layout.addLayout(self.controls)

        # --- Web View ---
        self.web_view = QWebEngineView()
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.web_view.loadFinished.connect(self._on_page_load_finished)
        
        self.bridge = WebChannelBridge()
        self.bridge.node_clicked.connect(self.node_selected.emit)
        self.bridge.node_right_clicked.connect(self._on_node_context_menu)
        
        self.channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.channel)
        self.channel.registerObject("bridge", self.bridge)
        
        self.layout.addWidget(self.web_view)

    def _on_page_load_finished(self, ok):
        self._is_page_loaded = True
        if ok and self._pending_chunk_load:
            self._pending_chunk_load = False
            total = len(self.sorted_nodes_for_loading)
            current = len(self.displayed_nodes)
            self.web_view.page().runJavaScript(f"window.updateLoadingProgress({current}, {total});")
            QTimer.singleShot(50, self._load_next_chunk)

    def render_static_image(self, image_path: str, title="Static Graph"):
        self._is_static_mode = True
        self.set_controls_enabled(False)

        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            image_uri = f"data:image/png;base64,{encoded_string}"
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    html, body {{ 
                        margin: 0; padding: 0; width: 100%; height: 100%; 
                        background-color: #282c34; color: white;
                        display: flex; align-items: center; justify-content: center;
                        font-family: sans-serif; overflow: hidden;
                    }}
                    img {{ width: 100%; height: 100%; object-fit: contain; }}
                    .watermark {{
                        position: absolute; top: 10px; left: 10px; color: rgba(255,255,255,0.8);
                        background: rgba(0,0,0,0.6); padding: 5px 10px; border-radius: 5px;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="watermark">{title}</div>
                <img src="{image_uri}" alt="Static graph render"/>
            </body>
            </html>
            """
            self.web_view.setHtml(html)

        except Exception as e:
            self.logger.error(f"Failed to load static image: {e}")
            self.web_view.setHtml(f"<h3>Error loading image:</h3><p>{e}</p>")

    def set_controls_enabled(self, enabled: bool):
        self.combo_mode.setEnabled(enabled)
        self.chk_full.setEnabled(enabled)
        self.slider_expand.setEnabled(enabled)

    def render_graph(self, nx_graph, title="Graph"):
        if self._is_static_mode:
            self.set_controls_enabled(True)
            self._is_static_mode = False

        self.cached_graph = nx_graph
        self.cached_title = title
        self.displayed_nodes.clear()
        self.sorted_nodes_for_loading.clear()
        self._is_page_loaded = False
        self._pending_chunk_load = False

        self._render_html(None, title)
        QTimer.singleShot(0, self._prepare_and_render_deferred)

    def _prepare_and_render_deferred(self):
        nx_graph = self.cached_graph
        title = self.cached_title

        if not nx_graph or nx_graph.number_of_nodes() == 0:
            self.web_view.setHtml("<html><body style='background:#282c34;color:#888;'><h3>No Graph Data</h3></body></html>")
            return

        is_full_mode = self.chk_full.isChecked()
        is_large_graph = nx_graph.number_of_nodes() > INITIAL_LOAD_SIZE

        initial_nodes = []
        final_title = title

        if is_full_mode and is_large_graph:
            degrees = dict(nx_graph.degree())
            self.sorted_nodes_for_loading = sorted(degrees, key=degrees.get, reverse=True)
            initial_nodes = self.sorted_nodes_for_loading[:INITIAL_LOAD_SIZE]
            self.displayed_nodes.update(initial_nodes)
            
            if len(self.displayed_nodes) < len(self.sorted_nodes_for_loading):
                self._pending_chunk_load = True
        else:
            initial_nodes = list(nx_graph.nodes())
            final_title += " (Overview)" if not is_full_mode else " (Full)"

        subgraph = nx_graph.subgraph(initial_nodes).copy()
        self._render_html(subgraph, final_title)

    def _load_next_chunk(self):
        try:
            if not self.cached_graph or not self.sorted_nodes_for_loading or not self._is_page_loaded: return

            start = len(self.displayed_nodes)
            end = start + CHUNK_LOAD_SIZE
            new_ids = self.sorted_nodes_for_loading[start:end]

            if not new_ids: return

            new_subgraph = self.cached_graph.subgraph(new_ids)
            connecting_edges = []
            for u, v, data in self.cached_graph.edges(new_ids, data=True):
                if u in self.displayed_nodes or v in self.displayed_nodes:
                    connecting_edges.append((u, v, data))
            
            new_nodes_data = self._format_nodes(new_subgraph)
            all_new_edges = list(new_subgraph.edges(data=True)) + connecting_edges
            new_edges_data = self._format_edges(all_new_edges)
            
            nodes_json = json.dumps(list(new_nodes_data), default=self._default_serializer)
            edges_json = json.dumps(list(new_edges_data), default=self._default_serializer)

            self.web_view.page().runJavaScript(f"addDataToGraph({nodes_json}, {edges_json});")
            self.displayed_nodes.update(new_ids)
            
            total = len(self.sorted_nodes_for_loading)
            current = len(self.displayed_nodes)
            self.web_view.page().runJavaScript(f"window.updateLoadingProgress({current}, {total});")

            if len(self.displayed_nodes) < len(self.sorted_nodes_for_loading):
                QTimer.singleShot(0, self._load_next_chunk)
            else:
                self.web_view.page().runJavaScript("window.hideLoadingIndicator();")
        except Exception as e:
            self.logger.error("Chunk load error", exc_info=True)

    def _render_html(self, graph, title):
        if graph is None:
            html = self._get_html_template(title, "[]", "[]", False, False)
            self.web_view.setHtml(html)
            return

        is_massive = graph.number_of_nodes() > 2500
        nodes_data = self._format_nodes(graph)
        edges_data = self._format_edges(graph.edges(data=True))
        
        try:
            nodes_json = json.dumps(list(nodes_data), default=self._default_serializer)
            edges_json = json.dumps(list(edges_data), default=self._default_serializer)
            html = self._get_html_template(title, nodes_json, edges_json, is_massive, self._pending_chunk_load)
            self.web_view.setHtml(html)
        except Exception as e:
            self.web_view.setHtml(f"Error: {e}")

    def _format_nodes(self, graph):
        # Generates the JSON object for Vis.js
        return (
            {
                "id": str(n), 
                "label": str(attr.get("label", os.path.basename(str(n)))),
                "group": attr.get("group", "Default"), 
                # CRITICAL: We pass the 'title' attribute directly. 
                # 'title' is the tooltip content. If it contains HTML, Vis.js renders it.
                "title": attr.get("title", str(n)), 
                "value": attr.get("size", 15), 
                "mass": attr.get("mass", 1),
                "font": {"color": "white", "strokeWidth": 0}
            }
            for n, attr in graph.nodes(data=True)
        )

    def _format_edges(self, edges):
        return (
            {"from": str(u), "to": str(v), "arrows": "to", "color": {"color": d.get("color", "#666"), "opacity": 0.5}, "dashes": d.get("style") == "dashed"} 
            for u, v, d in edges
        )

    def _default_serializer(self, obj):
        if isinstance(obj, (np.integer, int)): return int(obj)
        if isinstance(obj, (np.floating, float)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        raise TypeError(f"Type {type(obj)} not serializable")

    def on_expand_change(self, value):
        if self._is_page_loaded:
            self.web_view.page().runJavaScript(f"applyExpansion({value});")

    def _on_mode_combo_index_changed(self, index):
        modes = {0: "dependency", 1: "file_tree", 2: "scope"}
        self.mode_changed.emit(modes.get(index))

    def _on_node_context_menu(self, node_id):
        menu = QMenu(self)
        action_scope = QAction(f"Add '{os.path.basename(node_id)}' to Scope", self)
        action_scope.triggered.connect(lambda: self.add_to_scope_requested.emit(node_id))
        menu.addAction(action_scope)
        menu.exec(QCursor.pos())

    def _get_html_template(self, title, nodes_json, edges_json, is_massive, chunk_loading_active):
        if is_massive:
            physics_config = "enabled: false"
            edges_smooth = "type: 'continuous', enabled: false"
            layout_algo = "improvedLayout: false"
        else:
            physics_config = """
                enabled: true,
                stabilization: { enabled: true, iterations: 1000, fit: true, updateInterval: 50 },
                barnesHut: { gravitationalConstant: -8000, centralGravity: 0.3, springLength: 200, springConstant: 0.04, damping: 0.09, avoidOverlap: 0.5 }
            """
            edges_smooth = "type: 'continuous'"
            layout_algo = "improvedLayout: true"

        return GRAPH_HTML_TEMPLATE.format(
            title=title,
            nodes_json=nodes_json,
            edges_json=edges_json,
            edges_smooth=edges_smooth,
            layout_algo=layout_algo,
            physics_config=physics_config,
            js_bool_is_massive='true' if is_massive else 'false',
            chunk_loading_js='true' if chunk_loading_active else 'false'
        )