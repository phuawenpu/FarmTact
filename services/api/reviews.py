"""Public, release-bundled reviewer evidence. Never reads tenant records or user paths."""
import json
from fastapi import HTTPException
from services.api.views import ROOT


def install_routes(app):
    @app.get('/api/v1/reviews')
    def reviews():
        path = ROOT / 'config/review_panel.json'
        if not path.is_file():
            raise HTTPException(503, 'The independent review panel is being prepared.')
        # A curated build artifact, produced and verified before release.
        return json.loads(path.read_text())
