"""Acceptance inspects the complete seven findings independently of personas."""
import pytest
from fastapi.testclient import TestClient
from packages.agents import ROLES, council_review_issues
from services.api.app import create_app
from services.api.store import Store


def findings():
    return [dict(role=r,status='validated',recommendation='proceed_simulation') for r in ROLES]


@pytest.mark.parametrize('kind',['partial','rejected','dissent','duplicate','reordered'])
def test_gate_rejects_incomplete_or_unsupported_findings(kind):
    claims=findings()
    if kind=='partial':claims.pop()
    if kind=='rejected':claims[2]['status']='rejected'
    if kind=='dissent':claims[2]['recommendation']='hold'
    if kind=='duplicate':claims[2]['role']=claims[1]['role']
    if kind=='reordered':claims.reverse()
    assert council_review_issues(claims)
    assert not council_review_issues(findings())


@pytest.mark.parametrize('mode',['complete','partial','rejected','failed_before_claims'])
def test_mission_gate_preserves_alternatives_and_budget(monkeypatch,mode):
    import services.api.council as council_module
    monkeypatch.setenv('DEEPSEEK_API_KEY','contract-test-only')
    observed={}
    def council(computed,run_id,emit,cancelled,**kwargs):
        observed.update(kwargs)
        kwargs['budget'].reserve(1536)
        assert kwargs['market_signals']['status']=='not_connected'
        if mode=='failed_before_claims':raise RuntimeError('contract-test')
        rows=findings()
        if mode=='partial':rows.pop()
        if mode=='rejected':rows[2]['status']='rejected'
        return rows,[]
    monkeypatch.setattr(council_module,'council',council)
    store=Store('sqlite://');app=create_app(store,start_worker=False)
    with TestClient(app) as client:
        client.get('/api/v1/bootstrap')
        t=store.authenticate(client.cookies.get('farmtact_session'))
        item=client.post('/api/v1/planning-runs',json={'council':True},headers={'Idempotency-Key':'gate'}).json()
        store.claim(t,item['id']);app.state.worker.execute(t,item['id'])
        result=client.get('/api/v1/planning-runs/'+item['id']).json()
        assert result['strategies'] and any(s['status']=='FEASIBLE' for s in result['strategies'])
        assert result['inference_budget']['reserved_calls']==9
        assert result['inference_budget']['unused_released']==8
        assert result['council_version']=='seven-agent-council-v1'
        if mode in ('partial','rejected'):
            assert result['status']=='REVIEW_WITHHELD'
            assert result['evidence_validation']['status']=='withheld'
            assert not result.get('accepted_strategy_id')
        else:
            assert result['status']=='ACCEPTED_FOR_SIMULATION'
            assert result['acceptance']['policy_version']=='automatic-development-v2'
            assert result['evidence_validation']['basis']==('numerical-baseline' if mode=='failed_before_claims' else 'seven-agent-findings')
        replay=client.get('/api/v1/planning-runs/'+item['id']+'/replay').json()
        assert replay['market_signals']==result['market_signals']
        assert replay['evidence_validation']==result['evidence_validation']
