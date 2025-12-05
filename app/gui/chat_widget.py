from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QLabel, QSplitter, 
                             QListWidget, QCheckBox, QFrame)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QColor

class ChatWidget(QWidget):
    """
    Split-view widget: 
    Left: LLM Chat with Context Toggles
    Right: Direct File Scoping (bypassing LLM)
    """
    # Emits: (message_text, use_file_context, use_logic_context, use_scope_context)
    message_sent = pyqtSignal(str, bool, bool, bool) 
    search_requested = pyqtSignal(str) 
    scope_add_requested = pyqtSignal(str) 
    scope_extrapolate_requested = pyqtSignal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Main Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.splitter)

        # --- LEFT: Chat Area ---
        self.chat_container = QWidget()
        chat_layout = QVBoxLayout(self.chat_container)
        chat_layout.setContentsMargins(5, 5, 5, 5)

        self.header = QLabel("AI Assistant")
        self.header.setStyleSheet("color: #aaa; font-weight: bold;")
        chat_layout.addWidget(self.header)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 10))
        self.chat_display.setStyleSheet("background-color: #1e2127; color: #dcdfe4; border: 1px solid #3e4451;")
        chat_layout.addWidget(self.chat_display)

        # --- Context Toggles ---
        context_layout = QHBoxLayout()
        context_layout.setSpacing(15)
        
        self.chk_file = QCheckBox("File Context")
        self.chk_file.setToolTip("Include raw code content of relevant files (High Token Usage)")
        self.chk_file.setChecked(True)
        
        self.chk_logic = QCheckBox("Logic Context")
        self.chk_logic.setToolTip("Include high-level dependency map (Imports/Includes)")
        self.chk_logic.setChecked(True)
        
        self.chk_scope = QCheckBox("Scope Context")
        self.chk_scope.setToolTip("Include detailed function signatures and call graphs of the Active Scope")
        self.chk_scope.setChecked(True)

        for chk in [self.chk_file, self.chk_logic, self.chk_scope]:
            chk.setStyleSheet("""
                QCheckBox { color: #abb2bf; }
                QCheckBox::indicator { width: 13px; height: 13px; }
            """)
            context_layout.addWidget(chk)
        
        context_layout.addStretch()
        chat_layout.addLayout(context_layout)

        # Input Area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask AI about the code...")
        self.input_field.setStyleSheet("background-color: #282c34; color: white; padding: 5px; border: 1px solid #555;")
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("background-color: #61afef; color: black; font-weight: bold; padding: 5px 15px;")
        self.send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        chat_layout.addLayout(input_layout)

        # --- RIGHT: Direct Scope Manager ---
        self.scope_container = QWidget()
        scope_layout = QVBoxLayout(self.scope_container)
        scope_layout.setContentsMargins(5, 5, 5, 5)

        self.scope_header = QLabel("Quick Scope (Direct)")
        self.scope_header.setToolTip("Search and add files to scope manually, bypassing the AI.")
        self.scope_header.setStyleSheet("color: #98c379; font-weight: bold;")
        scope_layout.addWidget(self.scope_header)

        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Type filename to find...")
        self.search_bar.setStyleSheet("background-color: #282c34; color: white; padding: 5px; border: 1px solid #98c379;")
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        scope_layout.addWidget(self.search_bar)

        # Results List
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget { background-color: #21252b; color: #abb2bf; border: 1px solid #3e4451; }
            QListWidget::item:hover { background: #2c313a; }
            QListWidget::item:selected { background: #3e4451; color: white; }
        """)
        self.results_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.results_list.itemSelectionChanged.connect(self.on_selection_changed)
        scope_layout.addWidget(self.results_list)

        # Buttons Layout
        btn_layout = QHBoxLayout()
        
        # Extrapolate Button
        self.extrapolate_btn = QPushButton("Extrapolate Scope")
        self.extrapolate_btn.setToolTip("Finds all files that rely on this file (up) AND all files this file relies on (down).")
        self.extrapolate_btn.setStyleSheet("""
            QPushButton { background-color: #e5c07b; color: black; font-weight: bold; padding: 5px; }
            QPushButton:disabled { background-color: #3e4451; color: #5c6370; }
        """)
        self.extrapolate_btn.setEnabled(False)
        self.extrapolate_btn.clicked.connect(self.on_extrapolate_clicked)
        
        btn_layout.addWidget(self.extrapolate_btn)
        scope_layout.addLayout(btn_layout)

        # Help Label
        help_lbl = QLabel("Double-click to add single | Click Extrapolate for deps")
        help_lbl.setStyleSheet("color: #5c6370; font-size: 10px; font-style: italic;")
        help_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        scope_layout.addWidget(help_lbl)

        # Add widgets to splitter
        self.splitter.addWidget(self.chat_container)
        self.splitter.addWidget(self.scope_container)
        
        # Set initial sizes (70% Chat, 30% Scope)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)

    # --- Chat Logic ---
    def send_message(self):
        text = self.input_field.text().strip()
        if text:
            # Emit text plus the boolean state of the context toggles
            self.message_sent.emit(
                text,
                self.chk_file.isChecked(),
                self.chk_logic.isChecked(),
                self.chk_scope.isChecked()
            )
            self.input_field.clear()
            self.input_field.setEnabled(False)
            self.send_btn.setEnabled(False)

    def append_message(self, sender, text):
        color = "#61afef" if sender == "You" else "#98c379"
        formatted_text = text.replace("\n", "<br>")
        html = f"<div style='margin-bottom: 10px;'><b><font color='{color}'>{sender}:</font></b><br><span style='color: #abb2bf;'>{formatted_text}</span></div>"
        self.chat_display.append(html)
        sb = self.chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def enable_input(self):
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input_field.setFocus()

    # --- Scope Logic ---
    def on_search_text_changed(self, text):
        self.search_requested.emit(text)

    def update_search_results(self, files):
        self.results_list.clear()
        self.results_list.addItems(files)
        self.extrapolate_btn.setEnabled(False)

    def on_selection_changed(self):
        self.extrapolate_btn.setEnabled(bool(self.results_list.selectedItems()))

    def on_item_double_clicked(self, item):
        self.scope_add_requested.emit(item.text())
        item.setBackground(QColor("#98c379"))
        item.setForeground(QColor("#000000"))

    def on_extrapolate_clicked(self):
        item = self.results_list.currentItem()
        if item:
            self.scope_extrapolate_requested.emit(item.text())