"""One authenticated model-list request under the same process egress policy as service."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.api.store import Store,now
from services.api.egress import install
from runtime.deepseek_gateway import DeepSeekGateway,RunBudget
store=Store()
if not store.reserve_calls(1):raise SystemExit('Development inference budget unavailable')
install()
with DeepSeekGateway.from_config('config/deepseek_runtime.json',budget=RunBudget(max_requests=1,max_reserved_output_tokens=0,max_wall_seconds=20)) as gateway:
    models=gateway.list_models()
report={'status':'PASS','occurred_at':now(),'actual_requests':1,'destination':'https://api.deepseek.com/models','models':sorted(models),'policy':'Python socket audit hook and fixed provider gateway; production OS egress still required'}
Path('reports/provider_egress_probe.json').write_text(json.dumps(report,indent=2)+'\n')
print('Official DeepSeek request passed process egress policy; report saved.')
