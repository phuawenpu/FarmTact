"""Stage the next unpublished edition for operator-only acceptance.

The existing public registry remains unchanged. No publication number is reserved
until the pinned candidate passes acceptance and the normal publisher is invoked.
Previously published edition images and their data are preserved by machine_config.
"""
import argparse
import json
from pathlib import Path
import sys
import subprocess
import time
import shlex

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.publish_edition import (PublicationError,git,remote_registry,remote_active,load_json,validate_notes,make_entry,append_only,build_image,deploy_shared,IMAGE,COMMIT)


def prepare_restage(previous, remote):
    """Reset only an unpublished candidate's local manifest; retain its data."""
    from scripts.publish_edition import command, shared_settings
    entry = previous['entry']
    edition = entry['id']
    if edition != 'v' + str(len(remote['editions']) + 1):
        raise PublicationError('Cannot restage a published edition')
    settings = shared_settings()
    code = ("import json,os; from pathlib import Path; "
            "p=Path('/data/releases/registry.json'); old=json.loads(p.read_text()); "
            "expected=" + repr(remote) + "; candidate=" + repr(entry) + "; "
            "assert old==expected or old==dict(latest=candidate['id'],editions=[*expected['editions'],candidate]); "
            "n=p.with_suffix('.restage'); n.write_text(json.dumps(expected)); os.replace(n,p)")
    command(['fly','ssh','console','--app','farmtact','--machine',settings['machine_id'],
             '--container',edition,'--command','python -c '+shlex.quote(code)])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--edition',required=True);parser.add_argument('--source-commit',required=True);parser.add_argument('--notes',type=Path,required=True);parser.add_argument('--image');parser.add_argument('--record',type=Path,required=True)
    args=parser.parse_args()
    if git('status','--porcelain'):raise PublicationError('Stage a clean committed candidate')
    if not COMMIT.fullmatch(args.source_commit) or git('rev-parse','HEAD')!=args.source_commit:raise PublicationError('Candidate source must equal committed HEAD')
    remote=remote_registry('https://farmtact.fly.dev')
    active=remote_active('https://farmtact.fly.dev')
    if remote!=load_json(ROOT/'config/releases/registry.json'):raise PublicationError('Local and public registries differ')
    if args.edition!='v'+str(len(remote['editions'])+1):raise PublicationError('Only the next unpublished edition may be staged')
    notes=load_json(args.notes);validate_notes(notes)
    previous=load_json(args.record) if args.record.exists() else None
    image=args.image or build_image(args.edition,args.source_commit)
    if not IMAGE.fullmatch(image):raise PublicationError('Pinned candidate image required')
    entry=make_entry(args.edition,notes,image,args.source_commit,remote)
    candidate={'latest':args.edition,'editions':[*remote['editions'],entry]};append_only(remote,candidate)
    if previous and previous.get('status') == 'STAGED':
        prepare_restage(previous, remote)
    args.record.write_text(json.dumps(dict(status='BUILT',public_registry_changed=False,entry=entry),indent=2)+'\n')
    for attempt in range(3):
        try:
            deploy_shared(candidate, active, staged=args.edition)
            break
        except subprocess.CalledProcessError as exc:
            # The image identity never changes during registry-readiness retries.
            if 'MANIFEST_UNKNOWN' not in (exc.stderr or '') or attempt==2:raise
            time.sleep(10)
    if remote_registry('https://farmtact.fly.dev')!=remote:raise PublicationError('Staging unexpectedly changed public registry')
    args.record.write_text(json.dumps(dict(status='STAGED',public_registry_changed=False,entry=entry),indent=2)+'\n')
    print('Staged '+args.edition+' for operator acceptance; public registry unchanged.')

if __name__=='__main__':main()
