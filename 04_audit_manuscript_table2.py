# -*- coding: utf-8 -*-
"""
Step 04: Independent audit of manuscript Table 2 (denoising metrics)
====================================================================
This script does NOT re-run any model. It takes the numbers printed in the
manuscript R2 (its Table 2) as given and checks their INTERNAL arithmetic
consistency - the checks behind Review Comment #1 of the 2026-09-30 report.

Checks performed
----------------
A. Window-weighted RMSE aggregation
   If per-window RMSE values are each computed within their own gates,
   the all-window RMSE must equal
       sqrt( sum_i( RMSE_i^2 * N_i ) / 40 )
   The manuscript reports per-window and all-window values that do not
   satisfy this relation.

B. SNR-gain vs RMSE-ratio consistency
   Under the standard definitions used in Step 03, and when noise and
   residual are measured against the same truth,
       SNR_gain(dB)  =  20 * log10( RMSE_noisy / RMSE_denoised )
   The manuscript's all-window figures (16.3 dB vs a 9.5x ratio ~ 19.6 dB)
   violate this relation.

C. Implied noise level from reported noisy SNR
   A statement "5% Gaussian noise" has an unambiguous meaning once the
   reference is specified. The reported all-window noisy SNR of 12.4 dB
   implies a noise/signal amplitude ratio of ~24% under the standard
   energy definition.

Outputs
-------
output/audit_report_<variant>.txt
"""
import numpy as np
import os

here = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(here, '..', 'output')
os.makedirs(out_dir, exist_ok=True)

# ---- numbers as printed in manuscript R2, Table 2 ---------------------------
MS = {
    'early':  {'n': 12, 'SNR_noisy': 24.5, 'SNR_den': 36.8,
               'RMSE_noisy': 0.285, 'RMSE_den': 0.038,
               'MRE_noisy': 12.4, 'MRE_den': 3.1},
    'middle': {'n': 16, 'SNR_noisy': 15.2, 'SNR_den': 29.4,
               'RMSE_noisy': 0.124, 'RMSE_den': 0.016,
               'MRE_noisy': 28.6, 'MRE_den': 5.4},
    'late':   {'n': 12, 'SNR_noisy': 5.8, 'SNER_den': 23.1,
               'SNR_den': 23.1,
               'RMSE_noisy': 0.082, 'RMSE_den': 0.007,
               'MRE_noisy': 68.2, 'MRE_den': 8.7},
    'all':    {'n': 40, 'SNR_noisy': 12.4, 'SNR_den': 28.7,
               'RMSE_noisy': 0.142, 'RMSE_den': 0.015,
               'MRE_noisy': 68.2, 'MRE_den': 8.7},
}


def check_A():
    """Weighted RMSE aggregation across windows."""
    num_noisy = sum(MS[w]['RMSE_noisy'] ** 2 * MS[w]['n'] for w in
                    ('early', 'middle', 'late'))
    num_den = sum(MS[w]['RMSE_den'] ** 2 * MS[w]['n'] for w in
                  ('early', 'middle', 'late'))
    agg_noisy = np.sqrt(num_noisy / 40)
    agg_den = np.sqrt(num_den / 40)
    return {
        'expected_all_RMSE_noisy': round(float(agg_noisy), 4),
        'manuscript_all_RMSE_noisy': MS['all']['RMSE_noisy'],
        'expected_all_RMSE_denoised': round(float(agg_den), 4),
        'manuscript_all_RMSE_denoised': MS['all']['RMSE_den'],
        'consistent': bool(abs(agg_noisy - MS['all']['RMSE_noisy']) < 0.01
                           and abs(agg_den - MS['all']['RMSE_den']) < 0.01),
    }


def check_B():
    """SNR gain must equal 20*log10(RMSE_noisy / RMSE_denoised)."""
    out = {}
    for w, d in MS.items():
        implied_db = 20 * np.log10(d['RMSE_noisy'] / d['RMSE_den'])
        reported_gain = d['SNR_den'] - d['SNR_noisy']
        out[w] = {
            'reported_SNR_gain_dB': round(reported_gain, 2),
            'implied_by_RMSE_ratio_dB': round(float(implied_db), 2),
            'delta_dB': round(float(reported_gain - implied_db), 2),
        }
    return out


def check_C():
    """Noise level implied by the reported all-window noisy SNR."""
    s = MS['all']['SNR_noisy']
    ratio = 10 ** (-s / 20.0)         # amplitude ratio noise/signal
    return {
        'reported_all_window_SNR_dB': s,
        'implied_noise_over_signal_pct': round(float(ratio * 100), 1),
        'manuscript_claim': '5% Gaussian noise',
    }


def main():
    a = check_A()
    b = check_B()
    c = check_C()

    lines = []
    lines.append('INDEPENDENT ARITHMETIC AUDIT - Manuscript R2, Table 2')
    lines.append('(numbers taken from the manuscript; no model re-run)')
    lines.append('=' * 60)
    lines.append('')
    lines.append('[A] Window-weighted RMSE aggregation')
    lines.append('    expected all-window RMSE (noisy)   = %.3f   (manuscript: %.3f)'
                 % (a['expected_all_RMSE_noisy'], a['manuscript_all_RMSE_noisy']))
    lines.append('    expected all-window RMSE (denoised)= %.4f   (manuscript: %.3f)'
                 % (a['expected_all_RMSE_denoised'], a['manuscript_all_RMSE_denoised']))
    lines.append('    CONSISTENT: %s' % a['consistent'])
    lines.append('')
    lines.append('[B] SNR-gain vs RMSE-ratio consistency (delta should be ~0)')
    for w in ('early', 'middle', 'late', 'all'):
        lines.append('    %-6s reported %6.2f dB | implied %6.2f dB | delta %+6.2f dB'
                     % (w, b[w]['reported_SNR_gain_dB'],
                        b[w]['implied_by_RMSE_ratio_dB'], b[w]['delta_dB']))
    lines.append('')
    lines.append('[C] Noise level implied by reported noisy SNR')
    lines.append('    reported all-window noisy SNR = %.1f dB' % c['reported_all_window_SNR_dB'])
    lines.append('    implied noise/signal amplitude = %.1f %%   (claim: %s)'
                 % (c['implied_noise_over_signal_pct'], c['manuscript_claim']))
    lines.append('')
    lines.append('Interpretation: see Review Comment #1 of the 2026-09-30 report.')

    txt = '\n'.join(lines)
    out = os.path.join(out_dir, 'audit_report_manuscript_table2.txt')
    with open(out, 'w') as f:
        f.write(txt)
    print(txt)
    print('\nwritten:', os.path.relpath(out, os.path.join(here, '..')))


if __name__ == '__main__':
    main()
