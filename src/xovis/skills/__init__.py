"""
Xovis SDK - Agentic Skills Layer

Operates at the boundary of the Control and State Planes.
This package contains the toolkits and skills required for autonomous AI agents
(e.g., OpenAI, Anthropic, LangChain) to orchestrate Xovis hardware natively.
"""

from .toolkit import XovisAIToolkit

# SchemaAnalyst is an internal-only skill for firmware discovery and SDK evolution.
# It is excluded from public releases.
try:
    from .discovery import SchemaAnalyst

    _HAS_SCHEMA_ANALYST = True
except ImportError:
    SchemaAnalyst = None
    _HAS_SCHEMA_ANALYST = False

__all__ = ["XovisAIToolkit", "SchemaAnalyst"]
