from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

class AppStyles:
    """ Manages the visual styling for the application. """
    
    @staticmethod
    def apply_dark_theme(app_window):
        """Sets a VS Code-like Dark Theme using Palette and Stylesheets."""
        # Color Palette
        dark_bg = QColor("#282c34")
        darker_bg = QColor("#21252b")
        text_color = QColor("#abb2bf")
        accent_color = QColor("#61afef")
        
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, dark_bg)
        palette.setColor(QPalette.ColorRole.WindowText, text_color)
        palette.setColor(QPalette.ColorRole.Base, darker_bg)
        palette.setColor(QPalette.ColorRole.AlternateBase, dark_bg)
        palette.setColor(QPalette.ColorRole.ToolTipBase, text_color)
        palette.setColor(QPalette.ColorRole.ToolTipText, darker_bg)
        palette.setColor(QPalette.ColorRole.Text, text_color)
        palette.setColor(QPalette.ColorRole.Button, dark_bg)
        palette.setColor(QPalette.ColorRole.ButtonText, text_color)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, accent_color)
        palette.setColor(QPalette.ColorRole.Highlight, accent_color)
        palette.setColor(QPalette.ColorRole.HighlightedText, darker_bg)
        
        app_window.setPalette(palette)
        
        # Specific Widget Styling (QSS)
        app_window.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #282c34;
                color: #abb2bf;
            }
            QLabel {
                color: #abb2bf;
                background: transparent;
            }
            /* --- Menus --- */
            QMenuBar {
                background-color: #21252b;
                color: #abb2bf;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #3e4451;
            }
            QMenu {
                background-color: #21252b;
                color: #abb2bf;
                border: 1px solid #181a1f;
            }
            QMenu::item:selected {
                background-color: #3e4451;
            }
            /* --- Toolbar --- */
            QToolBar {
                background: #21252b;
                border-bottom: 1px solid #1e2127;
                spacing: 5px;
                padding: 3px;
            }
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px 8px;
                color: #e0e0e0; /* Bright text for toolbar */
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #3e4451;
                border: 1px solid #4b5263;
            }
            QToolButton:pressed {
                background-color: #282c34;
            }
            /* --- Docks --- */
            QDockWidget {
                titlebar-close-icon: url(:/close.png);
                titlebar-normal-icon: url(:/float.png);
                border: 1px solid #1e2127;
                color: #abb2bf;
                font-weight: bold;
            }
            QDockWidget::title { 
                background: #21252b; 
                padding-left: 5px; 
                padding-top: 4px;
            }
            /* --- Lists & Trees --- */
            QTreeView, QListWidget, QTextEdit {
                background-color: #21252b;
                border: 1px solid #181a1f;
                color: #abb2bf;
                outline: 0;
            }
            QTreeView::item:hover, QListWidget::item:hover {
                background: #2c313a;
            }
            QTreeView::item:selected, QListWidget::item:selected {
                background: #3e4451;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #282c34;
                color: #abb2bf;
                border: none;
                padding: 4px;
            }
            /* --- Dropdowns --- */
            QComboBox {
                background-color: #21252b;
                border: 1px solid #181a1f;
                border-radius: 3px;
                padding: 3px;
                color: #abb2bf;
                min-width: 6em;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 0px;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }
            QComboBox QAbstractItemView {
                background-color: #21252b;
                color: #abb2bf;
                selection-background-color: #3e4451;
                border: 1px solid #181a1f;
            }
            /* --- Buttons --- */
            QPushButton {
                background-color: #3e4451;
                border: 1px solid #4b5263;
                border-radius: 3px;
                color: #abb2bf;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #4b5263;
            }
            /* --- Scrollbars --- */
            QScrollBar:vertical {
                border: none;
                background: #282c34;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #4b5263;
                min-height: 20px;
                border-radius: 5px;
            }
            /* --- Status Bar --- */
            QStatusBar {
                background: #21252b;
                color: #9da5b4;
            }
            QProgressBar {
                border: 1px solid #4b5263;
                border-radius: 3px;
                text-align: center;
                background: #282c34;
                color: #abb2bf;
            }
            QProgressBar::chunk {
                background-color: #61afef;
            }
        """)