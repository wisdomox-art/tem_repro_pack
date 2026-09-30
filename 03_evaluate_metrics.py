# -*- coding: utf-8 -*-
"""
Step 03: Metric evaluation (SNR / RMSE / MRE)
=============================================
Computes the three quality metrics used in the manuscript R2 (its Eqs. 9-11),
on four windows identical to the manuscript's Table 2:

    early  : gates 1-12   (0.080 - 0.650 ms)
    middle : gates 13-28  (0.820 - 8.450 ms)
    late   : gates 29-40  (10.70 - 45.20 ms)
    all    : gates 1-40  (0.080 - 45.20 ms)

Metric definitions (standard in the signal-denoising literature):
    SNR  = 10 * log10( sum(s^2) / sum((s - s_hat)^2) )      [dB]
    RMSE = sqrt( mean( (s - s_hat)^2 ) )
    MRE  = max( |s - s_hat| / |s| ) * 100                   [%]

NOTE: The manuscript does not print the explicit definitions of Eqs. 9-11.
If the authors' SNR uses a different convention (e.g. 20*log10 of amplitude
ratio, or mean-squared-error normalised differently), the numbers will shift
systematically. This is exactly the ambiguity flagged in Review Comment #1.

Outputs
-------
output/metrics_<variant>.csv
"""
import numpy as np
import csv
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(here, '..', 'data')
out_dir = os.path.join(here, '..', 'output')
os.makedirs(out_dir, exist_ok=True)

WINDOWS = {
    'early':  (0, 12),
    'middle': (12, 28),
    'late':   (28, 40),
    'all':    (0, 40),
}


def snr_db(s, sh):
    e = np.sum((s - sh) ** 2)
    return 10.0 * np.log10(np.sum(s ** 2) / e) if e > 0 else np.inf


def rmse(s, sh):
    return float(np.sqrt(np.mean((s - sh) ** 2)))


def mre_pct(s, sh):
    d = np.abs(s - sh) / np.maximum(np.abs(s), 1e-30)
    return float(np.max(d) * 100.0)


def evaluate(clean, noisy, denoised, tag):
    rows = []
    for name, (a, b) in WINDOWS.items():
        cs, ns, ds = clean[a:b], noisy[a:b], denoised[a:b]
        rows.append([tag, name, f'{snr_db(cs, ns):.2f}', f'{rmse(cs, ns):.4f}',
                     f'{mre_pct(cs, ns):.2f}'])
        rows.append([tag, name, f'{snr_db(cs, ds):.2f}', f'{rmse(cs, ds):.4f}',
                     f'{mre_pct(cs, ds):.2f}'])
    return rows


def main():
    variant = sys.argv[1] if len(sys.argv) > 1 else 'n24_sig'
    fpath = os.path.join(data_dir, f'denoised_{variant}.csv')
    clean, noisy, den_i, den_s = [], [], [], []
    with open(fpath) as f:
        r = csv.DictReader(f)
        for row in r:
            clean.append(float(row['clean_uVA']))
            noisy.append(float(row['noisy_uVA']))
            den_i.append(float(row['denoised_improved_uVA']))
            den_s.append(float(row['denoised_soft_uVA']))

    clean = np.array(clean)
    noisy = np.array(noisy)
    den_i = np.array(den_i)
    den_s = np.array(den_s)

    rows = []
    rows.append(['variant', 'window', 'state', 'SNR_dB', 'RMSE_uVA', 'MRE_pct'])
    for name, (a, b) in WINDOWS.items():
        cs, ns, di, ds_ = clean[a:b], noisy[a:b], den_i[a:b], den_s[a:b]
        for state, arr in (('noisy', ns), ('denoised_improved', di),
                           ('denoised_soft', ds_)):
            rows.append([variant, name, state, f'{snr_db(cs, arr):.2f}',
                         f'{rmse(cs, arr):.4f}', f'{mre_pct(cs, arr):.2f}'])

    out = os.path.join(out_dir, f'metrics_{variant}.csv')
    with open(out, 'w', newline='') as f:
        csv.writer(f).writerows(rows)
    print('written:', os.path.relpath(out, os.path.join(here, '..')))
    # console echo, 'all' window
    print('\n--- all-window summary (%s) ---' % variant)
    print('state              SNR_dB   RMSE_uVA   MRE_%')
    for r in rows:
        if r[1] == 'all':
            print('%-18s %7s  %9s  %6s' % (r[2], r[3], r[4], r[5]))


if __name__ == '__main__':
    main()
