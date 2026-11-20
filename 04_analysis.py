import common as c
from itertools import product
from decimal import Decimal,localcontext
c.setup(c.args().root)
a=c.readj(c.DATA/'harmonized/national.json');cp=c.readj(c.DATA/'raw_extracted/CPI.json');cpmap={r['year']:r['annual_CPI_U'] for r in cp};base=cpmap[2023]
for r in cp:r['factor_to_2023']=base/r['annual_CPI_U']
for r in a:
 f=base/cpmap[r['year']];r.update(CPI_U=cpmap[r['year']],deflator_2023=f,V_1000_2023_USD=None if r['V_nominal_1000_USD'] is None else r['V_nominal_1000_USD']*f,P_2023_USD_per_lb=None if r['P_nominal_USD_per_lb'] is None else r['P_nominal_USD_per_lb']*f)
decomp=[];growth=[];rounding=[];pricechecks=[];ident=[]
def find(cat,y):return next(r for r in a if r['category']==cat and r['year']==y)
def calc(v0,v1,q0,q1):
 p0,p1=v0/q0,v1/q1;dq=(q1-q0)*(p0+p1)/2;dp=(p1-p0)*(q0+q1)/2;return v1-v0,dq,dp,p0,p1
for cat in c.CATEGORIES:
 for y0,y1 in c.PERIODS:
  s,t=find(cat,y0),find(cat,y1)
  gr=dict(category=cat,from_year=y0,to_year=y1)
  for k in ['all_size_farms','V_nominal_1000_USD','V_1000_2023_USD','Q_live_weight_1000_lb','N_sold_1000','P_nominal_USD_per_lb','P_2023_USD_per_lb']:gr[k+'_from']=s[k];gr[k+'_to']=t[k];gr[k+'_change']=None if s[k] is None or t[k] is None else t[k]-s[k];gr[k+'_pct']=c.pct(s[k],t[k])
  growth.append(gr)
  for basis,vcol in [('nominal','V_nominal_1000_USD'),('2023 USD','V_1000_2023_USD')]:
   v0,v1,q0,q1=s[vcol],t[vcol],s['Q_live_weight_1000_lb'],t['Q_live_weight_1000_lb'];ok=all(v is not None for v in [v0,v1,q0,q1]) and q0>0 and q1>0
   r=dict(category=cat,role=c.role(cat),from_year=y0,to_year=y1,basis=basis,status='IDENTIFIED' if ok else 'NOT_IDENTIFIED',reason='' if ok else '; '.join(f"{x['year']} {x['reason']}" for x in [s,t] if x['status']!='IDENTIFIED'),V0_1000_USD=v0,V1_1000_USD=v1,Q0_1000_lb=q0,Q1_1000_lb=q1,delta_V_1000_USD=None,quantity_component_1000_USD=None,unit_value_component_1000_USD=None,P0_USD_per_lb=None,P1_USD_per_lb=None,identity_residual_1000_USD=None)
   if ok:
    dv,cq,cu,p0,p1=calc(v0,v1,q0,q1);res=dv-cq-cu;assert abs(res)<1e-8;r.update(delta_V_1000_USD=dv,quantity_component_1000_USD=cq,unit_value_component_1000_USD=cu,P0_USD_per_lb=p0,P1_USD_per_lb=p1,identity_residual_1000_USD=res)
    # Independent high precision calculation starts from raw printed V/Q and raw CPI.
    with localcontext() as ctx:
     ctx.prec=45;D=Decimal;vv0=D(s['V_raw'].replace(',',''));vv1=D(t['V_raw'].replace(',',''));qq0=D(s['Q_raw'].replace(',',''));qq1=D(t['Q_raw'].replace(',',''))
     if basis=='2023 USD':vv0*=D(str(base))/D(str(cpmap[y0]));vv1*=D(str(base))/D(str(cpmap[y1]))
     pp0,pp1=vv0/qq0,vv1/qq1;dcq=pp0*(qq1-qq0)+(pp1-pp0)*(qq1-qq0)/2;dcu=qq0*(pp1-pp0)+(pp1-pp0)*(qq1-qq0)/2;dr=vv1-vv0-dcq-dcu
     assert abs(dr)<D('1e-35');assert abs(float(dcq)-cq)<1e-8 and abs(float(dcu)-cu)<1e-8
     ident.append(dict(category=cat,from_year=y0,to_year=y1,basis=basis,float_residual=res,decimal_residual=str(dr),quantity_independent=float(dcq),unit_value_independent=float(dcu),match=True))
    # Publication rounding corners, not confidence intervals.
    corners=[]
    for e in product([-.5,.5],repeat=4):
     z0=(s['V_nominal_1000_USD']+e[0])*(s['deflator_2023'] if basis=='2023 USD' else 1);z1=(t['V_nominal_1000_USD']+e[1])*(t['deflator_2023'] if basis=='2023 USD' else 1)
     corners.append(calc(z0,z1,q0+e[2],q1+e[3]))
    sen={k+suffix:f(z[i] for z in corners) for i,k in enumerate(['delta_V','quantity','unit_value']) for suffix,f in [('_min',min),('_max',max)]}
    sen.update(category=cat,from_year=y0,to_year=y1,basis=basis,unit='1000 USD of stated basis',scope='16 endpoint corners; publication rounding only; not confidence intervals',quantity_sign_stable=sen['quantity_min']*sen['quantity_max']>0,unit_value_sign_stable=sen['unit_value_min']*sen['unit_value_max']>0,P_change_pct_min=min((z[4]/z[3]-1)*100 for z in corners),P_change_pct_max=max((z[4]/z[3]-1)*100 for z in corners));rounding.append(sen)
   decomp.append(r)
for r in a:
 if r['status']!='IDENTIFIED':continue
 v,q,p=r['V_nominal_1000_USD'],r['Q_live_weight_1000_lb'],r['official_average_price_USD_per_lb'];lo,hi=(v-.5)/(q+.5),(v+.5)/(q-.5);ok=lo<=p+.005 and hi>=p-.005;assert ok,(r['category'],r['year'])
 pricechecks.append(dict(category=r['category'],year=r['year'],V_1000_USD=v,Q_1000_lb=q,recomputed_P=v/q,official_P=p,recomputed_lower=lo,recomputed_upper=hi,official_rounding_lower=p-.005,official_rounding_upper=p+.005,rounding_intervals_overlap=ok,note='Published V/Q rounded to whole thousands; official P to cents. Overlap, not forced point equality.'))
assert sum(r['status']=='IDENTIFIED' for r in a)==16
assert len(decomp)==42 and sum(r['status']=='IDENTIFIED' for r in decomp)==28
c.writej(c.DATA/'analytic/annual.json',a);c.csvout(c.DATA/'analytic/annual.csv',a);c.writej(c.DATA/'analytic/decomposition.json',decomp);c.csvout(c.DATA/'analytic/decomposition.csv',decomp);c.csvout(c.DATA/'analytic/changes.csv',growth);c.writej(c.DATA/'analytic/changes.json',growth)
c.writej(c.DATA/'analytic/CPI.json',cp);c.csvout(c.DATA/'analytic/CPI.csv',cp);c.writej(c.DATA/'analytic/rounding.json',rounding);c.csvout(c.DATA/'analytic/rounding.csv',rounding);c.writej(c.DATA/'analytic/official_price_checks.json',pricechecks);c.csvout(c.QC/'formula_validation/DECIMAL_IDENTITY_CHECK.csv',ident)
print('Analysis PASS:16 eligible category-years,28 identified decompositions,14 explicitly unavailable,16 official price reconciliations')
