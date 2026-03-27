from pathlib import Path
from docx import Document
from app.services.document_processor import DocumentProcessor

root=Path(r"e:/xiangmudaima/shijuanshibie")
subject=root/'test'/'语文'
processor=DocumentProcessor()

def show(num):
    fp=None
    for ext in ('.docx','.doc'):
        p=subject/f"{num}{ext}"
        if p.exists(): fp=p; break
    if fp is None:
        print('missing',num); return
    print('\n===== DOC',num,fp.name,'=====')
    if fp.suffix.lower()=='.docx':
        doc=Document(str(fp))
        lines=processor._collect_docx_lines(doc)
    else:
        converted=processor._convert_doc_to_docx(fp)
        doc=Document(str(converted))
        lines=processor._collect_docx_lines(doc)
    main,_=processor._split_lines_by_answer(lines, processor._compile_answer_patterns(None))
    exp=processor._extract_answer_heading_score_map if False else None
    for i,l in enumerate(main,1):
        if i>220: break
        if any(k in l for k in ['三、','三.','（一）','（二）','（1）','(1)','1.','2.','3.','4.','5.','6.','7.','8.','9.','10.','11.','12.','13.','14.','15.','16.','17.','18.','19.','20.','21.','22.','23.','24.','25.','26.','27.','28.']) or '分' in l:
            print(f"{i:03d}: {l}")

for n in [238,251,295,302]:
    show(n)
