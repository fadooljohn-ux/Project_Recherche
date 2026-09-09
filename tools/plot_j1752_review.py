"""Plot saved focused-review outputs; no new fits or simulations."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1]
E=R/'results/research/j1752-focused-review-20260909'
D=R.parent/'Project Recherche Data/j1752-focused-review-20260909'
O=R/'output/pdf/j1752-figures';O.mkdir(parents=True,exist_ok=True)
j=json.loads((E/'joint.json').read_text());n=json.loads((E/'null-generators.json').read_text());p=json.loads((E/'propagation.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
colors=['#245781','#b35422','#43816c']
fig,ax=plt.subplots(figsize=(8.3,3.2))
for m,c in zip(j['models'],colors):
 periods=np.array([r['period_days'] for r in m['profile']]);q=np.array([r['objective'] for r in m['profile']])
 ax.plot(periods,m['null_objective']-q,color=c,label=f"{m['modes']} modes")
ax.axvline(81.7518653,color='0.5',ls=':',lw=1);ax.axhline(0,color='0.8',lw=.7)
ax.set(xlabel='Trial period (days)',ylabel='Joint fit improvement in Q');ax.legend(frameon=False,ncol=3);fig.tight_layout();fig.savefig(O/'joint-profile.png');plt.close(fig)
arr=np.load(D/'null-arrays.npz');fig,ax=plt.subplots(figsize=(8.3,3.2))
labels=['Earlier steeper 64 (reused)','Released 12','Published 64','Fitted 32-mode null']
for key,label,c in zip(arr.files,labels,['#888888']+colors):
 s=np.sort(arr[key]);ax.step(s,(len(s)-np.arange(len(s)))/len(s),where='post',label=label,color=c)
ax.axvline(n['observed_candidate_statistic'],color='black',ls='--',label='Observed first-review statistic')
ax.set(yscale='log',xlabel='First-review family statistic',ylabel='Empirical survival fraction',ylim=(.001,1.2));ax.legend(frameon=False,fontsize=8);fig.tight_layout();fig.savefig(O/'null-generators.png');plt.close(fig)
pa=np.load(D/'propagation-arrays.npz');fig,axs=plt.subplots(1,2,figsize=(8.3,3.3))
for m,c in zip(p['models'],colors):
 k=f"m{m['modes']}";axs[0].hist(pa[k+'_periods'],bins=35,histtype='step',density=True,color=c,label=f"{m['modes']} modes")
 q=np.quantile(pa[k+'_power'],[.05,.5,.95])*100
 axs[1].errorbar(q[1],m['modes'],xerr=[[q[1]-q[0]],[q[2]-q[1]]],fmt='o',capsize=3,color=c)
axs[0].set(xlabel='Local sampled period (days)',ylabel='Profile-weighted density');axs[0].legend(frameon=False,fontsize=8)
axs[1].set(xlabel='Conditional TPA detection power (%)',ylabel='Red-noise modes',yticks=[12,32,64],xlim=(0,65));fig.tight_layout();fig.savefig(O/'tpa-uncertainty.png');plt.close(fig)
print(O)
