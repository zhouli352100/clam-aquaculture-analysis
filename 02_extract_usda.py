import common as c
import pdfplumber,csv,re
c.setup(c.args().root)
raw=[];pages=[];states=[];checks=[]
FIELDS=['farms','number_1000','live_weight_1000_lb','number_per_lb','sales_1000_USD','official_unit_value_USD_per_lb']
def records(text,y,path,native=False):
 parent='';cat=None;remain=0;out=[]
 for ln,line in enumerate(text.splitlines(),1):
  line=re.sub(r'\.{2,}',' ',line).strip();header=False
  if line.startswith('Clams, total'):parent='Clams';cat='Total clams';remain=0;header=True
  elif line.startswith('Oysters, total'):parent='Oysters';cat=None;remain=0
  elif line.startswith('Geoduck '):cat='Geoducks';header=True
  elif line.startswith('Hard '):cat='Hard clams';header=True
  elif line.startswith('Manila '):cat='Manila clams';header=True
  elif line.startswith('Mussels '):parent='Mussels';cat='Mussels';header=True
  elif line.startswith('Eastern '):cat='Eastern oysters';header=True
  elif line.startswith('Pacific '):cat='Pacific oysters';header=True
  elif line.startswith('Other ') and remain==0 and parent=='Clams' and cat=='Manila clams':cat='Other clams';header=True
  elif line.startswith('Other ') and remain==0 and parent=='Oysters' and cat=='Pacific oysters':cat=None
  elif line.startswith('Other mollusks'):cat=None;parent='';remain=0
  if cat not in c.CATEGORIES+['Total clams']:continue
  if header:stage='All sizes';remain=4
  elif line.startswith('Food or market size'):stage='Food or market size';remain-=1
  elif re.match(r'^(Broodstock|Larvae and seed|Other)\s',line):remain=max(0,remain-1);continue
  else:continue
  m=re.search(r'((?:\(?[DX]\)?|-|[\d,]+(?:\.\d+)?)(?:\s+(?:\(?[DX]\)?|-|[\d,]+(?:\.\d+)?)){5})$',line)
  if not m:continue
  vals=m.group(1).split();assert len(vals)==6
  r=dict(year=y,category=cat,stage=stage,questionnaire_code=c.CODES.get(cat),source_file=c.rawref(path),source_sha256=c.sha(path),source_table='Table 7',pdf_page=1,printed_page=10,source_line=ln,original_line=line)
  for k,v in zip(FIELDS,vals):r[k+'_raw']=v;r[k],r[k+'_status']=c.numeric(v,k=='farms')
  out.append(r)
 return out
for y in c.YEARS:
 p=c.rawfile(y,'table7')
 with pdfplumber.open(p) as pdf:tx=pdf.pages[0].extract_text(x_tolerance=2,y_tolerance=2)
 pages.append(dict(year=y,table='Table 7',source_file=c.rawref(p),pdf_page=1,printed_page=10,text=tx));rr=records(tx,y,p);assert len(rr)==15,(y,len(rr));raw+=rr
 # Independent native CSV check. Locate actual Table 7 title rather than component filename.
 if y!=2013:
  np=c.rawfile(y,'native_csv');ns=list(csv.reader(np.open(encoding='cp1252',newline='')))
  title=next(r for r in ns if len(r)>2 and 'Table 7.' in ' '.join(r) and 'Mollusk' in ' '.join(r));block=title[0]
  lines=[]
  for r in ns:
   if len(r)>=9 and r[0]==block and r[1]=='d':lines.append(r[2]+' '+' '.join(r[3:9]))
  nr=records('\n'.join(lines),y,np);assert len(nr)==15,(y,len(nr),lines)
  for a in rr:
   b=next(z for z in nr if (z['category'],z['stage'])==(a['category'],a['stage']))
   for k in FIELDS:
    ok=a[k+'_raw'].replace(',','')==b[k+'_raw'].replace(',','');assert ok,(y,a['category'],a['stage'],k,a[k+'_raw'],b[k+'_raw'])
    checks.append(dict(year=y,category=a['category'],stage=a['stage'],field=k,pdf_raw=a[k+'_raw'],native_csv_raw=b[k+'_raw'],match=ok))
 p=c.rawfile(y,'table19');groups={1:['Mollusks','Abalone','Total clams'],2:['Geoducks','Hard clams','Manila clams'],3:['Other clams','Mussels','Oysters']}
 with pdfplumber.open(p) as pdf:
  for pi in (1,2,3):
   tx=pdf.pages[pi-1].extract_text(x_tolerance=2,y_tolerance=2);pages.append(dict(year=y,table='Table 19',source_file=c.rawref(p),pdf_page=pi,printed_page=(45 if y==2013 else 43)+pi,text=tx))
   for ln,line in enumerate(tx.splitlines(),1):
    tok=[v for v in re.sub(r'\.{2,}',' ',line).split() if v!='.'];vals=[]
    while tok and re.fullmatch(r'(?:\d[\d,]*(?:\.\d+)?|\([A-Z]+\)|-)',tok[-1]):vals.insert(0,tok.pop())
    st=' '.join(tok)
    if st not in c.STATES+['United States']:continue
    assert len(vals)==12,(y,pi,st,vals)
    for j,cat in enumerate(groups[pi]):
     if cat not in c.PRIMARY+['Other clams','Total clams']:continue
     r=dict(year=y,category=cat,state=st,source_table='Table 19',source_file=c.rawref(p),source_sha256=c.sha(p),pdf_page=pi,printed_page=(45 if y==2013 else 43)+pi,source_line=ln,original_line=line)
     for k,v in [('farms',vals[4*j]),('sales_1000_USD',vals[4*j+1])]:r[k+'_raw']=v;r[k],r[k+'_status']=c.numeric(v,k=='farms')
     states.append(r)
assert len(raw)==45 and len(states)==765,(len(raw),len(states))
cp=[]
for y in c.YEARS:
 p=c.rawfile(y,'cpi');j=c.readj(p);s=j['Results']['series'][0];assert s['seriesID']=='CUUR0000SA0';d=next(r for r in s['data'] if r['period']=='M13' and int(r['year'])==y)
 cp.append(dict(year=y,series_id=s['seriesID'],period='M13',annual_CPI_U=float(d['value']),raw_value=d['value'],source_file=c.rawref(p),sha256=c.sha(p),index_definition='All items; U.S. city average; not seasonally adjusted; 1982-84=100'))
c.writej(c.DATA/'raw_extracted/table7.json',raw);c.csvout(c.DATA/'raw_extracted/table7.csv',raw)
c.writej(c.DATA/'raw_extracted/table19.json',states);c.csvout(c.DATA/'raw_extracted/table19.csv',states)
c.writej(c.DATA/'raw_extracted/CPI.json',cp);c.csvout(c.DATA/'raw_extracted/CPI.csv',cp)
c.writej(c.DATA/'raw_extracted/PDF_PAGE_TEXT.json',pages);c.csvout(c.QC/'source_validation/PDF_NATIVE_CSV_CHECK.csv',checks)
# Re-read definition documents from raw PDFs. Scanned questionnaire pages require visual review.
defs=[]
for r in c.csvread(c.RAW/'RAW_DATA_MANIFEST.csv'):
 if r['kind'] not in ['appendix_a','introduction','questionnaire','update']:continue
 p=c.RAW/r['archive_relative_path']
 with pdfplumber.open(p) as pdf:
  for pi,pg in enumerate(pdf.pages,1):
   tx=pg.extract_text() or ''
   if r['kind']!='questionnaire' or pi in [13,14,86]:defs.append(dict(source_file=c.rawref(p),kind=r['kind'],year=r['year'],pdf_page=pi,text=tx,manual_review_required=r['kind']=='questionnaire'))
c.writej(c.DATA/'raw_extracted/DEFINITION_PAGE_TEXT.json',defs)
print('Extracted fresh raw:',len(raw),'national stage rows;',len(states),'state/national rows;',len(checks),'native PDF cell matches')
