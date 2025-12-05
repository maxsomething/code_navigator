from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QDialogButtonBox, QFrame, QScrollArea, QWidget)
from PyQt6.QtGui import QColor, QPalette

class DiagnosticsDialog(QDialog):
    def __init__(self, checks, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Checks")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Startup Diagnostics</b>"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.checks_layout = QVBoxLayout(content_widget)
        
        for check in checks:
            self.add_check_row(check)
            
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.accept)
        layout.addWidget(btn_box)

    def add_check_row(self, check):
        row = QHBoxLayout()
        
        name = QLabel(f"{check['name']}:")
        name.setFixedWidth(150)
        name.setStyleSheet("font-weight: bold;")
        
        status = QLabel(check['status'].upper())
        status.setFixedWidth(80)
        
        msg = QLabel(check['message'])
        msg.setWordWrap(True)
        
        # Color coding
        palette = status.palette()
        if check['status'] == 'ok':
            status.setStyleSheet("color: green; font-weight: bold;")
        elif check['status'] == 'error':
            status.setStyleSheet("color: red; font-weight: bold;")
        else:
            status.setStyleSheet("color: orange; font-weight: bold;")
        
        row.addWidget(name)
        row.addWidget(status)
        row.addWidget(msg)
        
        self.checks_layout.addLayout(row)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.checks_layout.addWidget(line)