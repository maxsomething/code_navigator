import os
from pathlib import Path
import logging

class DependencyResolver:
    """
    Resolves import strings to concrete file paths within the project.
    Strictly ignores files that do not exist in the provided file list.
    """
    def __init__(self, all_files: set[str]):
        # all_files must be relative paths from project root
        self.all_files = all_files
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Optimization: Map filenames to full relative paths (e.g., 'utils.h' -> 'src/utils.h')
        self.basename_map = {os.path.basename(f): f for f in all_files}
        
        # Optimization: Map Python/Lua module dots to paths
        self.module_map = self._build_module_map(all_files)

    def _build_module_map(self, all_files):
        """Creates a map from 'package.module' to 'package/module.py'."""
        module_map = {}
        for f in all_files:
            if f.endswith('.py') or f.endswith('.lua'):
                # Convert 'app/services/main.py' -> 'app.services.main'
                no_ext = os.path.splitext(f)[0]
                mod_name = no_ext.replace(os.path.sep, '.')
                
                module_map[mod_name] = f
                
                # Handle __init__ packages
                if mod_name.endswith('.__init__'):
                    pkg_name = mod_name[:-9] # strip .__init__
                    module_map[pkg_name] = f
        return module_map

    def _sanitize(self, import_str: str) -> str:
        """Removes quotes, brackets, and whitespace."""
        clean = import_str.strip()
        # Remove surrounding quotes or brackets common in C/C++
        # Loop ensures nested artifacts are removed
        while (clean.startswith('"') and clean.endswith('"')) or \
              (clean.startswith('<') and clean.endswith('>')) or \
              (clean.startswith("'") and clean.endswith("'")):
            clean = clean[1:-1]
        return clean.strip()

    def resolve(self, source_file: str, import_str: str) -> str | None:
        """
        Returns the specific project file path for an import, or None if external.
        """
        target = self._sanitize(import_str)
        if not target:
            return None

        # 1. Direct Match / Module Match
        if target in self.all_files: return target
        if target in self.module_map: return self.module_map[target]

        # 2. Relative Path Resolution
        try:
            source_dir = os.path.dirname(source_file)
            if target == '.': 
                abs_candidate = source_dir
            else:
                abs_candidate = os.path.normpath(os.path.join(source_dir, target))
            
            # Check exact match
            if abs_candidate in self.all_files:
                return abs_candidate
                
            # Check Windows/Linux separator mismatch
            alt_candidate = abs_candidate.replace('\\', '/')
            if alt_candidate in self.all_files:
                return alt_candidate
        except Exception:
            pass

        # 3. Basename Fallback (Fuzzy lookup for C/C++ includes)
        basename = os.path.basename(target)
        if basename in self.basename_map:
            return self.basename_map[basename]

        return None