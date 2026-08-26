"""Open Memory Protocol (OMP) reference implementation.

Public API:
- MemoryDirectory: a validated OMP memory root
- MemoryFile: a single markdown file within an OMP memory root
- load_memory(path): load and validate an OMP memory directory
- validate_memory(path): validate structure without loading contents
- HarnessContext: the object a conforming harness passes to an agent
"""

from open_memory_protocol.types import MemoryDirectory, MemoryFile, HarnessContext
from open_memory_protocol.loader import load_memory
from open_memory_protocol.validator import validate_memory, ValidationError

__version__ = "0.1.0"
__all__ = [
    "MemoryDirectory",
    "MemoryFile",
    "HarnessContext",
    "load_memory",
    "validate_memory",
    "ValidationError",
]
