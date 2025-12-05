import os
import logging
from typing import List

from .language_handler import BaseParser, ParseResult, Definition

try:
    from tree_sitter import Language, Parser, Query
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Query = None

GRAMMARS = {}

if TREE_SITTER_AVAILABLE:
    def load_grammar(name, pkg):
        """
        Loads a grammar, handling the v0.22+ requirement to wrap PyCapsules 
        in a Language object.
        """
        try:
            if hasattr(pkg, 'language'): 
                ptr = pkg.language()
                # If ptr is a PyCapsule (standard in newer bindings), wrap it.
                # If it's already a Language object (older bindings/wrappers), use as is.
                if isinstance(ptr, Language):
                    GRAMMARS[name] = ptr
                else:
                    try:
                        GRAMMARS[name] = Language(ptr)
                    except TypeError:
                        # Fallback for older versions or unexpected types
                        GRAMMARS[name] = ptr
            else:
                logging.getLogger("PolyglotParser").debug(f"Package {pkg} has no 'language' attribute.")
        except Exception as e:
            logging.getLogger("PolyglotParser").debug(f"Failed to load grammar {name}: {e}")

    # Load supported grammars
    try: import tree_sitter_c; load_grammar('c', tree_sitter_c)
    except ImportError: pass
    try: import tree_sitter_cpp; load_grammar('cpp', tree_sitter_cpp)
    except ImportError: pass
    try: import tree_sitter_python; load_grammar('python', tree_sitter_python)
    except ImportError: pass
    try: import tree_sitter_lua; load_grammar('lua', tree_sitter_lua)
    except ImportError: pass
    try: import tree_sitter_java; load_grammar('java', tree_sitter_java)
    except ImportError: pass
    try: import tree_sitter_rust; load_grammar('rust', tree_sitter_rust)
    except ImportError: pass
    try: import tree_sitter_javascript; load_grammar('javascript', tree_sitter_javascript)
    except ImportError: pass

class PolyglotParser(BaseParser):
    EXTENSION_MAP = {
        '.c': 'c', '.h': 'c',
        '.cpp': 'cpp', '.hpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
        '.py': 'python',
        '.lua': 'lua',
        '.java': 'java',
        '.rs': 'rust',
        '.js': 'javascript', '.mjs': 'javascript', '.jsx': 'javascript'
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        if not TREE_SITTER_AVAILABLE:
            self.logger.critical("tree-sitter library not installed. Parsing disabled.")
        else:
            self.parser = Parser()

        # Queries specifically designed to capture Structure (definitions) and Logic (calls/imports)
        self._queries = {
            'c': {
                'import': """(preproc_include path: (_) @import)""",
                'def': """(function_definition declarator: (function_declarator declarator: (identifier) @name) body: (_) @body) @def""",
                'call': """(call_expression function: (identifier) @call_name)"""
            },
            'cpp': {
                'import': """(preproc_include path: (_) @import)""",
                'def': """
                    (function_definition declarator: (function_declarator declarator: (identifier) @name) body: (_) @body) @def
                    (class_specifier name: (type_identifier) @name) @def
                """,
                'call': """(call_expression function: (identifier) @call_name)"""
            },
            'python': {
                'import': """
                    (import_statement name: (dotted_name) @import)
                    (import_from_statement module_name: (dotted_name) @import)
                """,
                'def': """
                    (function_definition name: (identifier) @name body: (_) @body) @def
                    (class_definition name: (identifier) @name body: (_) @body) @def
                """,
                'call': """(call function: (identifier) @call_name)"""
            },
            'java': {
                'import': """(import_declaration) @import""",
                'def': """
                    (method_declaration name: (identifier) @name body: (_) @body) @def
                    (class_declaration name: (identifier) @name body: (_) @body) @def
                """,
                'call': """(method_invocation name: (identifier) @call_name)"""
            },
            'javascript': {
                'import': """(import_statement source: (string) @import)""",
                'def': """
                    (function_declaration name: (identifier) @name body: (_) @body) @def
                    (class_declaration name: (identifier) @name body: (_) @body) @def
                """,
                'call': """(call_expression function: (identifier) @call_name)"""
            }
        }

    def _get_language_id(self, file_path: str) -> str:
        _, ext = os.path.splitext(file_path)
        return self.EXTENSION_MAP.get(ext.lower())

    def _get_captures(self, query: Query, node) -> List:
        """Adapts to breaking changes in the tree-sitter Python API (v0.22+)."""
        if hasattr(query, 'captures'):
            return query.captures(node)

        try:
            from tree_sitter import QueryCursor
            try:
                cursor = QueryCursor()
                raw_captures = cursor.captures(query, node)
            except TypeError:
                cursor = QueryCursor(query)
                raw_captures = cursor.captures(node)

            results = []
            if isinstance(raw_captures, dict):
                for name, nodes in raw_captures.items():
                    if not isinstance(nodes, list): nodes = [nodes]
                    for n in nodes:
                        results.append((n, name))
                return results

            for item in raw_captures:
                if isinstance(item, tuple) and len(item) >= 2:
                    captured_node = item[0]
                    capture_info = item[1]
                    if isinstance(capture_info, int):
                        if hasattr(query, 'capture_name_for_id'):
                            name = query.capture_name_for_id(capture_info)
                        else:
                            name = str(capture_info)
                        results.append((captured_node, name))
                    else:
                        results.append((captured_node, str(capture_info)))
            return results

        except Exception as e:
            self.logger.error(f"Tree-sitter capture logic failed: {e}")
            return []

    def _run_query(self, lang, query_str, node, capture_name=None):
        if not query_str: return []
        try:
            q = Query(lang, query_str)
            captures = self._get_captures(q, node)
            results = []
            for n, name in captures:
                if capture_name is None or name == capture_name:
                    results.append(n.text.decode('utf8').strip())
            return results
        except Exception:
            return []

    def parse_file(self, file_path: str, detailed: bool = False) -> ParseResult:
        lang_id = self._get_language_id(file_path)
        if not TREE_SITTER_AVAILABLE:
            return ParseResult(file_path, str(lang_id), error="Tree-sitter library missing.")
        
        if not lang_id or lang_id not in GRAMMARS:
             return ParseResult(file_path, str(lang_id), error=f"Language {lang_id} not supported.")

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content_str = f.read()
                content_bytes = content_str.encode('utf8')

            lang_obj = GRAMMARS[lang_id]
            self.parser.language = lang_obj
            
            tree = self.parser.parse(content_bytes)
            
            # 1. Imports
            import_query = self._queries.get(lang_id, {}).get('import', "")
            imports = self._run_query(lang_obj, import_query, tree.root_node, capture_name="import")
            
            # Clean imports
            clean_imports = []
            for imp in imports:
                i = imp.replace('import ', '').replace(';', '').replace('"', '').replace("'", "")
                clean_imports.append(i.strip())

            definitions = []
            
            if detailed:
                def_query_str = self._queries.get(lang_id, {}).get('def', "")
                call_query_str = self._queries.get(lang_id, {}).get('call', "")
                
                if def_query_str:
                    q_def = Query(lang_obj, def_query_str)
                    captures = self._get_captures(q_def, tree.root_node)
                    
                    processed_nodes = set()
                    
                    for node, name in captures:
                        if name == 'def' and node.id not in processed_nodes:
                            processed_nodes.add(node.id)
                            
                            def_text = node.text.decode('utf8')
                            def_name = "unknown"
                            
                            # Attempt to find the @name capture within this node's range
                            for sub_n, sub_name in captures:
                                if sub_name == 'name' and sub_n.start_byte >= node.start_byte and sub_n.end_byte <= node.end_byte:
                                    def_name = sub_n.text.decode('utf8')
                                    break
                            
                            calls = []
                            if call_query_str:
                                calls = self._run_query(lang_obj, call_query_str, node, capture_name="call_name")
                                calls = list(set(calls))

                            definitions.append(Definition(
                                name=def_name,
                                type='function', 
                                start_byte=node.start_byte,
                                end_byte=node.end_byte,
                                content=def_text,
                                calls=calls
                            ))

            return ParseResult(file_path, lang_id, definitions=definitions, imports=clean_imports, content=content_str)
        
        except Exception as e:
            self.logger.error(f"Parsing failed for {file_path}: {e}")
            return ParseResult(file_path, lang_id, error=str(e))