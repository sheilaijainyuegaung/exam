from pathlib import Path
from app.services.document_processor import DocumentProcessor

root=Path(r"e:/xiangmudaima/shijuanshibie")
subject=root/'test'/'语文'
processor=DocumentProcessor()

def find(num):
  for ext in ('.docx','.doc'):
    p=subject/f"{num}{ext}"
    if p.exists(): return p

def print_tree(nodes,indent=0,max_depth=4):
  for n in nodes:
    num=str(n.get('numbering') or '')
    score=n.get('score')
    raw=str(n.get('rawText') or '')
    bt=str(n.get('blankText') or '')
    print('  '*indent+f"- [{n.get('level')}] {num} s={score} raw={raw[:90]} bt={bt[:60]}")
    if indent+1<max_depth:
      print_tree(n.get('children') or [],indent+1,max_depth)

for num in [251,295,302,238]:
  fp=find(num)
  out=processor.process(task_id=970000+num,file_path=str(fp),file_ext=fp.suffix.lower(),max_level=8,second_level_mode='auto',answer_section_patterns=None,score_patterns=None)
  roots=out['details']['outlineItems']
  print('\n===== ',num,fp.name,'=====')
  print_tree(roots,max_depth=5)
