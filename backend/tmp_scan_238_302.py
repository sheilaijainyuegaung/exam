import json
from pathlib import Path
from app.services.document_processor import DocumentProcessor

root = Path(r"e:/xiangmudaima/shijuanshibie")
subject_dir = root / 'test' / '语文'
processor = DocumentProcessor()

def find_file(num):
    for ext in ('.docx','.doc','.pdf'):
        p = subject_dir / f"{num}{ext}"
        if p.exists():
            return p
    return None

def iter_nodes(nodes, path=''):
    for i,n in enumerate(nodes,1):
        num = str(n.get('numbering') or '').strip() or f'idx{i}'
        p = f"{path}/{num}" if path else num
        yield n,p
        cs = n.get('children') or []
        yield from iter_nodes(cs,p)

def collect_dup(nodes):
    out=[]
    def walk(ns,path='root'):
        nums=[str(n.get('numbering') or '').strip() for n in ns if str(n.get('numbering') or '').strip()]
        dups=sorted(set([x for x in nums if nums.count(x)>1]))
        if dups:
            out.append((path,dups))
        for i,n in enumerate(ns,1):
            num=str(n.get('numbering') or '').strip() or f'idx{i}'
            walk(n.get('children') or [], f"{path}/{num}")
    walk(nodes)
    return out

for num in [302,301,300,299,298,297,296,295,294,293,292,291,290,289,288,287,286,285,284,283,282,281,280,279,278,277,276,275,274,272,271,270,269,268,267,266,265,264,263,262,261,260,259,258,257,256,255,254,253,252,251,250,249,248,247,246,244,243,241,240,239,238]:
    fp = find_file(num)
    if not fp:
        print(f"{num}\tMISSING")
        continue
    try:
        out = processor.process(
            task_id=980000+num,
            file_path=str(fp),
            file_ext=fp.suffix.lower(),
            max_level=8,
            second_level_mode='auto',
            answer_section_patterns=None,
            score_patterns=None,
        )
    except Exception as e:
        print(f"{num}\tFAILED\t{type(e).__name__}:{e}")
        continue
    roots = out.get('details',{}).get('outlineItems',[]) or []
    dups = collect_dup(roots)
    empty_nodes = []
    for n,p in iter_nodes(roots):
        if (not (n.get('children') or [])) and not str(n.get('numbering') or '').strip() and not str(n.get('rawText') or '').strip() and float(n.get('score') or 0)<=0:
            empty_nodes.append(p)
    # parent score display mismatch
    def agg(n):
        cs=n.get('children') or []
        s=float(n.get('score') or 0)
        if not cs:
            return s
        return s if s>0 else sum(agg(c) for c in cs)
    score_mismatch=[]
    for n,p in iter_nodes(roots):
        cs=n.get('children') or []
        s=float(n.get('score') or 0)
        if not cs or s<=0:
            continue
        child_sum=sum(agg(c) for c in cs)
        if child_sum>0 and abs(s-child_sum)>0.11:
            score_mismatch.append((p,s,child_sum))
    # count paren/circled under arabic leaf-like maybe suspicious
    suspicious=[]
    for n,p in iter_nodes(roots):
        tok=str(n.get('_tokenType') or '')
        if tok in ('paren_arabic','circled') and not (n.get('children') or []):
            raw=str(n.get('rawText') or '')
            if '阅读' in raw and '回答' in raw:
                suspicious.append(p)
    print(f"{num}\tOK\troots={len(roots)}\tdups={len(dups)}\tempty={len(empty_nodes)}\tscoreGap={len(score_mismatch)}\tsusp={len(suspicious)}\tfile={fp.name}")
