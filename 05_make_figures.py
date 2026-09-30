# -*- coding: utf-8 -*-
"""
Step 05: Figure generation (PNG) for the review pack.
Run after steps 01-04. Writes output/fig*.png
"""
import numpy as np
import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

here = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(here, '..', 'data')
out_dir = os.path.join(here, '..', 'output')
os.makedirs(out_dir, exist_ok=True)
VARIANT = 'n24_sig'

# ---------- load 40-gate table ----------
t40, clean, noisy, den_imp, den_soft = [], [], [], [], []
with open(os.path.join(data_dir, f'denoised_{VARIANT}.csv')) as f:
    r = csv.DictReader(f)
    for row in r:
        t40.append(float(row['t_center_ms']))
        clean.append(float(row['clean_uVA']))
        noisy.append(float(row['noisy_uVA']))
        den_imp.append(float(row['denoised_improved_uVA']))
        den_soft.append(float(row['denoised_soft_uVA']))
t40 = np.array(t40); clean = np.array(clean); noisy = np.array(noisy)
den_imp = np.array(den_imp); den_soft = np.array(den_soft)

# ---------- Fig 1: decay curves ----------
fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.loglog(t40, np.abs(clean), 'k-', lw=2, label='clean (truth)')
ax.loglog(t40, np.abs(noisy), '.', color='#c0392b', ms=5, label='noisy (24% signal-scaled)')
ax.loglog(t40, np.abs(den_imp), 'o-', color='#2980b9', ms=4, lw=1.2,
          label='denoised - improved soft threshold')
ax.loglog(t40, np.abs(den_soft), 's--', color='#27ae60', ms=3.5, lw=1,
          label='denoised - classical soft (baseline)')
ax.set_xlabel('center time (ms)')
ax.set_ylabel('|V| (uV/A)')
ax.set_title('Synthetic TEM decay curve - reference denoising pipeline\n'
             '(sym8 / 5-level / Rigrsure, per manuscript Table 1)')
ax.grid(True, which='both', alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(out_dir, 'fig1_decay.png'), dpi=200)
plt.close(fig)

# ---------- Fig 2: recomputed metrics by window ----------
WINDOWS = {'early\n(1-12)': (0, 12), 'middle\n(13-28)': (12, 28),
           'late\n(29-40)': (28, 40), 'all\n(1-40)': (0, 40)}

def snr(s, sh):
    e = np.sum((s - sh) ** 2)
    return 10 * np.log10(np.sum(s ** 2) / e)

def rmse(s, sh):
    return float(np.sqrt(np.mean((s - sh) ** 2)))

def mre(s, sh):
    return float(np.max(np.abs(s - sh) / np.maximum(np.abs(s), 1e-30)) * 100)

labels = list(WINDOWS.keys())
x = np.arange(len(labels))
series = {}
for name in ('noisy', 'denoised_improved', 'denoised_soft'):
    pass
snr_v = {'noisy': [], 'improved': [], 'soft': []}
rmse_v = {'noisy': [], 'improved': [], 'soft': []}
mre_v = {'noisy': [], 'improved': [], 'soft': []}
for lab, (a, b) in WINDOWS.items():
    cs, ns, di, ds = clean[a:b], noisy[a:b], den_imp[a:b], den_soft[a:b]
    snr_v['noisy'].append(snr(cs, ns)); snr_v['improved'].append(snr(cs, di))
    snr_v['soft'].append(snr(cs, ds))
    rmse_v['noisy'].append(rmse(cs, ns)); rmse_v['improved'].append(rmse(cs, di))
    rmse_v['soft'].append(rmse(cs, ds))
    mre_v['noisy'].append(mre(cs, ns)); mre_v['improved'].append(mre(cs, di))
    mre_v['soft'].append(mre(cs, ds))

colors = {'noisy': '#c0392b', 'improved': '#2980b9', 'soft': '#27ae60'}
fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.9))
for ax, metric, title in zip(axes,
                             (snr_v, rmse_v, mre_v),
                             ('SNR (dB)', 'RMSE (uV/A)', 'MRE (%)')):
    w = 0.25
    for i, key in enumerate(('noisy', 'improved', 'soft')):
        ax.bar(x + (i - 1) * w, metric[key], w, label=key, color=colors[key])
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set_title(title, fontsize=10)
    ax.grid(axis='y', alpha=0.3)
axes[0].legend(fontsize=7.5)
fig.suptitle('Recomputed metrics on the synthetic case - reference pipeline (%s noise)'
             % VARIANT, fontsize=10)
fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig(os.path.join(out_dir, 'fig2_metrics.png'), dpi=200)
plt.close(fig)

# ---------- Fig 3: audit of manuscript Table 2 ----------
MS = {'early': {'n': 12, 'RMSE_noisy': 0.285, 'RMSE_den': 0.038,
                'SNR_noisy': 24.5, 'SNR_den': 36.8},
      'middle': {'n': 16, 'RMSE_noisy': 0.124, 'RMSE_den': 0.016,
                 'SNR_noisy': 15.2, 'SNR_den': 29.4},
      'late': {'n': 12, 'RMSE_noisy': 0.082, 'RMSE_den': 0.007,
               'SNR_noisy': 5.8, 'SNR_den': 23.1},
      'all': {'n': 40, 'RMSE_noisy': 0.142, 'RMSE_den': 0.015,
              'SNR_noisy': 12.4, 'SNR_den': 28.7}}

agg_noisy = float(np.sqrt(sum(MS[w_]['RMSE_noisy'] ** 2 * MS[w_]['n']
                              for w_ in ('early', 'middle', 'late')) / 40))
agg_den = float(np.sqrt(sum(MS[w_]['RMSE_den'] ** 2 * MS[w_]['n']
                            for w_ in ('early', 'middle', 'late')) / 40))

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
# panel A: manuscript all-window RMSE vs window-weighted recomputation
ax = axes[0]
cats = ['noisy\n(manuscript 0.142)', 'noisy\n(weighted 0.180)',
        'denoised\n(manuscript 0.015)', 'denoised\n(weighted 0.0235)']
vals = [MS['all']['RMSE_noisy'], agg_noisy, MS['all']['RMSE_den'], agg_den]
bars = ax.bar(cats, vals, color=['#e67e22', '#c0392b', '#3498db', '#2980b9'])
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.004, '%.4f' % v,
            ha='center', fontsize=8)
ax.set_ylabel('RMSE (uV/A)')
ax.set_title('[A] Manuscript all-window RMSE vs\nwindow-weighted aggregation', fontsize=10)
ax.grid(axis='y', alpha=0.3)
ax.tick_params(axis='x', labelsize=7.5)

# panel B: reported SNR gain vs implied by RMSE ratio
ax = axes[1]
wl = ['early', 'middle', 'late', 'all']
rep = [MS[w_]['SNR_den'] - MS[w_]['SNR_noisy'] for w_ in wl]
imp = [20 * np.log10(MS[w_]['RMSE_noisy'] / MS[w_]['RMSE_den']) for w_ in wl]
x = np.arange(4)
ax.bar(x - 0.18, rep, 0.36, label='reported SNR gain (dB)', color='#8e44ad')
ax.bar(x + 0.18, imp, 0.36, label='implied by RMSE ratio (dB)', color='#16a085')
for i in range(4):
    ax.text(x[i] - 0.18, rep[i] + 0.3, '%.1f' % rep[i], ha='center', fontsize=8)
    ax.text(x[i] + 0.18, imp[i] + 0.3, '%.1f' % imp[i], ha='center', fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(wl)
ax.set_ylabel('dB')
ax.set_title('[B] Reported SNR gain vs gain implied by\nRMSE ratio (delta should be ~0)', fontsize=10)
ax.legend(fontsize=8)
ax.grid(axis='y', alpha=0.3)

fig.tight_layout()
fig.savefig(os.path.join(out_dir, 'fig3_audit.png'), dpi=200)
plt.close(fig)
print('figures written to output/fig1_decay.png, fig2_metrics.png, fig3_audit.png')
