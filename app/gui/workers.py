from PyQt6.QtCore import QThread, pyqtSignal

class GraphBuilderWorker(QThread):
    """
    Worker thread for running heavy graph analysis tasks off the main UI thread.
    """
    finished = pyqtSignal()
    progress = pyqtSignal(int, int, str) 
    
    def __init__(self, analyzer, mode):
        super().__init__()
        self.analyzer = analyzer
        self.mode = mode # 'file_tree', 'logic_graphs', 'scope'

    def run(self):
        def callback(c, t, m):
            self.progress.emit(c, t, m)
        
        try:
            if self.mode == 'file_tree':
                self.analyzer.build_file_tree(callback)
            elif self.mode == 'logic_graphs':
                self.analyzer.build_logic_graphs(callback)
            elif self.mode == 'scope':
                self.analyzer.build_scope_graph(callback)
        except Exception as e:
            self.progress.emit(0, 0, f"Error: {str(e)}")
        
        self.finished.emit()

class LLMWorker(QThread):
    """
    Worker thread for handling LLM requests to prevent UI freezing during generation.
    Updated to support granular context toggling.
    """
    response_received = pyqtSignal(dict)
    
    def __init__(self, llm_interface, prompt, use_file=True, use_logic=True, use_scope=True): 
        super().__init__()
        self.llm = llm_interface
        self.prompt = prompt
        self.use_file = use_file
        self.use_logic = use_logic
        self.use_scope = use_scope
        
    def run(self): 
        # Pass the context flags to the LLM Interface
        result = self.llm.process_user_query(
            self.prompt, 
            use_file=self.use_file, 
            use_logic=self.use_logic, 
            use_scope=self.use_scope
        )
        self.response_received.emit(result)