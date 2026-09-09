#!/usr/bin/env python3
"""One bounded public refresh; no credentials, article crawling or inference."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.news import refresh

if __name__ == "__main__":
    import json
    result = refresh()
    print(json.dumps({"version": result["version"], "refreshed_at": result["refreshed_at"],
                      "records": len(result["records"]), "sources": result["sources"]}, indent=2))
