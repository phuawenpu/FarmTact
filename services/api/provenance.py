"""Immutable edition identity; development trees explicitly remain unsealed."""
import os
from pathlib import Path
import re


def runtime_provenance():
    path=Path(__file__).resolve().parents[2]/'config/build-source.txt'
    commit=path.read_text().strip() if path.is_file() else None
    sealed=bool(commit and re.fullmatch(r'[0-9a-f]{40}',commit))
    return dict(edition=os.environ.get('FARMTACT_EDITION','development'),source_commit=commit if sealed else None,
                source_status='immutable_edition' if sealed and os.environ.get('FARMTACT_EDITION') else 'unsealed_development',
                source_identity_basis='edition_image_build_source',cross_edition_state_shared=False)
