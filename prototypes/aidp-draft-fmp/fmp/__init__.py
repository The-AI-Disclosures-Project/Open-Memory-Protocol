"""Federated Memory Protocol (FMP), AIDP draft v0.1.

- fmp.schema     : the wire types (memory records, uploads, search, info)
- fmp.store      : reference SQLite backend, and a read-only backend over the ACP transcript index
- fmp.server     : FastAPI app exposing the /fmp/* endpoints
- fmp.client     : FMPClient (one server) and FederatedMemory (many servers, one view)
- fmp.middleware : LangChain create_agent middleware (search_memory / remember tools + transcript hook)
"""

from fmp.client import FederatedMemory, FMPClient, ServerConfig
from fmp.middleware import FMPMiddleware
from fmp.server import create_app
from fmp.store import ACPIndexStore, SQLiteStore

__version__ = "0.1.0"
FMP_VERSION = "0.1"
__all__ = [
    "ACPIndexStore",
    "FMPClient",
    "FMPMiddleware",
    "FederatedMemory",
    "SQLiteStore",
    "ServerConfig",
    "create_app",
]
