"""Copy only raw/code/instructions to an empty folder and execute the full pipeline."""
import common as c
from pathlib import Path
import shutil,subprocess,sys,os,zipfile,json
from pypdf import PdfReader
import pypdfium2 as pdfium
c.setup(c.args().root)
base=c.QC/'clean_rerun';base.mkdir(exist_ok=True);n=1
while (base/f'run_{n:03d}').exists():n+=1
fresh=base/f'run_{n:03d}';fresh.mkdir()
for folder in c.FOLDERS[:3]:shutil.copytree(c.ROOT/folder,fresh/folder,ignore=shutil.ignore_patterns('__pycache__'))
input_files=[dict(relative_path=p.relative_to(fresh).as_posix(),sha256=c.sha(p)) for p in sorted(fresh.rglob('*')) if p.is_file()]
c.csvout(c.QC/'CLEAN_RERUN_INITIAL_INPUTS.csv',input_files)
assert not (fresh/c.FOLDERS[3]).exists() and not (fresh/c.FOLDERS[7]).exists()
cmd=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(fresh/c.FOLDERS[0]/'run_all.ps1'),'-Python',sys.executable] if os.name=='nt' else None
assert cmd,'Run the stages manually with --root on non-Windows environments; the analysis scripts remain portable.'
log=c.QC/'CLEAN_RERUN_EXECUTION_LOG.txt'
with log.open('w',encoding='utf-8') as f:
 proc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=420,creationflags=subprocess.CREATE_NO_WINDOW)
if proc.returncode!=0:raise RuntimeError('Clean pipeline failed; inspect '+str(log))
def zipmembers(p):
 import re
 with zipfile.ZipFile(p) as z:
  out={n:z.read(n) for n in z.namelist()}
 # openpyxl refreshes this timestamp at save. No cells, styles or other members are excluded.
 if 'docProps/core.xml' in out:out['docProps/core.xml']=re.sub(rb'(<dcterms:modified\b[^>]*>).*?(</dcterms:modified>)',rb'\1TIMESTAMP_IGNORED\2',out['docProps/core.xml'])
 return out
def pdf_pixels(p):
 doc=pdfium.PdfDocument(str(p));result=[]
 for page in doc:im=page.render(scale=130/72).to_pil();result.append((im.size,__import__('hashlib').sha256(im.tobytes()).hexdigest()));page.close()
 doc.close();return result
results=[]
for folder in c.FOLDERS[3:7]:
 for p in sorted((c.ROOT/folder).rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(c.ROOT);q=fresh/rel;assert q.exists(),str(rel)
  method='SHA256 exact bytes';ok=c.sha(p)==c.sha(q)
  if p.suffix in ['.xlsx','.docx']:
   method='All OOXML member contents; only dcterms:modified timestamp normalized';ok=zipmembers(p)==zipmembers(q)
  if p.suffix=='.pdf' and not ok:
   method='Every page text, count and rendered130dpi pixels; metadata excluded';x,y=PdfReader(p),PdfReader(q);ok=len(x.pages)==len(y.pages) and [pg.extract_text() for pg in x.pages]==[pg.extract_text() for pg in y.pages] and pdf_pixels(p)==pdf_pixels(q)
  results.append(dict(relative_path=rel.as_posix(),method=method,primary_sha256=c.sha(p),fresh_sha256=c.sha(q),match=ok))
bad=[r for r in results if not r['match']];c.csvout(c.QC/'CLEAN_RERUN_FILE_COMPARISON.csv',results)
fresh_qc=c.readj(fresh/c.FOLDERS[7]/'MACHINE_QC.json');assert fresh_qc['benchmark_fields']==0 and fresh_qc['upstream_files_unchanged']==0
out=dict(pass_=not bad,fresh_directory=str(fresh.relative_to(c.ROOT)),initial_input_files=len(input_files),only_initial_folders=c.FOLDERS[:3],no_upstream_benchmark=True,files_compared=len(results),mismatches=bad,fresh_machine_summary=fresh_qc,primary_code_sha256={p.name:c.sha(p) for p in (c.ROOT/c.FOLDERS[2]).iterdir() if p.is_file()},scope='Official raw/code/instructions only. No previous output, workbook, benchmark or manual extraction copied. Numerical files and all publication artifacts compared. Only OOXML last-modified timestamp is normalized; Word PDF metadata is excluded only when all page text/count/pixels match.')
out['pass']=out.pop('pass_');c.writej(c.QC/'CLEAN_RERUN_COMPARISON.json',out)
print(json.dumps({k:v for k,v in out.items() if k!='mismatches'},ensure_ascii=False))
if bad:raise SystemExit('Clean reproduction mismatch; final readiness must remain CONDITIONAL/FAIL until resolved.')
