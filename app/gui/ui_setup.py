from pathlib import Path
from PyQt6.QtWidgets import (QDockWidget, QTextEdit, QListWidget, QProgressBar, 
                             QLabel, QTreeView, QToolBar, QStyle, QAbstractItemView, QApplication)
from PyQt6.QtGui import (QFont, QAction, QIcon, QFileSystemModel, QKeySequence, 
                         QPainter, QPixmap, QColor)
from PyQt6.QtCore import Qt, QSize, QDir

# App Imports
from app.gui.graph_widget import GraphWidget
from app.gui.chat_widget import ChatWidget

class MainWindowUiMixin:
    """
    A mixin class containing UI initialization and setup methods for MainWindow.
    """
    def init_ui(self):
        # --- Central Editor ---
        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setFont(QFont("Fira Code", 11))
        if not self.editor.fontInfo().exactMatch():
            self.editor.setFont(QFont("Monospace", 11))
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #282c34; color: #abb2bf;
                selection-background-color: #3e4451;
            }
        """)
        self.setCentralWidget(self.editor)

        # --- Docks ---
        self._setup_docks()

        # --- Toolbars & Menus ---
        self.setup_menu()
        self.setup_toolbar()

        # --- Status Bar ---
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 0 5px;")
        self.statusBar().addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)

    def _setup_docks(self):
        # --- Left Dock: File Explorer ---
        self.explorer_dock = QDockWidget("Project Explorer", self)
        self.explorer_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(str(Path.home()))
        self.file_model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs | QDir.Filter.Files)
        
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(str(Path.home())))
        self.file_tree.setAnimated(True)
        self.file_tree.setIndentation(20)
        self.file_tree.setSortingEnabled(True)
        self.file_tree.setColumnWidth(0, 200)
        for i in range(1, 4): self.file_tree.hideColumn(i)
        self.file_tree.setHeaderHidden(True)
        self.file_tree.doubleClicked.connect(self.on_file_double_clicked)
        
        self.explorer_dock.setWidget(self.file_tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.explorer_dock)

        # --- Left Dock: Scope Manager ---
        self.scope_dock = QDockWidget("Active Scope", self)
        self.scope_list = QListWidget()
        self.scope_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.scope_list.setToolTip("Files selected for Deep Logic analysis.\nDouble-click to remove.")
        self.scope_list.itemDoubleClicked.connect(lambda item: self.remove_from_scope(item.text()))
        
        self.scope_dock.setWidget(self.scope_list)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.scope_dock)
        
        self.tabifyDockWidget(self.explorer_dock, self.scope_dock)
        self.explorer_dock.raise_()

        # --- Right Dock: Graph ---
        self.graph_dock = QDockWidget("Dependency Navigator", self)
        self.graph_widget = GraphWidget()
        self.graph_widget.node_selected.connect(self.on_node_selected)
        self.graph_widget.mode_changed.connect(self.on_graph_mode_changed)
        self.graph_widget.add_to_scope_requested.connect(self.on_add_to_scope)
        self.graph_dock.setWidget(self.graph_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.graph_dock)

        # --- Bottom Dock: Chat ---
        self.chat_dock = QDockWidget("AI Assistant", self)
        self.chat_widget = ChatWidget()
        self.chat_widget.message_sent.connect(self.on_chat_message)
        self.chat_dock.setWidget(self.chat_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.chat_dock)

    def setup_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        act_open = QAction("Open Project...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self.on_open_project_dialog)
        file_menu.addAction(act_open)
        
        self.recent_menu = file_menu.addMenu("Open &Recent")
        self.update_recent_menu()
        
        file_menu.addSeparator()
        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        act_exit.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(act_exit)
        
        view_menu = menubar.addMenu("&View")
        # --- FIX ---
        # Add the action returned by toggleViewAction() directly.
        # The action's text will automatically match the dock's title.
        view_menu.addAction(self.explorer_dock.toggleViewAction())
        view_menu.addAction(self.graph_dock.toggleViewAction())
        view_menu.addAction(self.scope_dock.toggleViewAction())
        view_menu.addAction(self.chat_dock.toggleViewAction())

    def _create_themed_icon(self, standard_pixmap):
        base_icon = self.style().standardIcon(standard_pixmap)
        pixmap = base_icon.pixmap(QSize(24, 24))
        if pixmap.isNull(): return base_icon

        colored_pixmap = QPixmap(pixmap.size())
        colored_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(colored_pixmap)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(colored_pixmap.rect(), QColor("#e0e0e0"))
        painter.end()

        return QIcon(colored_pixmap)

    def setup_toolbar(self):
        self.gen_toolbar = QToolBar("Analysis Tools")
        self.gen_toolbar.setIconSize(QSize(18, 18))
        self.gen_toolbar.setMovable(False)
        self.gen_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(self.gen_toolbar)
        
        actions = [
            ("1. Scan Files", "SP_DirIcon", "Fast: Builds the directory structure graph", 'file_tree'),
            ("2. Map Dependencies", "SP_FileDialogDetailedView", "Medium: Parses imports to map connections", 'dependency'),
            ("3. Process Scope", "SP_ComputerIcon", "Slow: Deeply analyzes logic of files in Active Scope", 'scope')
        ]

        for text, icon_name, tooltip, mode in actions:
            icon = self._create_themed_icon(getattr(QStyle.StandardPixmap, icon_name))
            btn = QAction(icon, text, self)
            btn.setToolTip(tooltip)
            btn.triggered.connect(lambda checked, m=mode: self.run_graph_builder(m))
            self.gen_toolbar.addAction(btn)
            self.gen_toolbar.addSeparator()
        
        icon_trash = self._create_themed_icon(QStyle.StandardPixmap.SP_TrashIcon)
        btn_clear = QAction(icon_trash, "Clear Project Data", self)
        btn_clear.setToolTip("Delete all cached graphs and vectors for this project")
        btn_clear.triggered.connect(self.clear_cache)
        self.gen_toolbar.addAction(btn_clear)