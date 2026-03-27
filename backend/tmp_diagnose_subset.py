import json
from pathlib import Path
from app.services.document_processor import DocumentProcessor

root = Path(r"e:/xiangmudaima/shijuanshibie")
subject_dir = root / 'test' / '语文'
processor = DocumentProcessor()

nums = [302,295,294,291,290,289,287,286,285,283,282,278,275,274,272,271,269,267,263,259,256,255,254,251,246,239,238]

def find_file(num):
    for ext in ('.docx','.doc'):
        p = subject_dir / f"{num}{ext}"
        if p.exists():
            return p
    return None

def iter_nodes(nodes,path='root'):
    for i,n in enumerate(nodes,1):
        num = str(n.get('numbering') or '').strip() or f'idx{i}'
        p = f"{path}/{num}" if path!='root' else num
        yield n,p
        for t in iter_nodes(n.get('children') or [], p):
            yield t

def dup_issues(nodes,path='root'):
    out=[]
    nums=[]
    for i,n in enumerate(nodes,1):
        numbering=str(n.get('numbering') or '').strip()
        if numbering:
            nums.append((i,numbering,n))
    from collections import defaultdict
    mp=defaultdict(list)
    for i,no,n in nums:
        mp[no].append((i,n))
    for no,arr in mp.items():
        if len(arr)>1:
            out.append((path,no,[(i,str(n.get('rawText') or '')[:120],float(n.get('score') or 0.0)) for i,n in arr]))
    for i,n in enumerate(nodes,1):
        num = str(n.get('numbering') or '').strip() or f'idx{i}'
        child_path=f"{path}/{num}" if path!='root' else num
        out.extend(dup_issues(n.get('children') or [], child_path))
    return out

def agg(n):
    cs=n.get('children') or []
    s=float(n.get('score') or 0)
    if not cs:
        return s
    return s if s>0 else sum(agg(c) for c in cs)

for num in nums:
    fp=find_file(num)
    if not fp:
        print('\n###',num,'MISSING')
        continue
    out=processor.process(task_id=990000+num,file_path=str(fp),file_ext=fp.suffix.lower(),max_level=8,second_level_mode='auto',answer_section_patterns=None,score_patterns=None)
    roots=out.get('details',{}).get('outlineItems',[]) or []
    dups=dup_issues(roots)
    gaps=[]
    for n,p in iter_nodes(roots):
        cs=n.get('children') or []
        s=float(n.get('score') or 0)
        if not cs or s<=0:
            continue
        csum=sum(agg(c) for c in cs)
        if csum>0 and abs(s-csum)>0.11:
            gaps.append((p,s,csum,str(n.get('rawText') or '')[:120]))
    if not dups and not gaps:
        continue
    print(f"\n### {num} ({fp.name})")
    for p,no,arr in dups[:8]:
        print('DUP',p,'num=',no,'items=',arr)
    for g in gaps[:8]:
        print('GAP',g)
