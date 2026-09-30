# -*- coding: utf-8 -*-
"""
Step 02: Wavelet denoising pipeline
===================================
Reference implementation of the denoising configuration disclosed in the
manuscript R2 (its Table 1 "key parameters"):

    mother wavelet : Symlets-8 (sym8)
    decomposition  : 5-level discrete wavelet transform (DWT)
    threshold rule : Rigrsure (Stein's unbiased risk estimate)
    shrinkage      : "improved nonlinear soft threshold" (explicit functional
                     form NOT disclosed in the manuscript)

Because the manuscript does not disclose the explicit functional form of its
"improved" threshold, this script implements TWO shrinkage operators:

    soft       : classical Donoho-Johnstone soft threshold
                 eta(w) = sign(w) * max(|w| - T, 0)

    improved   : a continuous-derivative improved soft threshold used in the
                 improved-threshold literature,
                 eta(w) = sign(w) * (|w| - T)_+ * (1 - exp(-beta*(|w|-T)_+/T))
                 with beta = 2.0 (parameterized; replace with the authors'
                 exact form when disclosed)

改进说明（v2）：去噪在 2048 点高分辨率时序上进行（见 01 脚本），去噪后
按 40 道对数时间窗边界分窗平均，回到 40 道评估口径——与稿件表 2 的
"测道"概念对齐。v1 在 40 点序列上直接做 5 层分解因边界效应失败。

Usage
-----
    python3 02_denoise_wavelet.py [n5_sig|n5_fs|n24_sig]
Default input column: n24_sig (the noise level implied by the manuscript's
reported all-window noisy SNR of 12.4 dB).

Outputs
-------
data/denoised_<variant>.csv   40-gate table: clean / noisy / denoised (improved
                              and classical soft threshold)
"""
import numpy as np
import csv
import os
import sys
import pywt

here = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(here, '..', 'data')

WAVELET = 'sym8'
LEVELS = 5
BETA = 2.0  # parameter of the improved soft threshold
N_CH = 40
T_MIN_MS = 0.08
T_MAX_MS = 45.2


def rigrsure_threshold(coeffs):
    """Stein's unbiased risk estimate (SURE) threshold."""
    n = len(coeffs)
    if n == 0:
        return 0.0
    s = np.sort(np.abs(coeffs)) ** 2
    cs = np.cumsum(s)
    idx = np.arange(1, n + 1)
    risk = (n - 2 * idx + cs + s * (n - idx)) / n
    best = np.argmin(risk)
    return float(np.sqrt(s[best]))


def soft_threshold(c, T):
    return np.sign(c) * np.maximum(np.abs(c) - T, 0.0)


def improved_soft_threshold(c, T, beta=BETA):
    d = np.maximum(np.abs(c) - T, 0.0)
    factor = 1.0 - np.exp(-beta * d / T) if T > 0 else 1.0
    return np.sign(c) * d * factor


def denoise(signal, shrink='improved'):
    max_level = pywt.dwt_max_level(len(signal), pywt.Wavelet(WAVELET).dec_len)
    lvl = min(LEVELS, max_level)
    coeffs = pywt.wavedec(signal, WAVELET, level=lvl)
    new_coeffs = [coeffs[0]]  # keep approximation coefficients untouched
    for detail in coeffs[1:]:
        T = rigrsure_threshold(detail)
        if shrink == 'soft':
            new_coeffs.append(soft_threshold(detail, T))
        else:
            new_coeffs.append(improved_soft_threshold(detail, T))
    return pywt.waverec(new_coeffs, WAVELET)[: len(signal)]


def window_aggregation(t_ts, v_ts):
    """Aggregate a high-resolution time series into the 40 TEM gates."""
    edges = np.logspace(np.log10(T_MIN_MS * 0.9),
                        np.log10(T_MAX_MS * 1.1), N_CH + 1)
    centers = np.logspace(np.log10(T_MIN_MS), np.log10(T_MAX_MS), N_CH)
    out = np.zeros(N_CH)
    for g in range(N_CH):
        m = (t_ts >= edges[g]) & (t_ts < edges[g + 1])
        out[g] = v_ts[m].mean() if m.any() else np.interp(centers[g], t_ts, v_ts)
    return out


def main():
    variant = sys.argv[1] if len(sys.argv) > 1 else 'n24_sig'

    # -- 40-gate clean reference --
    clean = []
    with open(os.path.join(data_dir, 'synthetic_tem_clean.csv')) as f:
        r = csv.DictReader(f)
        for row in r:
            clean.append(float(row['V_clean_uVA']))

    # -- 40-gate noisy (reporting reference, same RNG stream as 01) --
    noisy40 = []
    with open(os.path.join(data_dir, 'synthetic_tem_noisy.csv')) as f:
        r = csv.DictReader(f)
        for row in r:
            noisy40.append(float(row[f'V_{variant}_uVA']))

    # -- high-resolution noisy time series for DWT --
    t_ts, v_ts = [], []
    with open(os.path.join(data_dir, f'timeseries_noisy_{variant}.csv')) as f:
        r = csv.DictReader(f)
        for row in r:
            t_ts.append(float(row['t_ms']))
            v_ts.append(float(row[f'V_{variant}_uVA']))
    t_ts = np.array(t_ts)
    v_ts = np.array(v_ts)

    den_ts_imp = denoise(v_ts, 'improved')
    den_ts_soft = denoise(v_ts, 'soft')

    den40_imp = window_aggregation(t_ts, den_ts_imp)
    den40_soft = window_aggregation(t_ts, den_ts_soft)

    out = os.path.join(data_dir, f'denoised_{variant}.csv')
    with open(out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['gate', 't_center_ms', 'clean_uVA', 'noisy_uVA',
                    'denoised_improved_uVA', 'denoised_soft_uVA'])
        t40 = np.logspace(np.log10(T_MIN_MS), np.log10(T_MAX_MS), N_CH)
        for i in range(N_CH):
            w.writerow([i + 1, f'{t40[i]:.5f}', f'{clean[i]:.6e}',
                        f'{noisy40[i]:.6e}', f'{den40_imp[i]:.6e}',
                        f'{den40_soft[i]:.6e}'])
    print('variant  :', variant)
    print('wavelet  :', WAVELET, '| levels:', LEVELS,
          '(on %d-point time series)' % len(v_ts))
    print('rule     : rigrsure | shrink: improved + classical-soft baseline')
    print('written  :', os.path.relpath(out, os.path.join(here, '..')))


if __name__ == '__main__':
    main()
