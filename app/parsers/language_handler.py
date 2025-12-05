from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Definition:
    name: str
    type: str  # 'function', 'class', 'struct'
    start_byte: int
    end_byte: int
    signature: str = "" 
    content: str = ""   
    calls: List[str] = field(default_factory=list)
    docstring: Optional[str] = None

@dataclass
class ParseResult:
    file_path: str
    language: str
    definitions: List[Definition] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    content: str = "" 
    error: Optional[str] = None

class BaseParser:
    """Interface for language parsers."""
    def parse_file(self, file_path: str, detailed: bool = False) -> ParseResult:
        raise NotImplementedError