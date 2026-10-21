# Statistical Comparison Table (Précis NQ Benchmark)

Paired evaluation across 200 deterministic Natural Questions samples. Comp A: Original Précis vs Enhanced Baseline; Comp B: Enhanced Baseline vs Enhanced v2; Comp C: Enhanced v2 vs Naive RAG.
For quality metrics, positive $\Delta$ indicates an increase from Condition A to Condition B. $p$-values for continuous metrics derive from two-sided Wilcoxon signed-rank tests; Exact Match $p$-values derive from two-sided exact McNemar tests. $p_{\text{Holm}}$ reflects step-down Holm-Bonferroni correction within primary QA metrics per comparison. 95% bootstrap confidence intervals for the mean difference are computed over 10,000 resamples (seed 42).

### Table 1: Primary Quality Metrics

| Comparison | Metric | Cond A Mean | Cond B Mean | Mean Paired $\Delta$ | 95% Bootstrap CI | Rel $\Delta$ (%) | Non-zero $n$ | $W$ Stat | $r_{\text{rb}}$ | Win/Tie/Loss | $p_{\text{unadj}}$ | $p_{\text{Holm}}$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Original vs Enhanced** | Exact Match | 0.1400 | 0.1800 | +0.0400 (+4.00 pp) | [+0.0150, +0.0700] | +28.57% | 8 | 0.0 | 1.0000 | 8 / 192 / 0 | 0.0078 | 0.0078* |
| | ROUGE-L | 0.3444 | 0.4105 | +0.0661 | [+0.0353, +0.1001] | +19.19% | 76 | 832.5 | 0.4310 | 47 / 124 / 29 | 0.0011 | 0.0033* |
| | BERTScore | 0.5747 | 0.6119 | +0.0372 | [+0.0175, +0.0583] | +6.48% | 104 | 1805.5 | 0.3386 | 67 / 96 / 37 | 0.0027 | 0.0054* |
| | MiniLM Cosine | 0.4729 | 0.5290 | +0.0560 | [+0.0266, +0.0876] | +11.85% | 104 | 1674.0 | 0.3868 | 68 / 96 / 36 | 0.0006 | — |
| **Enhanced vs v2** | Exact Match | 0.1800 | 0.1800 | +0.0000 (+0.00 pp) | [+0.0000, +0.0000] | 0.00% | 0 | N/A | N/A | 0 / 200 / 0 | 1.0000 | 1.0000 |
| | ROUGE-L | 0.4105 | 0.4142 | +0.0037 | [-0.0052, +0.0118] | +0.90% | 22 | 101.0 | 0.2016 | 10 / 178 / 12 | 0.4066 | 0.8131 |
| | BERTScore | 0.6119 | 0.6161 | +0.0043 | [-0.0019, +0.0105] | +0.70% | 26 | 124.0 | 0.2934 | 12 / 174 / 14 | 0.1902 | 0.5705 |
| | MiniLM Cosine | 0.5290 | 0.5361 | +0.0072 | [-0.0034, +0.0181] | +1.35% | 26 | 154.0 | 0.1225 | 12 / 174 / 14 | 0.5844 | — |
| **v2 vs v3** | Exact Match | 0.1800 | 0.1900 | +0.0100 (+1.00 pp) | [-0.0150, +0.0350] | +5.56% | 6 | 7.0 | 0.3333 | 5 / 194 / 1 | 0.6875 | 1.0000 |
| | ROUGE-L | 0.4142 | 0.4155 | +0.0013 | [-0.0055, +0.0080] | +0.31% | 29 | 172.0 | 0.2109 | 17 / 171 / 12 | 0.2741 | 0.8223 |
| | BERTScore | 0.6161 | 0.6195 | +0.0034 | [-0.0042, +0.0110] | +0.55% | 38 | 328.0 | 0.1159 | 21 / 162 / 17 | 0.4998 | 0.9996 |
| | MiniLM Cosine | 0.5361 | 0.5393 | +0.0032 | [-0.0001, +0.0065] | +0.60% | 38 | 249.0 | 0.3288 | 24 / 162 / 14 | 0.0583 | — |
| **v3 vs Naive RAG** | Exact Match | 0.1900 | 0.2850 | +0.0950 (+9.50 pp) | [+0.0350, +0.1550] | +50.00% | 33 | 114.0 | 0.5936 | 28 / 167 / 5 | 9.41e-04 | 9.41e-04* |
| | ROUGE-L | 0.4155 | 0.5314 | +0.1159 | [+0.0638, +0.1680] | +27.89% | 122 | 2082.0 | 0.4411 | 82 / 78 / 40 | 7.05e-07 | 1.41e-06* |
| | BERTScore | 0.6195 | 0.6889 | +0.0694 | [+0.0401, +0.0987] | +11.20% | 143 | 2680.0 | 0.4795 | 99 / 57 / 44 | 9.58e-08 | 2.87e-07* |
| | MiniLM Cosine | 0.5393 | 0.6274 | +0.0881 | [+0.0462, +0.1300] | +16.34% | 143 | 3105.0 | 0.3969 | 94 / 57 / 49 | 9.71e-06 | — |

*Statistically significant at $\alpha = 0.05$ after Holm-Bonferroni correction. Win/Tie/Loss reflects the perspective of Condition B relative to Condition A. Note that v2 vs v3 improvements are NOT statistically significant ($p > 0.05$).

### Table 2: Resource and Latency Metrics

| Comparison | Metric | Cond A Mean | Cond B Mean | Mean Paired $\Delta$ | 95% Bootstrap CI | Rel $\Delta$ (%) | Non-zero $n$ | $p_{\text{Wilcoxon}}$ |
|---|---|---|---|---|---|---|---|---|
| **Original vs Enhanced** | Context Words | 163.6 | 249.6 | +86.0 | [+52.6, +124.3] | +52.58% | 179 | 1.64e-23* |
| | Context Tokens | 204.7 | 313.6 | +108.9 | [+66.1, +158.0] | +53.21% | 179 | 9.17e-24* |
| | Generated Tokens | 20.8 | 23.2 | +2.3 | [+0.2, +4.7] | +11.06% | 98 | 0.1108 |
| | Latency (ms) | 473.4 ms | 532.0 ms | +58.6 ms | [+10.1 ms, +113.7 ms] | +12.37% | 198 | 0.0199* |
| | Facts Packed | 7.4 | 10.3 | +2.9 | [+2.1, +3.6] | +38.45% | 122 | 3.21e-22* |
| **Enhanced vs v2** | Context Words | 249.6 | 250.2 | +0.5 | [+0.3, +0.8] | +0.21% | 23 | 2.32e-05* |
| | Context Tokens | 313.6 | 314.3 | +0.7 | [+0.4, +1.0] | +0.22% | 23 | 2.27e-05* |
| | Generated Tokens | 23.2 | 22.8 | -0.4 | [-1.1, +0.2] | -1.73% | 23 | 0.9145 |
| | Latency (ms) | 532.0 ms | 525.3 ms | -6.7 ms | [-22.4 ms, +7.4 ms] | -1.26% | 194 | 0.1657 |
| | Facts Packed | 10.3 | 10.3 | 0.0 | [0.0, 0.0] | 0.00% | 0 | N/A |
| **v2 vs v3** | Context Words | 250.2 | 257.4 | +7.2 | [+3.1, +11.5] | +2.88% | 45 | 1.84e-04* |
| | Context Tokens | 314.3 | 323.5 | +9.2 | [+4.0, +14.6] | +2.93% | 45 | 1.76e-04* |
| | Generated Tokens | 22.8 | 23.3 | +0.5 | [-0.3, +1.4] | +2.19% | 34 | 0.3120 |
| | Latency (ms) | 525.3 ms | 538.0 ms | +12.7 ms | [-5.2 ms, +31.4 ms] | +2.42% | 199 | 0.1852 |
| | Facts Packed | 10.3 | 10.5 | +0.2 | [+0.1, +0.4] | +1.94% | 32 | 1.15e-05* |
| **v3 vs Naive RAG** | Context Words | 257.4 | 159.3 | -98.1 | [-118.2, -78.4] | -38.11% | 200 | 1.12e-26* |
| | Context Tokens | 323.5 | 206.6 | -116.9 | [-141.2, -92.5] | -36.14% | 200 | 4.54e-26* |
| | Generated Tokens | 23.3 | 17.1 | -6.2 | [-9.1, -3.7] | -26.61% | 148 | 1.85e-05* |
| | Latency (ms) | 538.0 ms | 525.2 ms | -12.8 ms | [-81.4 ms, +48.2 ms] | -2.38% | 200 | 0.1415 |
| | Facts Packed | 10.5 | 0.0 | -10.5 | [-12.1, -9.1] | -100.00% | 199 | 1.90e-34* |

*Statistically significant at $\alpha = 0.05$.
