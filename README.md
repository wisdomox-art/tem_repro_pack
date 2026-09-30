# Reproducibility Pack — TEM Denoising Reference Pipeline & Manuscript Table 2 Audit

**Prepared for**: zhaoyangyang@92xueshu.com
**Date**: 2026-09-30
**Companion document**: APR Review Report R2, `APR评审报告_R2_含水构造TEM论文_20260930.docx` (Review Comments #1 and #4)

---

## 1. What this pack is

This pack provides (a) a **runnable English reference implementation** of the denoising
pipeline disclosed in the manuscript R2, and (b) an **independent arithmetic audit** of
the numbers printed in the manuscript's Table 2 (denoising performance).

It is built **only from parameters the manuscript itself discloses**. It does **not**
reconstruct the manuscript's 3-D forward model (grid, boundary conditions, transmitter
waveform are not disclosed — see Review Comment #4) and it uses **demonstration-grade
synthetic data**, not the authors' raw data.

> Bottom line: the reference pipeline runs end-to-end and improves the noisy signal,
> but its gain (+1.4 dB SNR, single realisation) is far below the manuscript's claimed
> +16.3 dB, and the manuscript's Table 2 fails three internal consistency checks
> (Section 5). This does not prove the manuscript's results are wrong — it shows they
> are **not currently checkable**, which is exactly what Review Comments #1/#4 require
> the authors to fix.

## 2. Package contents

```
tem_repro_pack/
├── README.md                          (this file)
├── data/
│   ├── synthetic_tem_clean.csv        40-gate clean decay curve (evaluation reference)
│   ├── synthetic_tem_noisy.csv        40-gate noisy curves, three noise definitions
│   ├── timeseries_clean.csv           2048-point clean time series (uV/A)
│   ├── timeseries_noisy_<variant>.csv 2048-point noisy series (DWT input)
│   └── denoised_<variant>.csv         40-gate clean/noisy/denoised table
├── src/
│   ├── 01_make_synthetic_data.py      synthetic data generator
│   ├── 02_denoise_wavelet.py          wavelet denoising (manuscript parameters)
│   ├── 03_evaluate_metrics.py         SNR / RMSE / MRE evaluation, 4 windows
│   ├── 04_audit_manuscript_table2.py  independent arithmetic audit of manuscript Table 2
│   └── 05_make_figures.py             figure generation (PNG)
└── output/
    ├── metrics_<variant>.csv          recomputed metric table
    ├── audit_report_manuscript_table2.txt
    ├── fig1_decay.png                 decay curves
    ├── fig2_metrics.png               recomputed metrics by window
    └── fig3_audit.png                 audit of manuscript Table 2
```

## 3. Method, aligned with manuscript disclosures

| Step | Manuscript disclosure | This pack |
|------|----------------------|-----------|
| Acquisition window | 40 gates, 0.08–45.2 ms (GEOTEM-1 spec, cited [21]) | identical log-spaced window |
| Truth model | not disclosed | late-time power law V=A·t^-2.5, 100 Ω·m half-space, earliest gate ~0.55 µV/A |
| Noise | "5% broadband Gaussian white noise" (reference undefined) | three variants: `n5_sig` (5% of instantaneous signal), `n5_fs` (5% of full scale), `n24_sig` (24% of signal — the level implied by the manuscript's reported all-window noisy SNR of 12.4 dB) |
| Wavelet | Symlets-8 (sym8) | sym8 |
| Decomposition | 5-level DWT | 5-level DWT **on the 2048-point time series** |
| Threshold rule | Rigrsure (Stein unbiased risk) | identical implementation |
| Shrinkage | "improved nonlinear soft threshold" (form undisclosed) | classical soft threshold (baseline) + a continuous-derivative improved variant (β=2). **Replace with the authors' exact form when disclosed.** |
| Metrics | Eqs. (9)-(11) (definitions not printed) | standard definitions: SNR=10·log10(Σs²/Σ(s-ŝ)²) dB; RMSE=√mean((s-ŝ)²); MRE=max(\|s-ŝ\|/\|s\|)·100 % |
| Windows | early 1-12 / middle 13-28 / late 29-40 / all 1-40 | identical |

**Why denoise on a 2048-point time series instead of the 40 gates?**
Our first implementation applied the 5-level DWT directly to the 40-gate curve.
PyWavelets then warns that level 5 is too high (boundary effects dominate; the
deepest level holds ~1-2 coefficients). Denoising *degraded* the signal
(SNR 17.9 → 2.5 dB). A field TEM instrument records a continuous waveform and the
40 gates are integrated windows of it, so denoising belongs on the waveform. This
is itself a useful finding about the manuscript's reporting granularity (see
Section 6, Finding F4).

## 4. How to run

```bash
# requires: numpy, pywavelets, matplotlib  (pip install numpy pywavelets matplotlib)
python3 src/01_make_synthetic_data.py
python3 src/02_denoise_wavelet.py n24_sig
python3 src/03_evaluate_metrics.py n24_sig
python3 src/04_audit_manuscript_table2.py
python3 src/05_make_figures.py
```

Reproducibility: RNG seed fixed at 42 in `01_make_synthetic_data.py`.

## 5. Audit of manuscript Table 2 (script 04)

The script takes the manuscript's printed numbers as given and checks internal
arithmetic only. Full output in `output/audit_report_manuscript_table2.txt`:

| Check | Manuscript | Independent recomputation | Consistent? |
|-------|-----------|---------------------------|-------------|
| A. All-window RMSE (noisy), from per-window values weighted by gate count | 0.142 | **0.180** | **No** |
| A. All-window RMSE (denoised) | 0.015 | **0.0235** | **No** |
| B. All-window SNR gain reported | +16.3 dB | +19.5 dB implied by the RMSE ratio | **Δ −3.2 dB** |
| B. early / middle / late SNR gain | +12.3 / +14.2 / +17.3 dB | +17.5 / +17.8 / +21.4 dB | Δ −3.6 to −5.2 dB |
| C. Noise level implied by reported noisy SNR 12.4 dB | "5% Gaussian" | **24 %** (amplitude, energy definition) | **No** |

Under the standard definitions of Section 3, checks A and B are mathematical
identities; a consistent table cannot fail them. The discrepancies can be
explained if (and only if) the manuscript uses non-standard metric definitions —
which must then be printed explicitly, as Review Comment #1 requires.

## 6. Additional findings from the reference run

- **F1 (statistical sensitivity).** The decay curve spans 7 orders of magnitude;
  91 % of signal energy sits in the first three gates. Energy-weighted SNR over a
  40-gate window is therefore highly realisation-dependent (Monte-Carlo, 2000
  draws: 24 % signal-scaled noise gives E[SNR]=13.9 dB, std 3.8 dB), and log-domain
  averaging shifts the expectation up by ~1.5 dB relative to the naive
  20·log10(1/η) formula. Reported SNR values are only comparable across papers
  when the definition *and* the realisation ensemble are stated.
- **F2 (gain magnitude).** On the demonstration case the reference pipeline
  improves all-window SNR from 17.9 to 19.3 dB (+1.4 dB) and MRE from 41 % to 15 %.
  A +16 dB-class gain, if real, requires the manuscript's exact noise setting,
  signal form and threshold variant — none of which are currently checkable.
- **F3 (late-gate recovery).** RMSE at late gates improves ~10x in the manuscript
  table; in the reference run late-gate *relative* error remains large because the
  clean signal itself is O(1e-7) µV/A. Denoising cannot recover information below
  the effective noise floor of the acquisition.
- **F4 (granularity).** "5-level DWT on 40 gates" is not meaningful as printed;
  the manuscript should state whether denoising was applied to the raw waveform or
  to gated data, and at what length.

## 7. What the authors should provide for full reproducibility

1. Raw (or synthetic-but-seeded) waveform data used for Table 2, with the noise
   realisation(s).
2. Exact metric definitions (equations 9-11) and the noise reference for the
   "5 %" statement.
3. The explicit functional form of the "improved nonlinear soft threshold".
4. 3-D forward-model settings: grid size, boundary conditions, transmitter
   waveform, resistivity mapping.
5. A public repository URL / DOI for the processing scripts (pledged in the
   response letter but not printed in the manuscript).

## 8. Limitations of this pack

- Synthetic demonstration data only; not the authors' dataset.
- No reconstruction of the manuscript's forward model or inversion (parameters
  not disclosed).
- The "improved" shrinkage is a literature-standard variant, not the authors'
  undisclosed form.
- Single noise realisation in the shipped CSVs (seeded); use the Monte-Carlo
  note in F1 for distributional statements.
