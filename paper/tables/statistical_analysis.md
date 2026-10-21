# Précis Benchmark: Paired Statistical Analysis Report

**Evaluation Corpus**: Natural Questions MRQA Benchmark (200 deterministic paired samples)  
**Methodology**: Paired comparisons with Exact McNemar tests, Wilcoxon signed-rank tests, 10,000 bootstrap resamples (seed 42), and Holm-Bonferroni family-wise error control.

---

## 1. Dataset and Pairing Validation

A strict audit of the benchmark evaluation records was conducted across all three benchmark result artifacts:
- **Original Benchmark**: `results/nq_benchmark/per_question_results.jsonl`
- **Enhanced Baseline**: `results/nq_benchmark_svoa_enhanced/per_question_results.jsonl`
- **Enhanced v2**: `results/nq_benchmark_svoa_enhanced_v2/per_question_results.jsonl`

### Validation Audit Results
- **Record Count**: Exactly 200 `precis_full` records in each of the three benchmark runs, plus exactly 200 `naive_rag` records in the v2 benchmark run.
- **Sample ID Integrity**: 200 unique 32-character hexadecimal MD5 sample IDs per condition. Zero duplicates detected.
- **Pairing Alignment**: Sample IDs, question text strings, and gold answer reference strings match identically across all runs with zero mismatches or missing pairs.
- **Ordering**: The sequence of samples is identical across all files ($N=200$).
- **Data Integrity Status**: **VERIFIED COMPLETE AND UNALTERED**. No records were dropped, imputed, or modified.

---

## 2. Statistical Methodology

### Paired Hypotheses and Effect Direction
For each paired comparison ($A \\rightarrow B$), differences are computed at the individual question level:
$$d_i = B_i - A_i \\quad \\text{for } i = 1, \\dots, 200$$

### Hypothesis Testing Framework
1. **Binary Quality (Exact Match)**:
   - Evaluated using a $2 \\times 2$ contingency table of paired outcomes.
   - Evaluated using a two-sided **exact binomial McNemar test** on discordant pairs ($b = n_{10}$, $c = n_{01}$):
     $$p = \\text{BinomialTest}(\\min(b, c), n=b+c, p=0.5)$$
   - When discordant counts are zero, $p=1.0000$.
   - Odds ratios ($c / b$) report the relative odds of Condition B answering correctly given discordance.

2. **Continuous Metrics (ROUGE-L, BERTScore, MiniLM Cosine, Resource Footprint)**:
   - Evaluated using the two-sided **Wilcoxon signed-rank test** with zero differences excluded (Wilcox method).
   - Effective sample size $n_{\\text{eff}}$ reflects strictly non-zero paired differences.
   - Test statistic reported is $W = \\min(W^+, W^-)$.
   - Effect size reported via the matched-pairs **rank-biserial correlation** ($r_{\\text{rb}}$):
     $$r_{\\text{rb}} = \\frac{W^+ - W^-}{W^+ + W^-}$$
     where $r_{\\text{rb}} \\in [-1, 1]$.

3. **Bootstrap Confidence Intervals**:
   - 95% two-sided percentile confidence intervals for the mean paired difference $\\bar{d}$ were constructed using $B = 10,000$ bootstrap resamples with a fixed seed of 42.

4. **Multiple Comparison Control**:
   - The primary QA quality metrics (**Exact Match**, **ROUGE-L**, **BERTScore**) form the core family of confirmatory hypotheses.
   - P-values are adjusted using the **Holm-Bonferroni step-down procedure** ($m=3$ within each comparison family, and globally $m=9$ across all primary quality comparisons).
   - Secondary engineering/resource metrics are reported transparently with unadjusted p-values and clearly demarcated as exploratory/engineering measures.

---

## 3. Comparison A: Original Précis vs Enhanced Baseline

**Hypothesis**: Does the broader SVOA enhancement (extended syntax patterns, expanded extraction) improve QA performance over the original Précis pipeline?

### Quality Results
- **Exact Match**: Improved from **0.1400** (14.0%) to **0.1800** (18.0%).
  - Absolute change: **+0.0400** (+4.00 percentage points).
  - Relative change: **+28.57%**.
  - McNemar exact $p = 0.007813$ (Significant after Holm adjustment: $p_{\\text{Holm}} = 0.007813$).
  - 95% Bootstrap CI: `[+0.0150, +0.0700]` (strictly excludes zero).
  - Discordant pairs: 8 questions improved under Enhanced, 0 questions degraded.
- **ROUGE-L**: Improved from **0.3444** to **0.4105**.
  - Absolute change: **+0.0661** (Relative: **+19.19%**).
  - Wilcoxon signed-rank: $W = 832.5$, $p = 0.001095$ ($p_{\\text{Holm}} = 0.003285$).
  - 95% Bootstrap CI: `[+0.0353, +0.1001]` (strictly excludes zero).
  - Rank-biserial correlation: $r_{\\text{rb}} = +0.4310$ (moderate-to-strong positive effect).
- **BERTScore (DeBERTa)**: Improved from **0.5747** to **0.6119**.
  - Absolute change: **+0.0372** (Relative: **+6.48%**).
  - Wilcoxon signed-rank: $W = 1805.5$, $p = 0.002716$ ($p_{\\text{Holm}} = 0.005432$).
  - 95% Bootstrap CI: `[+0.0175, +0.0583]`.
  - Rank-biserial correlation: $r_{\\text{rb}} = +0.3386$.
- **MiniLM Cosine**: Improved from **0.4729** to **0.5290**.
  - Absolute change: **+0.0560** (Relative: **+11.85%**).
  - Wilcoxon signed-rank: $W = 1674.0$, $p = 0.000616$.
  - 95% Bootstrap CI: `[+0.0266, +0.0876]`.

### Engineering Trade-offs
- **Context Words**: Increased from 163.6 to 249.6 words (+86.0 words, +52.58%, $p = 1.64 \\times 10^{-23}$).
- **Facts Packed**: Increased from 7.425 to 10.280 facts (+2.855 facts, +38.45%, $p = 3.21 \\times 10^{-22}$).
- **Latency**: Increased from 473.4 ms to 532.0 ms (+58.6 ms, +12.37%, $p = 0.0199$).

**Conclusion**: The broader SVOA enhancement produced a **statistically significant and robust improvement in QA quality** across all metrics. The gain was accompanied by an intentional and statistically significant increase in context size (+86 words) and latency (+58.6 ms).

---

## 4. Comparison B: Enhanced Baseline vs Enhanced v2

**Hypothesis**: Does the targeted passive-coordination extraction intervention (handling passive verb phrases and coordinated predicate clauses) yield measurable QA improvements over the Enhanced baseline?

### Quality Results
- **Exact Match**: **0.1800** $\\rightarrow$ **0.1800** (+0.0000, +0.00 pp).
  - Discordant pairs: 0 (36 both correct, 164 both incorrect).
  - McNemar exact $p = 1.0000$ ($p_{\\text{Holm}} = 1.0000$).
  - 95% Bootstrap CI: `[0.0000, 0.0000]`.
- **ROUGE-L**: **0.4105** $\\rightarrow$ **0.4142** (+0.0037, +0.90%).
  - 95% Bootstrap CI: `[-0.0052, +0.0118]` (**CROSSES ZERO**).
  - Wilcoxon signed-rank: $W = 101.0$, $n_{\\text{eff}} = 22$, $p = 0.406565$ ($p_{\\text{Holm}} = 0.813129$).
  - Rank-biserial correlation: $r_{\\text{rb}} = +0.2016$.
  - Win / Tie / Loss: **10 wins, 178 ties, 12 losses** (Net win margin: **-2**).
- **BERTScore (DeBERTa)**: **0.6119** $\\rightarrow$ **0.6161** (+0.0043, +0.70%).
  - 95% Bootstrap CI: `[-0.0019, +0.0105]` (**CROSSES ZERO**).
  - Wilcoxon signed-rank: $W = 124.0$, $n_{\\text{eff}} = 26$, $p = 0.190176$ ($p_{\\text{Holm}} = 0.570529$).
  - Rank-biserial correlation: $r_{\\text{rb}} = +0.2934$.
  - Win / Tie / Loss: **12 wins, 174 ties, 14 losses** (Net win margin: **-2**).
- **MiniLM Cosine**: **0.5290** $\\rightarrow$ **0.5361** (+0.0072, +1.35%).
  - 95% Bootstrap CI: `[-0.0034, +0.0181]` (**CROSSES ZERO**).
  - Wilcoxon signed-rank: $W = 154.0$, $n_{\\text{eff}} = 26$, $p = 0.584436$.
  - Win / Tie / Loss: **12 wins, 174 ties, 14 losses** (Net win margin: **-2**).

### Engineering Trade-offs
- **Context Words**: Increased marginally from 249.64 to 250.18 (+0.54 words, +0.21%, $p = 2.32 \\times 10^{-5}$). Exactly 23 questions gained a few words of passive coordination text.
- **Facts Packed**: Identical at 10.2800 vs 10.2800 (difference = 0.0000 across all 200 samples).
- **Latency**: Decreased non-significantly from 532.0 ms to 525.3 ms (-6.68 ms, -1.26%, $p = 0.1657$, 95% CI: `[-22.36 ms, +7.44 ms]` crosses zero).

**Conclusion**: The passive-coordination intervention in v2 is **NOT statistically significant**. The tiny mean increases in ROUGE-L (+0.0037) and BERTScore (+0.0043) are consistent with random fluctuation: all 95% confidence intervals cross zero, $p$-values are well above 0.05, and on question-level outcomes v2 actually registered more losses than wins (net margin of -2).

---

## 5. Comparison C: Enhanced v2 vs Naive RAG

**Hypothesis**: How does the optimized Précis v2 pipeline compare against the standard 512-token Naive RAG chunking baseline?

### Quality Results
- **Exact Match**: Naive RAG (**0.2850**) significantly outperforms Précis v2 (**0.1800**).
  - Absolute paired difference (Naive - v2): **+0.1050** (+10.50 percentage points).
  - Relative difference: Naive RAG is **+58.33%** higher in EM than v2 (v2 achieves 63.16% of Naive RAG's EM).
  - McNemar exact $p = 0.001065$ ($p_{\\text{Holm}} = 0.001065$).
  - Discordant pairs: 30 questions correct only under Naive RAG, 9 questions correct only under v2 (Odds Ratio = 3.3333).
  - 95% Bootstrap CI: `[+0.0450, +0.1650]` (strictly excludes zero).
- **ROUGE-L**: Naive RAG (**0.5328**) significantly outperforms Précis v2 (**0.4142**).
  - Absolute paired difference: **+0.1186** (Relative: **+28.63%**).
  - Wilcoxon signed-rank: $W = 2485.0$, $n_{\\text{eff}} = 135$, $p = 3.76 \\times 10^{-6}$ ($p_{\\text{Holm}} = 7.52 \\times 10^{-6}$).
  - 95% Bootstrap CI: `[+0.0665, +0.1713]`.
  - Rank-biserial correlation: $r_{\\text{rb}} = +0.4586$.
  - Win / Tie / Loss: **90 wins for Naive RAG, 65 ties, 45 wins for v2** (Net margin: +45).
- **BERTScore (DeBERTa)**: Naive RAG (**0.6909**) significantly outperforms Précis v2 (**0.6161**).
  - Absolute paired difference: **+0.0748** (Relative: **+12.14%**).
  - Wilcoxon signed-rank: $W = 2902.0$, $n_{\\text{eff}} = 150$, $p = 2.22 \\times 10^{-7}$ ($p_{\\text{Holm}} = 6.67 \\times 10^{-7}$).
  - 95% Bootstrap CI: `[+0.0455, +0.1042]`.
  - Rank-biserial correlation: $r_{\\text{rb}} = +0.4875$.
  - Win / Tie / Loss: **105 wins for Naive RAG, 50 ties, 45 wins for v2** (Net margin: +60).
- **MiniLM Cosine**: Naive RAG (**0.6325**) significantly outperforms Précis v2 (**0.5361**).
  - Absolute paired difference: **+0.0964** (Relative: **+17.98%**).
  - Wilcoxon signed-rank: $W = 3340.0$, $n_{\\text{eff}} = 150$, $p = 1.31 \\times 10^{-5}$.
  - 95% Bootstrap CI: `[+0.0545, +0.1395]`.

### Resource and Latency Analysis
- **Context Words**: Précis v2 supplies **250.2** words on average vs Naive RAG's **159.3** words.
  - Paired difference: -90.9 words for Naive RAG ($p = 2.41 \\times 10^{-26}$).
  - On this 200-sample NQ subset, Naive RAG's top-1 chunk averaged only 159 words, whereas Précis's enhanced fact packing aggregated ~10 facts across candidate passages totaling 250 words.
- **Generated Tokens**: Précis v2 generates **22.8** tokens vs Naive RAG's **16.9** tokens (+5.9 tokens, $p = 2.92 \\times 10^{-5}$). Précis outputs slightly longer, more descriptive phrases due to the structured prompt template.
- **Latency**: Précis v2 averages **525.3 ms** vs Naive RAG's **508.9 ms**.
  - Paired difference: 16.4 ms faster for Naive RAG, but this difference is **not statistically significant** ($p = 0.0760$, 95% CI: `[-83.8 ms, +43.9 ms]` crosses zero).

**Conclusion**: Naive RAG **statistically significantly outperforms Précis Enhanced v2 across all QA metrics**. Furthermore, in Enhanced mode, Précis is not providing context token compression relative to top-1 chunk retrieval on this slice, and shows comparable latency.

---

## 6. Exact Match Contingency Analysis (McNemar Tests)

### Comparison A: Original Précis vs Enhanced Baseline
| | Enhanced Correct | Enhanced Incorrect | Total |
|---|---|---|---|
| **Original Correct** | 28 | 0 | 28 |
| **Original Incorrect** | 8 | 164 | 172 |
| **Total** | 36 | 164 | 200 |

- **Both Correct**: 28
- **Original-Only Correct ($b$)**: 0
- **Enhanced-Only Correct ($c$)**: 8
- **Both Incorrect**: 164
- **Discordant Pairs ($b+c$)**: 8
- **Exact Binomial $p$-value**: $p = 0.0078125$ ($2 \\times 0.5^8$)
- **Odds Ratio**: $\\infty$ (Haldane-Anscombe corrected: $17.00$)
- **Interpretation**: Enhanced baseline strictly dominates Original Précis on EM. It corrected 8 previously missed questions while preserving 100% of the original correct answers.

---

### Comparison B: Enhanced Baseline vs Enhanced v2
| | v2 Correct | v2 Incorrect | Total |
|---|---|---|---|
| **Enhanced Correct** | 36 | 0 | 36 |
| **Enhanced Incorrect** | 0 | 164 | 164 |
| **Total** | 36 | 164 | 200 |

- **Both Correct**: 36
- **Enhanced-Only Correct ($b$)**: 0
- **v2-Only Correct ($c$)**: 0
- **Both Incorrect**: 164
- **Discordant Pairs ($b+c$)**: 0
- **Exact Binomial $p$-value**: $p = 1.0000$
- **Odds Ratio**: Undefined (no discordant observations)
- **Interpretation**: Exact Match performance is completely unchanged between Enhanced baseline and Enhanced v2. The passive-coordination intervention converted zero errors to correct answers and introduced zero regressions.

---

### Comparison C: Enhanced v2 vs Naive RAG
| | Naive RAG Correct | Naive RAG Incorrect | Total |
|---|---|---|---|
| **Précis v2 Correct** | 27 | 9 | 36 |
| **Précis v2 Incorrect** | 30 | 134 | 164 |
| **Total** | 57 | 143 | 200 |

- **Both Correct**: 27
- **v2-Only Correct ($b$)**: 9
- **Naive-Only Correct ($c$)**: 30
- **Both Incorrect**: 134
- **Discordant Pairs ($b+c$)**: 39
- **Exact Binomial $p$-value**: $p = 0.001065$
- **Odds Ratio**: $30 / 9 = 3.3333$
- **Interpretation**: On discordant questions, Naive RAG is 3.33 times more likely to answer correctly than Précis v2. Naive RAG's superior EM performance is statistically decisive ($p = 0.0011$).

---

## 7. Multiple Comparison Correction Summary

Applying the Holm-Bonferroni step-down procedure across the primary confirmatory quality metrics:

| Comparison | Hypothesis Test | Metric | Unadjusted $p$ | Rank ($k$) | Multiplier ($m - k + 1$) | Holm $p$ (Within Family, $m=3$) | Holm $p$ (Global Family, $m=9$) | Significant at $\\alpha = 0.05$? |
|---|---|---|---|---|---|---|---|---|
| **Orig vs Enh** | McNemar | Exact Match | 0.007812 | 3 | 1 | 0.007812 | 0.031250 | **Yes** |
| | Wilcoxon | ROUGE-L | 0.001095 | 1 | 3 | 0.003285 | 0.007455 | **Yes** |
| | Wilcoxon | BERTScore | 0.002716 | 2 | 2 | 0.005432 | 0.013580 | **Yes** |
| **Enh vs v2** | McNemar | Exact Match | 1.000000 | 3 | 1 | 1.000000 | 1.000000 | No |
| | Wilcoxon | ROUGE-L | 0.406565 | 2 | 2 | 0.813129 | 0.813129 | No |
| | Wilcoxon | BERTScore | 0.190176 | 1 | 3 | 0.570529 | 0.570529 | No |
| **v2 vs Naive** | McNemar | Exact Match | 0.001065 | 3 | 1 | 0.001065 | 0.007455 | **Yes** |
| | Wilcoxon | ROUGE-L | 3.76e-06 | 2 | 2 | 7.52e-06 | 3.01e-05 | **Yes** |
| | Wilcoxon | BERTScore | 2.22e-07 | 1 | 3 | 6.67e-07 | 2.00e-06 | **Yes** |

Whether controlled within each comparison family ($m=3$) or across the global set of all 9 primary tests ($m=9$), the inferential conclusions remain robust:
- Original $\\rightarrow$ Enhanced is unequivocally statistically significant ($p < 0.05$).
- Enhanced $\\rightarrow$ v2 fails to achieve statistical significance on every primary metric ($p \\ge 0.57$).
- v2 $\\rightarrow$ Naive is overwhelmingly statistically significant ($p < 0.01$).

---

## 8. Resource and Latency Analysis

| Comparison | Metric | Mean Paired Difference | Median Difference | 95% Bootstrap CI | Non-zero $n$ | Wilcoxon $p$-value | Practical Takeaway |
|---|---|---|---|---|---|---|---|
| **Orig vs Enh** | Context Words | +86.03 words | +13.00 words | [+52.64, +124.34] | 179 | 1.64e-23 | Intentional footprint increase to pack more SVOA facts |
| | Latency | +58.56 ms | +4.00 ms | [+10.15, +113.74] | 198 | 0.0199 | Modest +12.4% latency increase from extra extraction |
| | Facts Packed | +2.86 facts | +1.00 facts | [+2.12, +3.65] | 122 | 3.21e-22 | Packing density rose from 7.4 to 10.3 facts |
| **Enh vs v2** | Context Words | +0.54 words | 0.00 words | [+0.31, +0.79] | 23 | 2.32e-05 | Statistically detectable but practically negligible (+0.5 words) |
| | Latency | -6.68 ms | +1.00 ms | [-22.36, +7.44] | 194 | 0.1657 | Not statistically significant (noise) |
| | Facts Packed | 0.00 facts | 0.00 facts | [0.00, 0.00] | 0 | N/A | Exactly zero change in packed fact counts |
| **v2 vs Naive** | Context Words | -90.88 words | -57.00 words | [-109.88, -71.62] | 200 | 2.41e-26 | Naive RAG top-1 chunks are actually shorter than v2 context |
| | Latency | -16.37 ms | +55.50 ms | [-83.84, +43.89] | 200 | 0.0760 | No statistically significant difference in runtime latency |
| | Generated Tokens| -5.88 tokens | 0.00 tokens | [-8.77, -3.41] | 145 | 2.92e-05 | Naive RAG outputs more concise direct answers |

---

## 9. Question-Level Win / Tie / Loss Breakdown

| Comparison | Metric | B Wins | Ties | B Losses | Net Margin (B - A) | Notes |
|---|---|---|---|---|---|---|
| **Original vs Enhanced** | Exact Match | 8 | 192 | 0 | **+8** | 8 newly correct, 0 regressions |
| | ROUGE-L | 47 | 124 | 29 | **+18** | 47 questions improved, 29 deteriorated |
| | BERTScore | 67 | 96 | 37 | **+30** | 67 questions improved, 37 deteriorated |
| | MiniLM Cosine | 68 | 96 | 36 | **+32** | 68 questions improved, 36 deteriorated |
| **Enhanced vs v2** | Exact Match | 0 | 200 | 0 | **0** | Complete invariance across all 200 questions |
| | ROUGE-L | 10 | 178 | 12 | **-2** | Net negative margin despite slightly higher mean |
| | BERTScore | 12 | 174 | 14 | **-2** | Net negative margin despite slightly higher mean |
| | MiniLM Cosine | 12 | 174 | 14 | **-2** | Net negative margin despite slightly higher mean |
| **v2 vs Naive RAG** | Exact Match | 30 | 161 | 9 | **+21** (Naive wins) | Naive wins 30 discordant questions vs 9 for v2 |
| | ROUGE-L | 90 | 65 | 45 | **+45** (Naive wins) | Naive wins 2x as many questions as v2 |
| | BERTScore | 105 | 50 | 45 | **+60** (Naive wins) | Naive wins over 50% of the entire sample |
| | MiniLM Cosine | 99 | 50 | 51 | **+48** (Naive wins) | Naive wins ~2x as many questions as v2 |

---

## 10. Research Interpretation

### Interpretation of Comparison A (Original $\\rightarrow$ Enhanced Baseline)
The broader SVOA expansion (incorporating prepositional objects, verbal complements, and richer noun chunk attachments) was **empirically successful**. It produced statistically significant gains across all QA evaluation metrics (EM $+4.00$ pp, $p = 0.0078$; ROUGE-L $+0.0661$, $p = 0.0011$; BERTScore $+0.0372$, $p = 0.0027$). Crucially, the 8 newly correct questions under Exact Match occurred without any regressions on previously correct items. This demonstrates that the original pipeline was suffering from severe information truncation that broader SVOA extraction successfully alleviated.

### Interpretation of Comparison B (Enhanced Baseline $\\rightarrow$ Enhanced v2)
The targeted passive-coordination intervention in v2 **did NOT yield a statistically significant effect**. 
- The apparent increase in mean ROUGE-L ($0.4105 \\rightarrow 0.4142$, $+0.0037$) and BERTScore ($0.6119 \\rightarrow 0.6161$, $+0.0043$) must not be interpreted as genuine progress.
- All 95% bootstrap confidence intervals for quality metrics cross zero.
- The Wilcoxon tests fail to reject the null hypothesis ($p = 0.4066$ for ROUGE-L, $p = 0.1902$ for BERTScore).
- At the question level, v2 produced **more losses than wins** (10 wins vs 12 losses on ROUGE-L, 12 wins vs 14 losses on BERTScore, yielding a net margin of $-2$).
- Exact Match was perfectly identical across all 200 questions.
- While the intervention added an average of $+0.54$ context words on 23 questions ($p = 2.32 \\times 10^{-5}$), this grammatical refinement did not translate into downstream QA utility.

### Interpretation of Comparison C (Enhanced v2 vs Naive RAG)
The benchmark **does NOT demonstrate superiority over Naive RAG**:
- Naive RAG remains **statistically significantly superior** to Précis v2 across all quality measures (EM $0.2850$ vs $0.1800$, $p = 0.0011$; ROUGE-L $0.5328$ vs $0.4142$, $p = 3.76 \\times 10^{-6}$; BERTScore $0.6909$ vs $0.6161$, $p = 2.22 \\times 10^{-7}$).
- In terms of context footprint, Naive RAG's top-1 512-token chunks averaged $159.3$ words, whereas Précis's multi-fact packing averaged $250.2$ words. Thus, on this dataset slice, Précis is actually providing **more words of context** than single-chunk Naive RAG while obtaining **lower accuracy**.
- In terms of runtime latency, the two systems are statistically indistinguishable ($508.9$ ms vs $525.3$ ms, $p = 0.0760$).

---

## 11. Limitations

1. **Dataset Scope**: The current analysis is restricted to the 200 deterministic Natural Questions MRQA sample set. While paired testing provides high statistical power for within-sample differences, generalization across out-of-domain datasets (e.g., HotpotQA multi-hop, biomedical QA) cannot be inferred without additional benchmarking.
2. **Chunk Size Confound**: Naive RAG utilizes single retrieved passages (top-1 chunk) which often contain complete natural prose sentences, whereas Précis aggregates syntactically decoupled SVOA fact tuples across candidate passages. On short single-fact questions, natural paragraph coherence in top-1 passages confers a strong advantage to standard generation.
3. **Extraction vs Generator Mismatch**: Précis extracts isolated subject-verb-object-adverbial tuples. Although SDH scoring and diversity packing select high-salience facts, small generative models (like Qwen2.5-0.5B-Instruct) appear to struggle more with synthesizing answers from decoupled structured tuples than from standard narrative context.
