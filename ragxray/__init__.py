"""ragxray — Zero-LLM chunk-boundary & retrieval debugger for RAG pipelines."""

__version__ = "1.0.0"

from .diagnostics import inspect_path
from .retriever import probe_path

__all__ = ["__version__", "inspect_path", "probe_path"]
