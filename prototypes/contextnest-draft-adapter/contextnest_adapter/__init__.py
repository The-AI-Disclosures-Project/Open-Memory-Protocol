"""Context Nest proposal v0.1 (early-draft-specs/draft-v0.1-contextnest.md) as an agent plug.

The memory system is the `ctx` reference implementation, running against a local nest
directory or a hosted nest. This package is only the harness side:

- contextnest_adapter.ctx        : subprocess client for the `ctx` binary (query, search, add)
- contextnest_adapter.middleware : LangChain create_agent middleware (tools + context injection)
"""

from contextnest_adapter.ctx import CtxClient, CtxError, NestDocument, QueryResult
from contextnest_adapter.middleware import ContextNestMiddleware

__version__ = "0.1.0"
__all__ = ["ContextNestMiddleware", "CtxClient", "CtxError", "NestDocument", "QueryResult"]
