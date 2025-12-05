import logging
import os
import shutil
from pathlib import Path

# PyQt6 Imports
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtGui import QTextCursor

# App Imports
from app.gui.dialogs import DiagnosticsDialog
from app.gui.ui_setup import MainWindowUiMixin
from app.gui.ui_styles import AppStyles
from app.gui.workers import GraphBuilderWorker, LLMWorker
from app.services.project_analyzer import ProjectAnalyzer
from app.services.llm_interface import LLMInterface
from app.services.state_manager import StateManager

class MainWindow(QMainWindow, MainWindowUiMixin):
    def __init__(self, diagnostics=None):
        super().__init__()
        self.setWindowTitle("Code_Navigator")
        self.resize(1600, 900)
        
        self.analyzer = ProjectAnalyzer()
        self.llm = LLMInterface()
        self.llm.bind_analyzer(self.analyzer)
        self.state_manager = StateManager()
        
        AppStyles.apply_dark_theme(self)
        self.init_ui()
        
        # Connect Graph signals
        self.graph_widget.view_detail_changed.connect(self.on_view_detail_changed)
        self.graph_widget.mode_changed.connect(self.on_graph_mode_changed)

        # Connect Chat/Scope signals
        self.chat_widget.search_requested.connect(self.on_scope_search)
        self.chat_widget.scope_add_requested.connect(self.on_manual_scope_add)
        self.chat_widget.scope_extrapolate_requested.connect(self.on_extrapolate_scope)

        if diagnostics and any(d['status'] != 'ok' for d in diagnostics):
            DiagnosticsDialog(diagnostics, self).exec()

        last_proj = self.state_manager.get_last_project()
        if last_proj:
            self.load_project(last_proj)

    # --- Core Application Logic ---

    def on_chat_message(self, text, use_file, use_logic, use_scope):
        self.chat_widget.append_message("You", text)
        self.set_busy(True, "AI is thinking...", indeterminate=True)
        
        # Pass flags to worker
        self.llm_worker = LLMWorker(self.llm, text, use_file, use_logic, use_scope)
        self.llm_worker.response_received.connect(self.on_llm_response)
        self.llm_worker.start()

    def on_open_project_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Root")
        if path:
            self.load_project(path)

    def load_project(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Error", "Project path does not exist.")
            self.state_manager.remove_project(path)
            self.update_recent_menu()
            return

        self.setWindowTitle(f"Code_Navigator - {os.path.basename(path)}")
        self.status_label.setText(f"Loaded: {path}")
        
        self.state_manager.add_project(path)
        self.update_recent_menu()
        self.analyzer.set_project(path)
        
        self.file_model.setRootPath(path)
        self.file_tree.setRootIndex(self.file_model.index(path))
        
        self.graph_widget.render_graph(None)
        self.update_scope_display()
        
        self.on_scope_search("") 
        
        self.graph_widget.combo_mode.setCurrentIndex(1)
        self.graph_widget.chk_full.setChecked(False)
        self.on_graph_mode_changed("file_tree")
        
    def run_graph_builder(self, mode):
        if not self.analyzer.project_root:
            QMessageBox.warning(self, "Warning", "No project loaded.")
            return

        mode_map = {
            'file_tree': ("Scanning File Structure", "file_tree"),
            'dependency': ("Mapping Dependencies", "logic_graphs"),
            'scope': ("Processing Logic Scope", "scope")
        }
        title, worker_mode = mode_map.get(mode)
        
        self.set_busy(True, f"{title}...", indeterminate=True)
        
        self.builder_worker = GraphBuilderWorker(self.analyzer, worker_mode)
        self.builder_worker.progress.connect(self.on_progress)
        self.builder_worker.finished.connect(lambda: self.on_builder_finished(mode))
        self.builder_worker.start()

    def on_builder_finished(self, mode):
        self.set_busy(False, f"{mode.title().replace('_', ' ')} Complete.")
        
        mode_to_index = {"dependency": 0, "file_tree": 1, "scope": 2}
        if mode in mode_to_index:
            self.graph_widget.combo_mode.setCurrentIndex(mode_to_index[mode])
        
        self.on_graph_mode_changed(mode)
        self.on_scope_search("")

    def on_graph_mode_changed(self, mode):
        if not mode: return
        is_full = self.graph_widget.chk_full.isChecked()
        self.analyzer.load_graph(mode, is_full)
        graph = self.analyzer.get_graph()
        
        static_path = graph.graph.get('static_image_path')
        if static_path:
            self.graph_widget.render_static_image(static_path, title=f"Static Mode: {mode}")
            self.status_label.setText(f"View Mode: {mode} (Static Image)")
        else:
            self.graph_widget.render_graph(graph, title=f"Mode: {mode}")
            self.status_label.setText(f"View Mode: {mode} ({'Full' if is_full else 'Simple'})")

    def on_view_detail_changed(self, is_checked):
        modes = {0: "dependency", 1: "file_tree", 2: "scope"}
        current_mode = modes.get(self.graph_widget.combo_mode.currentIndex())
        self.on_graph_mode_changed(current_mode)

    def on_progress(self, current, total, message):
        self.status_label.setText(message)
        if total > 0: self.progress_bar.setRange(0, total); self.progress_bar.setValue(current)
        else: self.progress_bar.setRange(0, 0)

    def clear_cache(self):
        if not self.analyzer.project_root: return
        reply = QMessageBox.question(self, "Clear Data", "Delete all cached data?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.analyzer.clear_project_cache()
            self.graph_widget.render_graph(None)
            self.scope_list.clear()
            self.status_label.setText("Project Data Cleared.")
            self.on_scope_search("")

    def on_file_double_clicked(self, index):
        file_path = self.file_model.filePath(index)
        if os.path.isfile(file_path): self.display_file(file_path)

    def display_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f: self.editor.setText(f.read())
            self.status_label.setText(f"Viewing: {os.path.basename(path)}")
        except Exception as e: self.status_label.setText(f"Error reading file: {e}")

    def on_node_selected(self, node_id):
        if not self.analyzer.project_root: return
        rel_path = node_id.split("::")[0]
        full_path = os.path.join(self.analyzer.project_root, rel_path)
        if os.path.exists(full_path):
            self.display_file(full_path)
            if "::" in node_id:
                symbol = node_id.split("::")[1]
                if self.editor.find(symbol):
                    cursor = self.editor.textCursor()
                    cursor.select(QTextCursor.SelectionType.WordUnderCursor)
                    self.editor.setTextCursor(cursor); self.editor.centerCursor()
            else: self.editor.moveCursor(QTextCursor.MoveOperation.Start); self.editor.ensureCursorVisible()

    # --- Scope & Search (Manual) ---
    def on_scope_search(self, text):
        results = self.analyzer.search_files(text)
        self.chat_widget.update_search_results(results)

    def on_manual_scope_add(self, file_path):
        self.on_add_to_scope(file_path)

    def on_extrapolate_scope(self, file_path):
        self.set_busy(True, f"Extrapolating: {os.path.basename(file_path)}...")
        
        files = self.analyzer.extrapolate_dependencies(file_path)
        
        if not files:
            QMessageBox.information(self, "Extrapolation Failed", "No dependencies found or Logic Graph not built.\nPlease run 'Map Dependencies' first.")
            self.set_busy(False, "Ready")
            return
            
        added = self.analyzer.add_to_scope(files)
        self.update_scope_display()
        self.set_busy(False, f"Extrapolated: Added {len(added)} related files.")

    def on_add_to_scope(self, node_id):
        file_path = node_id.split("::")[0]
        added = self.analyzer.add_to_scope([file_path])
        if added:
            self.update_scope_display()
            self.status_label.setText(f"Added {file_path} to Scope.")

    def remove_from_scope(self, text):
        self.analyzer.update_scope(files_to_remove=[text])
        self.update_scope_display()
        self.status_label.setText(f"Removed {text} from Scope.")

    def update_scope_display(self):
        self.scope_list.clear()
        self.scope_list.addItems(sorted(self.analyzer.get_scope_list()))

    def update_recent_menu(self):
        self.recent_menu.clear()
        projects = self.state_manager.get_recent_projects()
        if not projects: self.recent_menu.addAction("No recent projects").setEnabled(False)
        else:
            for p in projects:
                act = p.get('name', 'Unknown')
                path = p.get('path')
                if path:
                    self.recent_menu.addAction(act, lambda checked, p=path: self.load_project(p))

    # --- Chat ---
    def on_chat_message(self, text):
        self.chat_widget.append_message("You", text)
        self.set_busy(True, "AI is thinking...", indeterminate=True)
        self.llm_worker = LLMWorker(self.llm, text)
        self.llm_worker.response_received.connect(self.on_llm_response)
        self.llm_worker.start()

    def on_llm_response(self, result: dict):
        self.set_busy(False, "Ready")
        answer = result.get("answer", "No response from AI.")
        self.chat_widget.append_message("AI", answer)
        self.chat_widget.enable_input()
        self.update_scope_display()

    def set_busy(self, busy, msg="", indeterminate=False):
        self.progress_bar.setVisible(busy)
        self.status_label.setText(msg)
        if busy:
            if indeterminate: self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100); self.progress_bar.setValue(0)
        self.gen_toolbar.setEnabled(not busy)