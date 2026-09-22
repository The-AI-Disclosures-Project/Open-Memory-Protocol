"""LangChain harness for the Open Memory Protocol (Packer draft v0.2).

Public API:
- OpenMemoryMiddleware: an AgentMiddleware implementing the four-rule harness contract
- create_omp_agent(memory_root, model, ...): convenience wrapper around create_agent
"""

from omp_langchain.middleware import OpenMemoryMiddleware, create_omp_agent
from omp_langchain.models import resolve_model
from omp_langchain.trace import ConsoleSink, JsonlSink, ListSink, TraceMiddleware

__version__ = "0.1.0"
__all__ = [
    "ConsoleSink",
    "JsonlSink",
    "ListSink",
    "OpenMemoryMiddleware",
    "TraceMiddleware",
    "create_omp_agent",
    "resolve_model",
]
