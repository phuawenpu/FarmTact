"""Export all technical chapters as a printable, offline HTML reading copy.

Uses Python Markdown (documentation-only dependency). Embeds local figures and
renders tables/code. Mermaid and TeX remain source notation in this offline copy;
GitHub renders the Markdown originals. No script, CDN, network or provider call.
"""
from pathlib import Path
import argparse
import base64
import html
import re
from urllib.parse import quote
import markdown

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHAPTERS = ['README.md', 'ai-provider-and-council.md', 'numerical-models-and-growth.md',
            'game-backend-and-state-machines.md', 'system-data-and-evidence.md',
            'gaps-and-next-iteration.md', 'reproducibility.md']


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    sections=[]
    for index,name in enumerate(CHAPTERS):
        path=HERE/name
        body=markdown.markdown(path.read_text(),extensions=['tables','fenced_code','toc'])
        # Embed only files referenced by authored documentation; this is a local
        # build script, not an HTTP file-serving endpoint.
        def image(match):
            source=match.group(1)
            if re.match(r'^[a-z]+:',source):return match.group(0)
            asset=(HERE/source).resolve()
            asset.relative_to(ROOT)
            mime='image/svg+xml' if asset.suffix=='.svg' else 'image/png'
            data=base64.b64encode(asset.read_bytes()).decode()
            return f'src="data:{mime};base64,{data}"'
        body=re.sub(r'src="([^"]+)"',image,body)
        def link(match):
            target=html.unescape(match.group(1))
            if target.startswith('#'):
                return f'href="#chapter-{index}-{quote(target[1:])}"'
            if re.match(r'^[a-z]+:',target):return match.group(0)
            local,_,fragment=target.partition('#')
            linked=(HERE/local).resolve()
            if linked.parent==HERE and linked.name in CHAPTERS:
                number=CHAPTERS.index(linked.name)
                return f'href="#chapter-{number}'+('-'+quote(fragment) if fragment else '')+'"'
            rel=linked.relative_to(ROOT).as_posix()
            return 'href="https://github.com/phuawenpu/FarmTact/blob/main/'+quote(rel)+'"'
        body=re.sub(r'href="([^"]+)"',link,body)
        body=re.sub(r'id="([^"]+)"',lambda m:f'id="chapter-{index}-{m.group(1)}"',body)
        sections.append(f'<article id="chapter-{index}">{body}</article>')
    style='''body{font:17px/1.6 Georgia,serif;color:#18332f;max-width:1120px;margin:40px auto;padding:0 24px}h1,h2,h3,table,nav{font-family:system-ui,sans-serif}h1{line-height:1.2}h2{border-bottom:1px solid #cadbd4;padding-top:24px}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px;display:block;overflow:auto}td,th{border:1px solid #cadbd4;padding:9px;text-align:left;vertical-align:top}th{background:#eef5f1}code,pre{font-family:monospace;font-size:.9em}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:16px;background:#f4f6f4}a{color:#215e93}article{margin-top:70px}blockquote{border-left:4px solid #b67120;margin-left:0;padding-left:20px}.notice{background:#fcf4e8;padding:16px}@media print{body{margin:0;max-width:none;font-size:10pt}article{break-before:page}h2,h3{break-after:avoid}table{font-size:8pt}tr,img,pre{break-inside:avoid}a{color:inherit;text-decoration:none}}'''
    nav=' | '.join(f'<a href="#chapter-{i}">{html.escape(Path(name).stem.replace("-"," "))}</a>' for i,name in enumerate(CHAPTERS))
    document='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>FarmTact scientific implementation report</title><style>'+style+'</style><body><nav>'+nav+'</nav><p class="notice">Offline reading copy. Figures are embedded. Mermaid diagrams and TeX equations retain readable source notation here; use the GitHub Markdown chapters for their rendered forms. External evidence links require GitHub access.</p>'+''.join(sections)+'</body></html>'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(document)
    print(f'Wrote {args.output}: {len(CHAPTERS)} chapters, embedded figures, no external scripts.')

if __name__=='__main__':main()
