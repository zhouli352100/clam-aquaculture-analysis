"""Render official source pages for the human visual review; no numeric inputs keyed."""
import common as c
from pathlib import Path
import pypdfium2 as pdfium
c.setup(c.args().root)
rows=[]
def render(p,indices,label):
 doc=pdfium.PdfDocument(str(p));out=c.QC/'source_validation/source_page_images';out.mkdir(exist_ok=True)
 for i in indices:
  page=doc[i-1];dest=out/f'{label}_page{i}.png';page.render(scale=150/72).to_pil().save(dest);page.close();rows.append(dict(source_file=c.rawref(p),source_sha256=c.sha(p),pdf_page=i,image_file=c.rawref(dest),human_review='PENDING'))
 doc.close()
for y in c.YEARS:
 render(c.rawfile(y,'table7'),[1],f'{y}_Table7');render(c.rawfile(y,'table19'),[1,2,3],f'{y}_Table19');render(c.rawfile(y,'questionnaire'),[14,15] if y==2013 else [86,87] if y==2018 else [13,14],f'{y}_Questionnaire')
render(c.rawfile(2023,'update'),[7],'2023_FormUpdate')
render(c.rawfile(2018,'appendix_a'),[3],'2018_Comparability');render(c.rawfile(2023,'appendix_a'),[2],'2023_Comparability')
c.csvout(c.QC/'source_validation/SOURCE_PAGE_REVIEW_REGISTER.csv',rows)
print('Source review images rendered:',len(rows))
