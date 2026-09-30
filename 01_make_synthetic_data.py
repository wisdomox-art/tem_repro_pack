# -*- coding: utf-8 -*-
"""
Step 01: Synthetic TEM data generator
=====================================
Generates a 40-channel synthetic transient electromagnetic (TEM) decay curve
following the acquisition window disclosed in the manuscript R2
(GEOTEM-1 instrument specification, cited as [21] in the manuscript):
center times 0.08 - 45.2 ms, logarithmically spaced, 40 gates.

Truth model
-----------
Late-time TEM response of a uniform half-space decays as a power law
V(t) = A * t**(-p),  p ~ 2.5  (Nabighian & Macnae convention).
Amplitude A is scaled so that the earliest gate is O(0.5) uV/A.

Noise models
------------
The manuscript states "5% broadband Gaussian white noise" without defining
the reference. This script therefore produces THREE noisy variants so that
the effect of the definition can be audited:

  (a) n5_sig   : sigma(t) = 0.05 * |V(t)|        (5% of instantaneous signal)
  (b) n5_fs    : sigma    = 0.05 * max|V|         (5% of full-scale)
  (c) n24_sig  : sigma(t) = 0.24 * |V(t)|         (the level implied by the
                 manuscript's reported all-window noisy SNR of 12.4 dB,
                 i.e. 20*log10(1/0.24) ~ 12.4 dB)

改进说明（v2）：真实 TEM 采集的是连续时序波形，40 道是按时间窗从时序中
积分得到的结果；小波去噪应作用在时序上。v1 直接在 40 道稀疏点上做 5 层
sym8 DWT，最深层每道仅剩 ~1-2 个系数，边界效应严重（pywt 显式警告），
去噪反而劣化（SNR 17.9 -> 2.5 dB）——这本身即说明 "40 道直接 5 层分解"
不可行。v2 生成 2048 点高分辨率时序，在其上完成 5 层分解后再分窗回 40 道。

Outputs
-------
data/synthetic_tem_clean.csv        40-gate clean curve (evaluation reference)
data/synthetic_tem_noisy.csv        40-gate noisy curves (three variants)
data/timeseries_clean.csv           2048-point clean time series (uV/A)
data/timeseries_noisy_<variant>.csv 2048-point noisy time series for DWT input
"""
import numpy as np
import csv
import os

rng = np.random.default_rng(42)

# ---- acquisition window (manuscript R2, Fig. 4 / GEOTEM-1 specification) ----
N_CH = 40
T_MIN_MS = 0.08
T_MAX_MS = 45.2
t_ms = np.logspace(np.log10(T_MIN_MS), np.log10(T_MAX_MS), N_CH)

# ---- gate boundaries (log-spaced) for window aggregation ----
edges = np.logspace(np.log10(T_MIN_MS * 0.9),
                    np.log10(T_MAX_MS * 1.1), N_CH + 1)

# ---- truth model: late-time power-law decay of a 100 Ohm·m half-space ----
P_DECAY = 2.5
A_AMP = 5.0e-3
V_clean = A_AMP * t_ms ** (-P_DECAY)
V_clean = V_clean / V_clean[0] * 0.55

# ---- noise variants on the 40-gate curve (for reporting) --------------------
def add_noise(sig, sigma_abs):
    return sig + rng.normal(0.0, sigma_abs, size=sig.shape)

V_n5_sig = add_noise(V_clean, 0.05 * np.abs(V_clean))
V_n5_fs = add_noise(V_clean, 0.05 * np.max(np.abs(V_clean)))
V_n24_sig = add_noise(V_clean, 0.24 * np.abs(V_clean))

# ---- high-resolution time series for wavelet denoising ---------------------
N_TS = 2048
t_ts = np.logspace(np.log10(T_MIN_MS), np.log10(T_MAX_MS), N_TS)
V_ts_clean = A_AMP * t_ts ** (-P_DECAY)
V_ts_clean = V_ts_clean / V_ts_clean[0] * 0.55

def add_noise_ts(sig, mode):
    if mode == 'n5_sig':
        return sig + rng.normal(0.0, 0.05 * np.abs(sig))
    if mode == 'n5_fs':
        return sig + rng.normal(0.0, 0.05 * np.max(np.abs(sig)))
    if mode == 'n24_sig':
        return sig + rng.normal(0.0, 0.24 * np.abs(sig))

variants = ['n5_sig', 'n5_fs', 'n24_sig']

# ---- write CSVs --------------------------------------------------------------
here = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(here, '..', 'data')
os.makedirs(out_dir, exist_ok=True)

with open(os.path.join(out_dir, 'synthetic_tem_clean.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['gate', 't_center_ms', 'V_clean_uVA'])
    for i in range(N_CH):
        w.writerow([i + 1, f'{t_ms[i]:.5f}', f'{V_clean[i]:.6e}'])

with open(os.path.join(out_dir, 'synthetic_tem_noisy.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['gate', 't_center_ms',
                'V_n5_sig_uVA', 'V_n5_fs_uVA', 'V_n24_sig_uVA'])
    for i in range(N_CH):
        w.writerow([i + 1, f'{t_ms[i]:.5f}',
                    f'{V_n5_sig[i]:.6e}', f'{V_n5_fs[i]:.6e}',
                    f'{V_n24_sig[i]:.6e}'])

# ---- time series CSVs --------------------------------------------------------
with open(os.path.join(out_dir, 'timeseries_clean.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['t_ms', 'V_clean_uVA'])
    for i in range(N_TS):
        w.writerow([f'{t_ts[i]:.6f}', f'{V_ts_clean[i]:.6e}'])

for var in variants:
    ts = add_noise_ts(V_ts_clean, var)
    with open(os.path.join(out_dir, f'timeseries_noisy_{var}.csv'), 'w',
              newline='') as f:
        w = csv.writer(f)
        w.writerow(['t_ms', f'V_{var}_uVA'])
        for i in range(N_TS):
            w.writerow([f'{t_ts[i]:.6f}', f'{ts[i]:.6e}'])

print('channels       :', N_CH)
print('window (ms)    : %.3f - %.2f' % (T_MIN_MS, T_MAX_MS))
print('dynamic range  : %.2e  ->  %.2e  uV/A' % (V_clean[0], V_clean[-1]))
print('time series    :', N_TS, 'log-spaced points (DWT input)')
for var in variants:
    print('written        : data/timeseries_noisy_%s.csv' % var)
