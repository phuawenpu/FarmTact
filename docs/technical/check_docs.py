"""Check documentation links, source line anchors, fences and generated diagrams.

This is a documentation integrity check, not an application or scientific test.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
from urllib.parse import unquote
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def main():
    files=[ROOT/'README.md',ROOT/'FarmTact_Build_Specification.md',ROOT/'FarmTact_DeepSeek_Runtime_Specification.md',*sorted((ROOT/'docs').rglob('*.md'))]
    errors=[];links=0;diagrams=0
    for file in files:
        content=file.read_text()
        if len(re.findall(r'^```',content,re.M))%2:errors.append(f'{file.relative_to(ROOT)}: unbalanced code fences')
        prose=re.sub(r'^```.*?^```[^\n]*','',content,flags=re.M|re.S)
        for match in re.finditer(r'!?\[[^\]\n]*\]\(([^)\n]+)\)',prose):
            target=match.group(1).strip().split(' "',1)[0].strip('<>')
            if re.match(r'^[a-z][a-z0-9+.-]*:',target,re.I) or target.startswith('#'):continue
            links+=1
            path,_,fragment=unquote(target).partition('#')
            local=(file.parent/path).resolve()
            if not local.exists():errors.append(f'{file.relative_to(ROOT)}: missing {target}');continue
            if fragment.startswith('L'):
                m=re.fullmatch(r'L(\d+)(?:-L?(\d+))?',fragment)
                if m and int(m.group(2) or m.group(1))>len(local.read_text().splitlines()):errors.append(f'{file.relative_to(ROOT)}: line anchor out of range {target}')
    manifest=HERE/'figures/diagrams/manifest.json'
    if manifest.exists():
        for name,rows in json.loads(manifest.read_text())['chapters'].items():
            blocks=re.findall(r'```mermaid\s*\n(.*?)\n```',(HERE/name).read_text(),re.S)
            if len(rows)!=len(blocks):errors.append(f'{name}: diagram count drift')
            for row,block in zip(rows,blocks):
                diagrams+=1
                if hashlib.sha256(block.encode()).hexdigest()!=row['source_sha256']:errors.append(f'{name}: diagram source hash drift {row["file"]}')
                try:ET.parse(HERE/row['file'])
                except (OSError,ET.ParseError):errors.append(f'{name}: invalid SVG {row["file"]}')
    report={'markdown_files':len(files),'relative_links_checked':links,'rendered_diagrams_checked':diagrams,'errors':errors}
    print(json.dumps(report,indent=2))
    return bool(errors)

if __name__=='__main__':sys.exit(main())
