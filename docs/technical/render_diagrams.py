"""Render chapter Mermaid diagrams locally and record source hashes.

Requires Mermaid CLI and its Chromium/system libraries. No runtime application or
provider request. Use --puppeteer-config only for local build sandbox configuration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
CHAPTERS=['v11-guided-production-planning.md', 'v10-grounding-followup.md','v9-ai-followup.md','v8-remediation-report.md','ai-provider-and-council.md','numerical-models-and-growth.md',
          'game-backend-and-state-machines.md','system-data-and-evidence.md']

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mmdc',default='mmdc')
    parser.add_argument('--puppeteer-config',type=Path)
    args=parser.parse_args()
    out=HERE/'figures/diagrams';out.mkdir(parents=True,exist_ok=True)
    manifest={'tool':'Mermaid CLI','version':subprocess.check_output([args.mmdc,'--version'],text=True).strip(),'chapters':{}}
    with tempfile.TemporaryDirectory(prefix='farmtact-diagrams-') as temp:
        temp=Path(temp)
        config=temp/'mermaid.json'
        config.write_text(json.dumps({'theme':'neutral','securityLevel':'strict','deterministicIds':True,'deterministicIDSeed':'farmtact-report-20260911','flowchart':{'htmlLabels':False},'fontFamily':'DejaVu Sans'}))
        for name in CHAPTERS:
            chapter=HERE/name
            blocks=re.findall(r'```mermaid\s*\n(.*?)\n```',chapter.read_text(),re.S)
            command=[args.mmdc,'-i',str(chapter),'-o',str(temp/name),'-a',str(out),'-c',str(config),'-j','2']
            if args.puppeteer_config:command+=['-p',str(args.puppeteer_config)]
            result=subprocess.run(command,capture_output=True,text=True)
            if result.returncode:raise RuntimeError(f'{name}: {result.stderr}')
            manifest['chapters'][name]=[{'file':f'figures/diagrams/{chapter.stem}-{i}.svg','source_sha256':hashlib.sha256(block.encode()).hexdigest()} for i,block in enumerate(blocks,1)]
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Rendered {sum(map(len,manifest["chapters"].values()))} Mermaid diagrams; wrote source-hash manifest.')

if __name__=='__main__':main()
