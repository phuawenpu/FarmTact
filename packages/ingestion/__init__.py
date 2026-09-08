"""FarmTact public-data ingestion API.

The package deliberately returns its own small dataclasses so it can be used before
the application's shared contracts are finalized.
"""

from .context import PublicContext, get_public_context, rebuild, refresh

__all__ = ["PublicContext", "get_public_context", "rebuild", "refresh"]
