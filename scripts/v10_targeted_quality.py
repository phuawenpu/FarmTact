#!/usr/bin/env python3
"""Score V10's preregistered planning/Council subset from saved records only.

Uses the unchanged full-suite case checks. Direct, invite, research and vision
are explicitly excluded; this is not a claim of a new complete five-workflow run.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from packages.ai_quality import evaluate_suite
from scripts.deepseek_quality_e2e import (
    collect_cases, collect_planning_cases, _workflow_integrity, _apply_human_review,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conversation-replay', type=Path, required=True)
    parser.add_argument('--planning-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    transcript = json.loads(args.conversation_replay.read_text())
    planning = json.loads(args.planning_report.read_text())
    cases, messages, attempts = collect_cases(transcript, 'conversation')
    planning_cases, planning_messages = collect_planning_cases(planning)
    cases.extend(planning_cases)
    messages.update(planning_messages)
    report = evaluate_suite(cases, messages, attempts)
    required = {'planning', 'council'}
    integrity = _workflow_integrity(cases, messages, required)
    report.update(
        execution_scope='stored_actual_outputs_no_new_inference',
        required_workflows=sorted(required),
        explicitly_excluded_workflows=['direct', 'invite', 'research', 'vision'],
        workflow_integrity=integrity,
        source_artifacts=dict(conversation=str(args.conversation_replay), planning=str(args.planning_report)),
        scope_basis='reports/v10/live-plan.json, recorded before any V10 provider calls',
        provider_calls=0,
    )
    if integrity['status'] != 'PASS' or any(case.workflow not in required for case in cases):
        report['status'] = 'FAIL'
    _apply_human_review(report, None)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: report.get(key) for key in ('status', 'case_count', 'failed_case_ids')}))
    return 0 if report['status'] == 'PASS_AUTOMATED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
