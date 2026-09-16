from packages.ai_contracts import typed_reference_catalog
from services.api.conversations import AdvisorReply, _validate_reply, _validation_issues, _bounded_model_context


def test_confirmed_shortfall_never_accepts_total_demand_fact():
    booked='strategy:resilient.metrics.booked_shortfall_kg'
    total='strategy:resilient.metrics.all_demand_shortfall_kg'
    tools={booked:306,total:412.01,'planning:demand_semantics':'booked covers confirmed orders only'}
    conversation={'snapshot_ref':{'kind':'planning','hash':'frozen'},'_tool_results':tools,
        '_typed_facts':typed_reference_catalog(tools,snapshot_hash='frozen'),
        '_evidence':[],'_highlight_refs':[],'_snapshot':{'batches':[],'recipes':[]}}
    content='Resilient has the lowest confirmed-demand shortfall.'
    bad=AdvisorReply(content=content,fact_refs=[total],relationship='answer')
    errors,_=_validate_reply(bad,conversation,require_typed_fact=True)
    assert 'demand_scope_mismatch' in {x['code'] for x in _validation_issues(errors)}
    good=AdvisorReply(content=content,fact_refs=[booked],relationship='answer')
    errors,_=_validate_reply(good,conversation,require_typed_fact=True)
    assert not errors
    context,facts=_bounded_model_context(conversation,'demand_analyst')
    assert booked in facts and total in facts
    assert context['planning:demand_semantics']==tools['planning:demand_semantics']
