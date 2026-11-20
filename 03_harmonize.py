import common as c
c.setup(c.args().root)
raw=c.readj(c.DATA/'raw_extracted/table7.json');st=c.readj(c.DATA/'raw_extracted/table19.json');cp=c.readj(c.DATA/'raw_extracted/CPI.json')
annual=[]
for cat in c.CATEGORIES:
 for y in c.YEARS:
  a=next(r for r in raw if (r['year'],r['category'],r['stage'])==(y,cat,'All sizes'));r=next(r for r in raw if (r['year'],r['category'],r['stage'])==(y,cat,'Food or market size'))
  v,q=r['sales_1000_USD'],r['live_weight_1000_lb'];p=v/q if v is not None and q is not None and q>0 else None
  annual.append(dict(category=cat,year=y,role=c.role(cat),questionnaire_code=c.CODES[cat],definition=c.definition(cat,y),all_size_farms=a['farms'],all_size_sales_1000_USD=a['sales_1000_USD'],market_farms=r['farms'],V_nominal_1000_USD=v,Q_live_weight_1000_lb=q,N_sold_1000=r['number_1000'],P_nominal_USD_per_lb=p,official_average_price_USD_per_lb=r['official_unit_value_USD_per_lb'],V_raw=r['sales_1000_USD_raw'],Q_raw=r['live_weight_1000_lb_raw'],N_raw=r['number_1000_raw'],V_status=r['sales_1000_USD_status'],Q_status=r['live_weight_1000_lb_status'],status='IDENTIFIED' if p is not None else 'NOT_IDENTIFIED',reason='' if p is not None else 'Market-size sales value '+r['sales_1000_USD_raw'],scope='Food or market size sales, not total aquaculture production',source_file=r['source_file'],source_sha256=r['source_sha256'],source_table=r['source_table'],pdf_page=r['pdf_page'],printed_page=r['printed_page'],source_line=r['source_line']))
state=[r for r in st if r['category']!='Total clams' and r['state']!='United States'];assert len(state)==600
checks=[]
for cat in c.PRIMARY+['Other clams','Total clams']:
 for y in c.YEARS:
  a=next(r for r in raw if (r['year'],r['category'],r['stage'])==(y,cat,'All sizes'));n=next(r for r in st if (r['year'],r['category'],r['state'])==(y,cat,'United States'))
  for k in ['farms','sales_1000_USD']:assert a[k]==n[k];checks.append(dict(year=y,category=cat,field=k,table7=a[k],table19=n[k],match=True))
  ss=sum(r['farms'] for r in st if r['year']==y and r['category']==cat and r['state']!='United States');assert ss==n['farms'];checks.append(dict(year=y,category=cat,field='State farm sum',table7=n['farms'],table19=ss,match=True))
c.csvout(c.QC/'source_validation/TABLE7_TABLE19_AND_STATE_SUMS.csv',checks)
c.writej(c.DATA/'harmonized/national.json',annual);c.csvout(c.DATA/'harmonized/national.csv',annual);c.writej(c.DATA/'harmonized/states.json',state);c.csvout(c.DATA/'harmonized/states.csv',state)
dd=[dict(field=k,description=v) for k,v in {'all_size_farms':'Published reporting operations, potentially shared across commercial categories; not unique sum','V_nominal_1000_USD':'Food or market-size nominal sales value in thousand USD','Q_live_weight_1000_lb':'Food or market-size whole live-weight sales in thousand lb; not total production','N_sold_1000':'Food or market-size number sold in thousand animals; no cross-category sum','P_nominal_USD_per_lb':'Matching market-size V/Q; calculated from published rounded inputs','CONFIDENTIAL_D':'Official disclosure suppression; numeric value remains null','ZERO_OR_ROUNDS_TO_ZERO':'Official dash; farms can be plotted as zero estimate; original dash preserved; sales not imputed zero','NOT_APPLICABLE_X':'Official X, not numeric','CPI_U':'All-items U.S. city average CPI-U; M13 annual average; not an aquaculture price index','source_line':'Line in reproducibly extracted page text, with PDF page and publication page retained'}.items()]
c.csvout(c.DATA/'data_dictionary/DATA_DICTIONARY.csv',dd)
print('Harmonized:',len(annual),'category-census rows;',len(state),'state rows. Scope checks PASS')
