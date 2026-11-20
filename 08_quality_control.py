"""Terminal checks and delivery assembly. Old benchmarks never feed analyses."""
import common as c
import artifact_helpers as h
from pathlib import Path
from openpyxl import load_workbook
from docx import Document
from PIL import Image
from pypdf import PdfReader
import zipfile,xml.etree.ElementTree as ET,math,shutil,json,re
c.setup(c.args().root)
a=c.readj(c.DATA/'analytic/annual.json');de=c.readj(c.DATA/'analytic/decomposition.json');st=c.readj(c.DATA/'harmonized/states.json');checks=[]
def check(name,ok,detail=''):
 checks.append(dict(check=name,pass_=bool(ok),detail=detail))
 if not ok:raise AssertionError((name,detail))
def equal(x,y):
 if x is None:return y is None or y=='NA' or y==''
 if isinstance(x,bool):return x==y or str(x)==str(y)
 if isinstance(x,(int,float)):
  try:return math.isclose(x,float(y),rel_tol=1e-12,abs_tol=1e-8)
  except (TypeError,ValueError):return False
 return str(x)==str(y)
for r in c.csvread(c.RAW/'RAW_DATA_MANIFEST.csv'):check('RAW_SHA256_'+r['archive_relative_path'],c.sha(c.RAW/r['archive_relative_path'])==r['sha256'])
check('National_grid_21',len(a)==21);check('Matched_category_years_16',sum(r['status']=='IDENTIFIED' for r in a)==16);check('State_grid_600',len(st)==600);check('Decomposition_rows_42',len(de)==42);check('Identified_decompositions_28',sum(r['status']=='IDENTIFIED' for r in de)==28)
for r in a:
 if r['V_status']=='CONFIDENTIAL_D':check(f"D_preserved_{r['category']}_{r['year']}",r['V_nominal_1000_USD'] is None and r['P_nominal_USD_per_lb'] is None and r['V_1000_2023_USD'] is None and r['P_2023_USD_per_lb'] is None)
 if r['status']=='IDENTIFIED':
  check(f"V_Q_scope_{r['category']}_{r['year']}",r['scope'].startswith('Food or market size') and equal(r['P_nominal_USD_per_lb'],r['V_nominal_1000_USD']/r['Q_live_weight_1000_lb']))
  check(f"CPI_{r['category']}_{r['year']}",equal(r['V_1000_2023_USD'],r['V_nominal_1000_USD']*r['deflator_2023']) and equal(r['P_2023_USD_per_lb'],r['V_1000_2023_USD']/r['Q_live_weight_1000_lb']))
for r in st:
 if r['sales_1000_USD_status'] in ['CONFIDENTIAL_D','NOT_APPLICABLE_X']:check('State_suppression_'+str((r['category'],r['year'],r['state'])),r['sales_1000_USD'] is None)
for r in de:
 if r['status']=='IDENTIFIED':check('Identity_'+str((r['category'],r['from_year'],r['to_year'],r['basis'])),abs(r['delta_V_1000_USD']-r['quantity_component_1000_USD']-r['unit_value_component_1000_USD'])<1e-8)
 else:check('NA_'+str((r['category'],r['from_year'],r['to_year'],r['basis'])),r['delta_V_1000_USD'] is None and r['quantity_component_1000_USD'] is None and r['unit_value_component_1000_USD'] is None and bool(r['reason']))
for r in c.readj(c.DATA/'analytic/changes.json'):
 for k in ['all_size_farms','V_nominal_1000_USD','V_1000_2023_USD','Q_live_weight_1000_lb','N_sold_1000','P_nominal_USD_per_lb','P_2023_USD_per_lb']:
  x,y=r[k+'_from'],r[k+'_to'];check('Growth_'+str((r['category'],r['from_year'],r['to_year'],k)),equal(c.pct(x,y),r[k+'_pct']))
# Terminal benchmark comparison. Omitted in a minimal raw/code-only clean rerun.
benchmark=c.QC/'source_validation/UPSTREAM_BENCHMARK_QC_ONLY.json';bench=[]
if benchmark.exists():
 b=c.readj(benchmark)
 for r in a:
  old=next(z for z in b['annual'] if (z['category'],z['year'])==(r['category'],r['year']))
  for k in ['market_farms','V_nominal_1000_USD','Q_live_weight_1000_lb','N_sold_1000','P_nominal_USD_per_lb','official_average_price_USD_per_lb','CPI_U','deflator_2023','V_1000_2023_USD','P_2023_USD_per_lb']:
   ok=equal(r[k],old[k]);check('Old_benchmark_'+str((r['category'],r['year'],k)),ok);bench.append(dict(category=r['category'],year=r['year'],field=k,new_value=r[k],old_value=old[k],match=ok))
 for r in de:
  old=next(z for z in b['decomp'] if (z['category'],z['from_year'],z['to_year'],z['basis'])==(r['category'],r['from_year'],r['to_year'],'NOMINAL_USD' if r['basis']=='nominal' else 'CONSTANT_2023_USD'))
  for k,ko in [('delta_V_1000_USD','delta_V'),('quantity_component_1000_USD','quantity_contribution'),('unit_value_component_1000_USD','unit_value_contribution')]:
   ok=equal(r[k],old[ko]);check('Old_decomp_'+str((r['category'],r['from_year'],r['to_year'],r['basis'],k)),ok);bench.append(dict(category=r['category'],year=f"{r['from_year']}-{r['to_year']} {r['basis']}",field=k,new_value=r[k],old_value=old[ko],match=ok))
 c.csvout(c.QC/'source_validation/UPSTREAM_BENCHMARK_COMPARISON.csv',bench)
# Every workbook cell compared to its owning CSV, not just checksums of whole files.
cell_count=0;workbook_checks=[]
workbooks=[(c.TABLES/f'Table_{i}/Table{i}_FINAL.xlsx',[(f'Table {i}',c.TABLES/f'Table_{i}/Table{i}_Source_Data.csv')]) for i in [1,2,3]]
workbooks += [(c.SUP/f'Supplementary_Tables/Table_S{i}.xlsx',[(f'Table S{i}',c.SUP/f'Supplementary_Tables/Table_S{i}_Source_Data.csv')]) for i in [1,2,4]]
workbooks +=[(c.SUP/'Supplementary_Tables/Table_S3.xlsx',[(n,p) for n,p in [('CPI',c.SUP/'Supplementary_Tables/Table_S3_CPI_Source_Data.csv'),('Official price checks',c.SUP/'Supplementary_Tables/Table_S3_Official_price_checks_Source_Data.csv'),('Rounding sensitivity',c.SUP/'Supplementary_Tables/Table_S3_Rounding_sensitivity_Source_Data.csv')]])]
for p,sheets in workbooks:
 w=load_workbook(p,data_only=True)
 for name,source in sheets:
  rows=c.csvread(source);s=w[name];keys=list(rows[0]);check('Workbook_rows_'+p.name+'_'+name,s.max_row==len(rows)+3)
  for i,r in enumerate(rows,4):
   for j,k in enumerate(keys,1):
    value=s.cell(i,j).value;target=r[k];ok=(value is None and target=='') or (equal(value,target) if isinstance(value,(int,float,bool)) else str(value)==('NA' if target=='' else target))
    check('Workbook_cell_'+str((p.name,name,i,j)),ok,(value,target) if not ok else '');cell_count+=1
  workbook_checks.append(dict(file=c.rawref(p),sheet=name,rows=len(rows),cells=len(rows)*len(keys),source_csv=c.rawref(source),pass_=True))
c.csvout(c.QC/'formula_validation/WORKBOOK_CELL_VALIDATION.csv',workbook_checks)
# Validate independent plot source records against analytic owners.
for i in [1,3]:
 rows=c.csvread(c.FIGS/f'Figure_{i}/Figure{i}_Source_Data.csv');expected=[r for r in a if r['category'] in (c.PRIMARY if i==1 else c.PRIMARY+c.REFERENCE)];check(f'Figure{i}_point_support',len(rows)==len(expected))
 for r,z in zip(rows,expected):
  for k,v in z.items():check('Plot_record_'+str((i,r['category'],r['year'],k)),equal(v,r[k]))
rows=c.csvread(c.FIGS/'Figure_2/Figure2_Source_Data.csv');expected=[r for r in de if r['category'] in c.PRIMARY and r['basis']=='2023 USD'];check('Figure2_rows_9',len(rows)==9)
for r,z in zip(rows,expected):
 for k,v in z.items():check('Plot2_record_'+str((z['category'],z['from_year'],z['to_year'],k)),equal(v,r[k]))
f4=c.csvread(c.SUP/'Supplementary_Figures/Figure_S1_Source_Data.csv');check('Heatmap_full_source_450',len(f4)==450);check('Heatmap_union_all_censuses_19',len({r['state'] for r in f4 if r['shown_in_heatmap']=='True'})==19)
# Word table cell counts and editable structure; semantic numbers also checked against displays.
doc_checks=[]
for i in [1,2,3]:
 p=c.TABLES/f'Table_{i}/Table{i}_FINAL.docx';d=Document(p);rows=c.csvread(p.parent/f'Table{i}_Source_Data.csv');check('Editable_main_table_'+str(i),len(d.tables)==1 and len(d.tables[0].rows)==len(rows)+1);doc_checks.append(dict(document=c.rawref(p),editable_tables=len(d.tables),body_rows=len(rows),pass_=True))
 def fmt(z):return 'NA' if z=='' else f'{float(z):,.3f}'
 for ri,(row,r) in enumerate(zip(d.tables[0].rows[1:],rows),1):
  if i==1:expected=[r[k] for k in ['Category','Role','Form_code','Farms_2013','Farms_2018','Farms_2023','Matched_market_years','Classification_and_availability']]
  elif i==2:expected=[r['Category'],r['Census_year'],fmt(r['Market_sales_million_nominal_USD']) if r['Market_sales_million_nominal_USD'] else 'D',fmt(r['Market_live_weight_million_lb']),fmt(r['Market_sales_million_2023_USD']),fmt(r['Market_unit_value_2023_USD_per_lb'])]
  else:expected=[r['Category'],r['Period'],fmt(r['Real_sales_change_million_2023_USD']),fmt(r['Quantity_component_million_2023_USD']),fmt(r['Unit_value_component_million_2023_USD']),r['Component_directions']]
  for ci,(cell,target) in enumerate(zip(row.cells,expected)):check('Word_cell_'+str((i,ri,ci)),cell.text==target,(cell.text,target))
supdoc=Document(c.SUP/'Supplementary_Materials.docx');check('Supplement_editable_tables_6',len(supdoc.tables)==6);check('Supplement_word_rows',[len(t.rows)-1 for t in supdoc.tables]==[21,42,3,16,28,600]);check('Supplement_figure_integrated',len(supdoc.inline_shapes)==1)
abbr={'Hard clams':'Hard','Manila clams':'Manila','Geoducks':'Geoduck','Other clams':'Other','Eastern oysters':'Eastern','Pacific oysters':'Pacific','Mussels':'Mussels'}
sr=c.SUP/'Supplementary_Tables';expected_supp=[]
rr=c.csvread(sr/'Table_S1_Source_Data.csv');expected_supp.append([[abbr[r['category']],r['year'],r['questionnaire_code'],r['market_V_raw'],r['market_Q_raw'],'Yes' if r['matched_status']=='IDENTIFIED' else 'No',r['questionnaire_label'].replace(' clams','').replace(' oysters','')] for r in rr])
rr=c.csvread(sr/'Table_S2_Source_Data.csv');expected_supp.append([[abbr[r['category']],f"{r['from_year']}-{r['to_year']}",'N' if r['basis']=='nominal' else 'R',fmt(r['delta_V_million_USD']),fmt(r['quantity_component_million_USD']),fmt(r['unit_value_component_million_USD']),r['reason'].replace('Market-size sales value ','sales ').replace('(D)','D') if r['status']!='IDENTIFIED' else 'Available'] for r in rr])
rr=c.csvread(sr/'Table_S3_CPI_Source_Data.csv');expected_supp.append([[r['year'],f"{float(r['annual_CPI_U']):.3f}",f"{float(r['factor_to_2023']):.9f}"] for r in rr])
rr=c.csvread(sr/'Table_S3_Official_price_checks_Source_Data.csv');expected_supp.append([[abbr[r['category']],r['year'],f"{float(r['recomputed_P']):.5f}",f"{float(r['official_P']):.2f}",f"{float(r['recomputed_lower']):.5f} to {float(r['recomputed_upper']):.5f}",'Yes' if r['rounding_intervals_overlap']=='True' else 'No'] for r in rr])
rr=c.csvread(sr/'Table_S3_Rounding_sensitivity_Source_Data.csv');expected_supp.append([[abbr[r['category']],f"{r['from_year']}-{r['to_year']}",'N' if r['basis']=='nominal' else 'R',f"{float(r['quantity_min'])/1000:.3f} to {float(r['quantity_max'])/1000:.3f}",f"{float(r['unit_value_min'])/1000:.3f} to {float(r['unit_value_max'])/1000:.3f}",f"{float(r['delta_V_min'])/1000:.3f} to {float(r['delta_V_max'])/1000:.3f}",f"{float(r['P_change_pct_min']):.3f} to {float(r['P_change_pct_max']):.3f}"] for r in rr])
rr=c.csvread(sr/'Table_S4_Source_Data.csv');expected_supp.append([[r['state'],abbr[r['category']],r['year'],r['farms_raw'],r['sales_1000_USD_raw'],'D confidential' if r['sales_1000_USD_status']=='CONFIDENTIAL_D' else 'Zero / rounds to zero' if r['sales_1000_USD_status']=='ZERO_OR_ROUNDS_TO_ZERO' else 'Published numeric' if r['sales_1000_USD_status']=='PUBLISHED_NUMERIC' else r['sales_1000_USD_status']] for r in rr])
supp_word_cells=0
for ti,(tab,expected) in enumerate(zip(supdoc.tables,expected_supp),1):
 for ri,(row,targets) in enumerate(zip(tab.rows[1:],expected),1):
  for ci,(cell,target) in enumerate(zip(row.cells,targets),1):check('Supplement_Word_cell_'+str((ti,ri,ci)),cell.text==target,(cell.text,target));supp_word_cells+=1
doc_checks.append(dict(document=c.rawref(c.SUP/'Supplementary_Materials.docx'),editable_tables=6,body_rows=710,pass_=True));c.csvout(c.QC/'formula_validation/DOCX_STRUCTURE_VALIDATION.csv',doc_checks)
# Raster/vector physical dimensions, SVG parsing, font embedding and PDF text bounds.
media=[]
figpaths=[c.FIGS/f'Figure_{i}/Figure{i}_FINAL' for i in [1,2,3]]+[c.SUP/'Supplementary_Figures/Figure_S1']
for p in figpaths:
 with Image.open(p.with_suffix('.png')) as im:
  dpi=im.info.get('dpi');check('PNG_600dpi_'+p.name,dpi is not None and all(abs(z-600)<.1 for z in dpi));check('PNG_width175mm_'+p.name,abs(im.width/600*25.4-175)<.1);px=list(im.size)
 tree=ET.parse(p.with_suffix('.svg'));check('SVG_valid_'+p.name,tree.getroot().tag.endswith('svg'))
 reader=PdfReader(p.with_suffix('.pdf'));pg=reader.pages[0];check('PDF_width175mm_'+p.name,abs(float(pg.mediabox.width)/72*25.4-175)<.1)
 def embedded(font):
  f=font.get_object()
  if '/DescendantFonts' in f:return all(embedded(z) for z in f['/DescendantFonts'])
  fd=f.get('/FontDescriptor');return fd is not None and any(k in fd.get_object() for k in ['/FontFile','/FontFile2','/FontFile3'])
 fonts=pg['/Resources'].get('/Font',{});fonts=fonts.get_object() if hasattr(fonts,'get_object') else fonts;check('PDF_fonts_embedded_'+p.name,len(fonts)>0 and all(embedded(z) for z in fonts.values()))
 media.append(dict(file=c.rawref(p),png_pixels=px,dpi=dpi,pdf_width_mm=float(pg.mediabox.width)/72*25.4,svg_valid=True,fonts_embedded=True))
c.writej(c.QC/'visual_review/MEDIA_TECHNICAL_QC.json',media)
# Source-page visual review, publication visual review and clean rerun are evidence gates.
vis=c.QC/'visual_review/VISUAL_REVIEW_RECORD.json';clean=c.QC/'CLEAN_RERUN_COMPARISON.json'
visual_ok=vis.exists() and c.readj(vis).get('pass') is True and all(c.sha(c.ROOT/r['relative_path'])==r['sha256'] for r in c.readj(vis).get('reviewed_files',[]))
clean_ok=clean.exists() and c.readj(clean).get('pass') is True
if clean_ok:
 clean_ok=all(c.sha(c.ROOT/r['relative_path'])==r['primary_sha256'] for r in c.csvread(c.QC/'CLEAN_RERUN_FILE_COMPARISON.csv')) and all(c.sha(c.ROOT/c.FOLDERS[2]/name)==hh for name,hh in c.readj(clean)['primary_code_sha256'].items())
up=c.QC/'hash_validation/UPSTREAM_SHA256_BEFORE.csv';up_count=0
if up.exists():
 after=[]
 for r in c.csvread(up):
  p=Path(r['original_path']);hh=c.sha(p);check('Upstream_unchanged_'+str(up_count),hh==r['sha256'],str(p));after.append(dict(original_path=str(p),before_sha256=r['sha256'],after_sha256=hh,unchanged=True));up_count+=1
 c.csvout(c.QC/'hash_validation/UPSTREAM_SHA256_AFTER.csv',after)
status='PASS' if visual_ok and clean_ok else 'CONDITIONAL'
summary=dict(status=status,machine_checks=len(checks),workbook_cells=cell_count,benchmark_fields=len(bench),raw_files=26,matched_category_years=16,identified_decompositions=28,unavailable_decompositions=14,max_float_identity_residual=max(abs(r['identity_residual_1000_USD']) for r in de if r['status']=='IDENTIFIED'),visual_review_pass=visual_ok,clean_rerun_pass=clean_ok,upstream_files_unchanged=up_count)
c.writej(c.QC/'MACHINE_QC.json',summary);c.csvout(c.QC/'formula_validation/ALL_MACHINE_CHECKS.csv',checks)
report=f'''# Step 4 final quality-control report

**{status}**. Numerical and source checks passed. Visual review: {visual_ok}. Clean raw/code-only rerun: {clean_ok}.

| Required question | Finding |
|---|---|
| 1. Official raw files to all main figures and tables? | Yes. USDA PDF/native CSV and BLS M13 JSON are freshly parsed by stages 01-04 before authoring. |
| 2. Dependence on old final statistics? | None for analysis or authoring. The optional upstream benchmark is read only in this terminal QC stage; it is absent from the clean rerun inputs. |
| 3. Human verification of PDF extraction? | Numeric Table 7 and Table 19 pages and questionnaire/category pages require visual comparison. No keyed numeric intermediate is needed. See source-page images and review record. Scanned forms are not treated as fully machine-read. |
| 4. Matching market-size value and weight? | Yes, within category/census/stage. All-size fields are separately named; no all-size V divided by market-size Q. |
| 5. Suppression retained? | Yes. 5 suppressed market-size category-years; 14 unavailable decomposition rows. All 47 state D sales remain non-numeric. Original X and dash tokens retained. |
| 6. Decomposition identities? | All 28 identified rows pass float and independent 45-digit Decimal checks; max float residual {summary['max_float_identity_residual']:.3g} thousand USD. |
| 7. Previous Step 3/3.5 agreement? | {len(bench)} terminal numeric field comparisons pass when benchmark is present. Scope distinction from Step 3 all-size sales is explicitly preserved. No old result modified. |
| 8. Unnecessary main-table/figure repetition? | T1 provides coverage and all-size farms; T2 exact matched levels; T3 five focal exact decompositions. F1 supplies context, F2 component pattern, F3 within-group adjusted unit values. Complete period/base grids are in S2. Some level/result overlap is intentional for exact values plus visual pattern. |
| 9. Four supplement tables and one figure complete? | Yes: S1 21 category-years; S2 42 prespecified rows; S3 CPI3 + official mean checks16 + rounding28; S4 all600 state rows; Figure S1 full450-row source and19 displayed states. Integrated editable DOCX contains all rows. |
| 10. Submission-ready material? | {'Yes for the requested figure/data/code stage. Final journal-specific formatting and a complete manuscript remain outside this task.' if status=='PASS' else 'Pending documented visual review and/or clean rerun; do not label ready before these gates pass.'} |

Machine checks: {len(checks):,}; workbook cells checked: {cell_count:,}; archived official files:26. Upstream files checked unchanged:{up_count:,}. Publication PNGs are600dpi at175mm width; figure PDFs have embedded TrueType fonts and SVGs parse correctly. Word tables remain editable.

Rendering environment: the packaged render_docx.py was attempted but no LibreOffice executable was installed. Native hidden Microsoft Word exported read-only DOCX files to PDF, then pypdfium2 rendered every page for visual inspection. The portable code supports Word on Windows and LibreOffice on other platforms; these are declared rendering dependencies. This is a rendering fallback, not a numeric extraction change.

No regression, significance test, imputation, confidential-value recovery, continuous-year interpolation or mechanistic inference was added. Rounding ranges are not confidence intervals. The public code package excludes official raw PDFs pending redistribution permission and provides source URLs and hashes.
'''
c.textout(c.QC/'FINAL_QC_REPORT.md',report)
# Submission assembly is allowlisted; no runtime/cache/fonts/raw PDFs/logs enter it.
dest=c.ROOT/c.FOLDERS[8]
def cpfile(p,to):to.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,to)
for i in [1,2,3]:
 for ext in ['xlsx','docx']:p=c.TABLES/f'Table_{i}/Table{i}_FINAL.{ext}';cpfile(p,dest/'Main_Tables'/p.name)
 for ext in ['pdf','svg','png']:p=c.FIGS/f'Figure_{i}/Figure{i}_FINAL.{ext}';cpfile(p,dest/'Main_Figures'/p.name)
 for kind,p in [('Tables',c.TABLES/f'Table_{i}/Table{i}_Source_Data.csv'),('Figures',c.FIGS/f'Figure_{i}/Figure{i}_Source_Data.csv')]:cpfile(p,dest/'Source_Data'/kind/p.name)
 p=c.FIGS/f'Figure_{i}/Figure{i}_Caption.md';cpfile(p,dest/'Main_Figures'/p.name)
cpfile(c.SUP/'Supplementary_Materials.docx',dest/'Supplementary_Materials/Supplementary_Materials.docx')
cpfile(c.SUP/'Supplementary_Methods/Supplementary_Methods.md',dest/'Supplementary_Materials/Supplementary_Methods.md')
for p in (c.SUP/'Supplementary_Tables').glob('*'):
 if p.suffix in ['.xlsx','.csv']:cpfile(p,dest/'Supplementary_Materials'/p.name)
for name in ['Figure_S1.pdf','Figure_S1.png','Figure_S1_Source_Data.csv','Figure_S1_Caption.md']:cpfile(c.SUP/'Supplementary_Figures'/name,dest/'Supplementary_Materials'/name)
availability='''# Data and code availability

Official sources are USDA NASS Census of Aquaculture 2013,2018,2023 and BLS CPI-U CUUR0000SA0 annual period M13. The public reproducibility ZIP includes complete analysis code, pinned direct requirements, source URLs, SHA256 values, derived numerical CSVs and a raw-file fetch helper. It excludes the original government PDFs, HTML, ZIPs and JSON pending file-specific redistribution confirmation. Users retrieve the exact listed official files or supply byte-identical archived copies and verify SHA256 before running. A changed official file must be investigated rather than silently accepted.

The internal full research archive retains all26 original official files and complete source and QC records. No farm microdata are used. D sales values remain unavailable; derived data do not reconstruct confidential cells. Public derived CSVs describe published commercial groups and are not biological species microdata. An appropriate repository DOI and the final journal data statement should be added when the author deposits the package. This local preparation does not constitute public deposit or journal submission.
'''
c.textout(dest/'Data_and_Code_Availability.md',availability)
manifest=c.csvread(c.RAW/'RAW_DATA_MANIFEST.csv');public=[{k:v for k,v in r.items() if k!='original_path'} for r in manifest];c.csvout(c.QC/'source_validation/PUBLIC_RAW_DATA_MANIFEST.csv',public)
zipout=dest/'Reproducible_Code_and_Derived_Data.zip'
with zipfile.ZipFile(zipout,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for folder in [c.ROOT/c.FOLDERS[2],c.DOCS]:
  for p in sorted(folder.iterdir()):
   if p.is_file() and p.suffix in ['.py','.ps1','.md','.txt']:z.write(p,c.rawref(p))
 z.write(c.QC/'source_validation/PUBLIC_RAW_DATA_MANIFEST.csv',c.FOLDERS[1]+'/RAW_DATA_MANIFEST.csv')
 for p in sorted((c.DATA/'analytic').glob('*.csv')):z.write(p,c.rawref(p))
 for p in sorted((c.DATA/'data_dictionary').glob('*.csv')):z.write(p,c.rawref(p))
 z.write(dest/'Data_and_Code_Availability.md','Data_and_Code_Availability.md')
with zipfile.ZipFile(zipout) as z:
 safe=not any(n.lower().endswith(('.pdf','.json','.zip','.png','.ttf','.whl')) or '__pycache__' in n or 'python_packages' in n for n in z.namelist());assert safe
 c.writej(c.QC/'SUBMISSION_PACKAGE_ALLOWLIST_QC.json',dict(pass_=safe,files=z.namelist(),excluded='Official originals, libraries, fonts, caches, logs and preview images'))
index='''# Step 4 完整交付索引

本目录为完整研究归档；08_SUBMISSION_READY 为精简投稿材料。两套文件用途不同。正文三表可编辑为XLSX与DOCX，正文三图均新生成PDF/SVG/600dpi PNG。所有数据由26份官方文件重新提取，不以旧阶段汇总结果作为输入。

| 成果 | 用途 | 来源 | 目录 |
|---|---|---|---|
| Table 1 | 商业类别、可用年份与经营场数背景 | USDA Table7；蛤类以Table19复核 | 04_MAIN_TABLES/Table_1 |
| Table 2 | 匹配商品规格金额、活重、实际单位价值的精确数值 | USDA Table7＋BLS M13 | 04_MAIN_TABLES/Table_2 |
| Table 3 | 五个预设重点比较的精确实际金额分量 | 同口径V/Q与CPI对称分解 | 04_MAIN_TABLES/Table_3 |
| Figure 1 | 三具名蛤类场数与商品活重的不同变化 | USDA Table7；Table19复核场数 | 05_MAIN_FIGURES/Figure_1 |
| Figure 2 | 三蛤类所有预设期间的实际数量/单位价值分量及净变化 | 新重算分解；Manila相邻期间NA | 05_MAIN_FIGURES/Figure_2 |
| Figure 3 | 六商业组内部实际单位价值跨期观察点 | 同口径V/Q＋CPI；不跨D连线 | 05_MAIN_FIGURES/Figure_3 |
| Supplementary Methods | 十项技术定义与限制 | 原问卷/附录、USDA表与BLS | 06_SUPPLEMENTARY/Supplementary_Methods |
| Table S1 | 21类别—年份定义、代码与准入 | 原问卷与Table7 | 06_SUPPLEMENTARY/Supplementary_Tables |
| Table S2 | 全部42行预设比较；含14行NA | 新重算两种货币基准分解 | 同上 |
| Table S3 | CPI3行、官方均值核对16行、舍入敏感性28行 | 官方JSON与原表公布精度 | 同上 |
| Table S4 | 全50州×四蛤类×三普查600行与原保密符号 | 新提取Table19 | 同上 |
| Figure S1 | 任一普查正场数州的分布；19州并集 | 全450主体州级源记录 | 06_SUPPLEMENTARY/Supplementary_Figures |
| Supplementary_Materials.docx | 整合方法、全部四表及附图，可编辑 | 上述完整内容 | 06_SUPPLEMENTARY |
| 复现入口与环境 | 从官方原始资料重新运行 | 代码、SHA、requirements | 00_README与项目说明/run_all.ps1 |
| 最终QC | 来源/计算/图表/干净重跑/上游未修改 | 执行证据 | 07_QC_核验/FINAL_QC_REPORT.md |

表格PDF为内部投稿预览；完整补充DOCX的PDF及逐页图片只用于内部视觉检查，不放进精简投稿包。08_SUBMISSION_READY中的代码ZIP不包含原始PDF或运行库。官方文件通过URL与SHA获取或从内部原始归档复制。
'''
index+='\n## 可点击文件清单\n\n'
for folder in [c.TABLES,c.FIGS,c.SUP]:
 for p in sorted(folder.rglob('*')):
  if p.is_file() and 'Preview' not in p.name and not (p.parent==c.SUP and p.suffix=='.pdf'):
   index+=f'- [{p.name}](<{p.as_posix()}>)\n'
index+='\n复现与QC入口：\n\n'
for p in [c.DOCS/'README.md',c.DOCS/'REPRODUCIBILITY_GUIDE.md',c.DOCS/'run_all.ps1',c.DOCS/'requirements.txt',c.RAW/'RAW_DATA_MANIFEST.csv',c.QC/'FINAL_QC_REPORT.md',dest/'Reproducible_Code_and_Derived_Data.zip']:
 index+=f'- [{p.name}](<{p.as_posix()}>)\n'
c.textout(c.ROOT/c.FOLDERS[9]/'FINAL_DELIVERY_INDEX.md',index)
c.textout(c.ROOT/c.FOLDERS[9]/'FIGURE_TABLE_MAP.md',index+'\n每个正式表图目录均有独立源CSV和完整图注。Table2提供精确水平值；Figure3展示类别内部变化。Table3只保留五个重点比较；Figure2保留三主体类别的全部期间及NA；S2承担完整比较网格。\n')
c.textout(c.ROOT/c.FOLDERS[9]/'SUBMISSION_READINESS.md',f'''# Step 4 投稿材料就绪判定

**{status}**

已完成从26份官方文件到正文三表三图、十项补充方法、四张完整补充表与一张补充图的自动化重建。16个可配对类别—普查点支持28行名义/实际分解；另14行保留NA。这些分解不是28个独立样本。

数值来源与计算通过；视觉核验={visual_ok}；全新目录原始文件/代码重跑={clean_ok}；与旧结果末端对照字段={len(bench)}；上游SHA前后未改文件={up_count}。

摘要可用：匹配商品规格后Geoducks2018-2023的名义/实际金额差别及数量分量、Hard十年活重与实际单位价值反向、三组类别特异的方向差异。均只能表述为描述性销售指标及算术分量，不是总生产量、纯价格或因果机制。

补充材料用途：完整名义与实际比较、官方平均值舍入协调、有限公布舍入敏感性、600州级记录和保密分布。所有D保持原样，不解释缺失为零。Source_Data中的完整精度优先于表格显示舍入。

本判定仅覆盖用户要求的图表、数据与复现阶段；没有重新评价期刊分区或承诺录用。最终期刊专用尺寸、文件命名、完整稿件及公开仓储DOI在选刊/实际提交时由作者补齐，不属于本次新增研究分析。
''')
shutil.make_archive(str(c.ROOT/c.FOLDERS[9]/'SUBMISSION_READY'),'zip',root_dir=dest)
files=[]
for p in sorted(c.ROOT.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts and 'matplotlib_config' not in p.parts and p.name!='OUTPUT_SHA256.csv' and 'clean_rerun' not in p.parts:files.append(dict(relative_path=c.rawref(p),sha256=c.sha(p),bytes=p.stat().st_size))
c.csvout(c.QC/'hash_validation/OUTPUT_SHA256.csv',files)
print(json.dumps(summary,ensure_ascii=False))
