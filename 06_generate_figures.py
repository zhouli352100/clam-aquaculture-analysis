import os
os.environ.setdefault('MPLCONFIGDIR',str(__import__('pathlib').Path(__file__).resolve().parent.parent/'07_QC_核验/matplotlib_config'))
import common as c
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
import numpy as np,datetime
from pathlib import Path
c.setup(c.args().root)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7.5,'ytick.labelsize':7.5,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'path','svg.hashsalt':'USDA-clams-step4-fixed','savefig.facecolor':'white','figure.facecolor':'white'})
a=c.readj(c.DATA/'analytic/annual.json');de=c.readj(c.DATA/'analytic/decomposition.json');audit=[]
def save(fig,n,rows,caption):
 out=c.FIGS/f'Figure_{n}';out.mkdir(parents=True,exist_ok=True);p=out/f'Figure{n}_FINAL';fig.set_size_inches(175/25.4,fig.get_figheight())
 for ext in ['pdf','svg','png']:
  kw={'metadata':{'CreationDate':datetime.datetime(2026,10,28,tzinfo=datetime.timezone.utc),'ModDate':datetime.datetime(2026,10,28,tzinfo=datetime.timezone.utc)}} if ext=='pdf' else {'metadata':{'Date':'2026-10-28'}} if ext=='svg' else {}
  fig.savefig(str(p)+'.'+ext,dpi=600,**kw)
 fig.savefig(out/f'Figure{n}_Preview.png',dpi=150);c.csvout(out/f'Figure{n}_Source_Data.csv',rows);c.textout(out/f'Figure{n}_Caption.md',caption);plt.close(fig)
def frame(ax):ax.grid(axis='y',color='#E3E7EB',lw=.5);ax.set_axisbelow(True)
# Figure 1 only observed census points; metrics have separate axes and units.
rows=[dict(r) for r in a if r['category'] in c.PRIMARY]
fig,axs=plt.subplots(3,2,figsize=(175/25.4,4.85));fig.subplots_adjust(left=.12,right=.97,bottom=.10,top=.91,wspace=.36,hspace=.55)
for i,cat in enumerate(c.PRIMARY):
 rr=[r for r in rows if r['category']==cat]
 for j,(key,unit,scale) in enumerate([('all_size_farms','Reporting farms',1),('Q_live_weight_1000_lb','Market-size live weight (million lb)',.001)]):
  ax=axs[i,j];ys=[r[key]*scale for r in rr];xs=[r['year'] for r in rr];ax.scatter(xs,ys,s=34,color=c.COLORS[cat],zorder=3,edgecolor='white',linewidth=.6);ax.set_ylim(0,max(ys)*1.30);ax.set_xlim(2011,2025);ax.set_xticks(c.YEARS);frame(ax)
  for x,y in zip(xs,ys):ax.annotate(f'{y:,.0f}' if scale==1 else f'{y:.3f}',(x,y),xytext=(0,7),textcoords='offset points',ha='center',fontsize=7.5)
  ax.set_ylabel('Farms' if j==0 else 'Million lb');ax.set_title(cat,loc='left',fontsize=8.5,color=c.COLORS[cat],pad=5)
fig.text(.12,.98,'A  Reporting farm numbers',fontweight='bold',fontsize=9,va='top')
fig.text(.61,.98,'B  Market-size live-weight sales',fontweight='bold',fontsize=9,va='top')
for ax in axs[-1,:]:ax.set_xlabel('Census year')
save(fig,1,rows,'Figure 1. Changes in reporting farm numbers and market-size live-weight sales among U.S. clam categories, 2013-2023.\n\nA uses national all-size reporting farm numbers; B uses food/market-size whole live-weight sales, in million lb. Sources: USDA Table 7, printed p. 10 in each census; clam all-size farms also checked against Table 19. Points are the three observed censuses; no intervening values are estimated. Axes are separate for each category and metric and start at zero. Category farm counts may overlap and must not be summed to unique operations. Weight sold is not total aquaculture production; the two panels do not identify farm productivity. Values above points are published counts or converted weight values.\n')
# Figure 2 signed components with net diamonds, complete prespecified primary grid.
rows=[r for r in de if r['category'] in c.PRIMARY and r['basis']=='2023 USD'];fig,axs=plt.subplots(3,1,figsize=(175/25.4,6.15),sharex=True);fig.subplots_adjust(left=.18,right=.97,top=.90,bottom=.10,hspace=.57)
qcol='#486B8C';ucol='#C48A37'
vals=[r[k]/1000 for r in rows if r['status']=='IDENTIFIED' for k in ['quantity_component_1000_USD','unit_value_component_1000_USD','delta_V_1000_USD']];xmin,xmax=min(vals),max(vals);span=xmax-xmin
for ax,cat in zip(axs,c.PRIMARY):
 ax.axvline(0,color='#444444',lw=.7);ax.set_title(cat,loc='left',fontweight='bold',color=c.COLORS[cat],pad=7);ax.set_yticks(range(3),[f'{x}-{y}' for x,y in c.PERIODS]);ax.set_ylim(2.6,-.6);ax.grid(axis='x',color='#E1E5EA',lw=.5);ax.set_axisbelow(True);ax.set_xlim(xmin-.16*span,xmax+.17*span)
 for i,(y0,y1) in enumerate(c.PERIODS):
  r=next(z for z in rows if (z['category'],z['from_year'],z['to_year'])==(cat,y0,y1))
  if r['status']!='IDENTIFIED':ax.text(.52,i,'NA: 2018 sales D',transform=ax.get_yaxis_transform(),ha='center',va='center',fontsize=7.8,color='#777777');continue
  q,u,v=[r[k]/1000 for k in ['quantity_component_1000_USD','unit_value_component_1000_USD','delta_V_1000_USD']];ax.barh(i-.16,q,height=.25,color=qcol);ax.barh(i+.16,u,height=.25,color=ucol);ax.plot(v,i,marker='D',color='#151515',markersize=4.5,linestyle='None',zorder=4)
  # Exact amounts belong to Tables 3/S2 and the source CSV; no text sits over bars or diamonds.
axs[-1].set_xlabel('Contribution or net change (million 2023 USD)')
fig.legend(handles=[plt.Rectangle((0,0),1,1,color=qcol,label='Quantity component'),plt.Rectangle((0,0),1,1,color=ucol,label='Unit-value component'),Line2D([],[],marker='D',color='#151515',linestyle='None',label='Net real sales change',markersize=4.5)],loc='upper center',bbox_to_anchor=(.5,.99),ncol=3,frameon=False,fontsize=7.5,columnspacing=1.3)
save(fig,2,rows,'Figure 2. Quantity and inflation-adjusted unit-value components of changes in market-size sales value.\n\nSigned bars show the symmetric quantity and unit-value components; black diamonds show their sum, the net change in sales value. All amounts are million 2023 USD, using CPI-U annual averages. Q is food/market-size live weight and P is matching adjusted V/Q. Periods are comparisons of census endpoints, not annual trajectories. Manila clams have suppressed 2018 market-size sales, so both adjacent comparisons are NA and have no bars or net marker. Exact numerical amounts are supplied in Table 3, Table S2 and the independent source CSV; the plot emphasizes component directions and magnitudes without overprinting amounts on bars or diamonds. Contributions are accounting components, not causal mechanisms or quality-adjusted price effects.\n')
# Figure 3 same-scope real unit values; no line connects or bridges suppressed years.
rows=[r for r in a if r['category'] in c.PRIMARY+c.REFERENCE];fig,axs=plt.subplots(2,3,figsize=(175/25.4,4.25));fig.subplots_adjust(left=.10,right=.98,bottom=.16,top=.91,hspace=.55,wspace=.43)
for i,(ax,cat) in enumerate(zip(axs.flat,c.PRIMARY+c.REFERENCE)):
 rr=[r for r in rows if r['category']==cat];valid=[r for r in rr if r['status']=='IDENTIFIED'];ys=[r['P_2023_USD_per_lb'] for r in valid];ax.scatter([r['year'] for r in valid],ys,s=30,color=c.COLORS[cat],edgecolor='white',linewidth=.6,zorder=3);ax.set_ylim(0,max(ys)*1.32);ax.set_xlim(2010.5,2025.5);ax.set_xticks(c.YEARS);ax.tick_params(axis='x',rotation=35);ax.set_title(cat,color=c.COLORS[cat],loc='left');frame(ax)
 for r in rr:
  if r['status']=='IDENTIFIED':ax.annotate(f"{r['P_2023_USD_per_lb']:.2f}",(r['year'],r['P_2023_USD_per_lb']),xytext=(0,7),textcoords='offset points',ha='center',fontsize=7)
  else:ax.text(r['year'],.12,'D',transform=ax.get_xaxis_transform(),ha='center',color='#777777',fontsize=8)
 if i%3==0:ax.set_ylabel('2023 USD/lb')
 if i>=3:ax.set_xlabel('Census year')
save(fig,3,rows,'Figure 3. Inflation-adjusted average unit value of market-size sales across cultured clam and reference shellfish categories.\n\nPoints show matching food/market-size sales value divided by whole live-weight sales, adjusted to 2023 USD using CPI-U. Only observed public values are plotted; D labels denote suppressed sales and do not represent zero. No points are joined. Panel-specific vertical scales start at zero; comparisons emphasize within-category changes. Commercial groups differ in product mix, quality and size, so levels are not prices of equivalent-quality products. Eastern refers to the published Table 7 label; the 2023 questionnaire code 12 wording is Eastern/Gulf Coast. Oyster and mussel categories are descriptive industry references. Source: USDA Table 7, printed p. 10, and BLS CUUR0000SA0 M13.\n')
# Registry links every drawn component to the precise CSV row and analytic value.
for n in [1,2,3]:
 p=c.FIGS/f'Figure_{n}/Figure{n}_Source_Data.csv';audit.append(dict(figure=n,source_csv=c.rawref(p),source_sha256=c.sha(p),note='Plot uses this exact in-memory analytic record list; no separate numeric transcription',width_mm=175,png_dpi=600))
c.csvout(c.QC/'formula_validation/FIGURE_SOURCE_REGISTER.csv',audit)
print('Generated three fresh main figures: vector PDF/SVG,600 dpi PNG,source CSV and captions')
