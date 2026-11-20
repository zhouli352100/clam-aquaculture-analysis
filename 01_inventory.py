import common as c
from pathlib import Path
import platform,importlib.metadata as md
c.setup(c.args().root)
rows=[]
for r in c.csvread(c.RAW/'RAW_DATA_MANIFEST.csv'):
 p=c.RAW/r['archive_relative_path'];h=c.sha(p);assert h==r['sha256'],(p,h,r['sha256']);rows.append(dict(file=c.rawref(p),expected_sha256=r['sha256'],actual_sha256=h,match=True))
c.csvout(c.QC/'hash_validation/RAW_HASH_CHECK.csv',rows)
c.writej(c.QC/'EXECUTION_ENVIRONMENT.json',dict(python=platform.python_version(),platform=platform.platform(),packages={p:md.version(p) for p in ['numpy','pandas','matplotlib','openpyxl','python-docx','pdfplumber','pypdf','pypdfium2','Pillow','reportlab']}))
print('Raw inventory and hashes PASS:',len(rows))
