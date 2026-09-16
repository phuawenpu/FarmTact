import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[2]


def test_local_launcher_rejects_historical_retired_worker_by_default(tmp_path):
    history = {'latest': 'v4', 'editions': [{'id': f'v{i}'} for i in range(1, 5)]}
    active = {'previous': 'v3', 'latest': 'v4'}
    history_path = tmp_path / 'registry.json'; history_path.write_text(json.dumps(history))
    active_path = tmp_path / 'active.json'; active_path.write_text(json.dumps(active))
    environment = {
        **os.environ,
        'FARMTACT_RELEASE_REGISTRY': str(history_path),
        'FARMTACT_ACTIVE_EDITIONS': str(active_path),
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/serve_editions_local.py'), 'v2'],
        cwd=ROOT, env=environment, text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert 'retired or not staged' in result.stderr


def test_generic_verifier_uses_active_and_history_apis_without_fixed_old_pair():
    source = (ROOT / 'scripts/verify_editions.py').read_text()
    assert "client.get('/api/releases/history')" in source
    assert "client.get('/api/releases')" in source
    assert "for edition in ('v1', 'v2')" not in source
    assert "client.get(f'/{retired_id}/api/v1/bootstrap')" in source
    assert "client.post(f'/{retired_id}/api/v1/planning-sessions'" in source
