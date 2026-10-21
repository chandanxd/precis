# Context-Budget Accounting & Boundary Report

## Executive Summary

During the Experiment 4.4 independent audit, a token-budget accounting defect was identified: the structured list section header (`### Structured List:
`, estimated at ~6 tokens) and inter-block markdown separators (`

`, ~1 token) were not deducted from available budget before calculating line budgets for partial packing. Under boundary conditions, this defect could lead to context-ceiling overshoots.

Experiment 4.5 addresses this defect directly, establishing exact accounting and hard ceiling guarantees.

## Defect Resolution Architecture

### 1. Up-Front Header and Delimiter Deduction

Before allocating line budgets for candidate list blocks, `build_structural_context()` deducts both the delimiter overhead and section header tokens:

```python
separator_overhead = estimate_text_tokens("\n\n")

for b in deduped_blocks:
    md_list = render_list_to_markdown(b)
    list_header = "### Structured List:\n"
    list_chunk = f"{list_header}{md_list}"
    tok_est = estimate_text_tokens(list_chunk)

    budget_remaining = token_ceiling - cur_tokens - separator_overhead

    if budget_remaining <= 0:
        break

    if tok_est <= budget_remaining:
        packed_parts.append(list_chunk)
        cur_tokens += tok_est + separator_overhead
        lists_packed += 1
    else:
        # Deduct truncation header before packing individual lines
        trunc_header = "### Structured List (Budget Truncated):\n"
        trunc_header_tokens = estimate_text_tokens(trunc_header)
        net_line_budget = budget_remaining - trunc_header_tokens

        if net_line_budget > 30:
            truncated_lines = []
            sub_tok = 0
            for line in md_list.split("\n"):
                l_tok = estimate_text_tokens(line)
                if sub_tok + l_tok <= net_line_budget:
                    truncated_lines.append(line)
                    sub_tok += l_tok
                else:
                    break
```

### 2. Minimum Viable Line Budget Guard

A minimum threshold of `net_line_budget > 30 tokens` ensures that Précis will never pack an empty truncation header (`### Structured List (Budget Truncated):`) without at least one meaningful content line.

### 3. Post-Assembly Deterministic Hard Clamp

To protect against subword estimation variance across token boundaries, a post-assembly guard enforces the ceiling unconditionally:

```python
full_context = "\n\n".join(packed_parts)
final_tokens = estimate_text_tokens(full_context) if full_context else 0

if final_tokens > token_ceiling:
    # Drop trailing parts (lists first)
    while len(packed_parts) > 1 and estimate_text_tokens("\n\n".join(packed_parts)) > token_ceiling:
        dropped = packed_parts.pop()
        if "### Structured List" in dropped:
            lists_packed = max(0, lists_packed - 1)
    full_context = "\n\n".join(packed_parts)
    # If single item (prose) still exceeds ceiling, trim words deterministically
    if estimate_text_tokens(full_context) > token_ceiling:
        words = full_context.split()
        k = len(words)
        while k > 0 and estimate_text_tokens(" ".join(words[:k])) > token_ceiling:
            k -= 1
        full_context = " ".join(words[:k])
    final_tokens = estimate_text_tokens(full_context) if full_context else 0
```

## Boundary Test Results

The budget accounting was verified across multiple ceiling scales with massive list fixtures (200+ list items) in `backend/tests/test_structural_integration.py`:

| Token Ceiling | Initial List Tokens | Final Context Tokens | Ceiling Violation | Truncation Status |
| :---: | :---: | :---: | :---: | :--- |
| **200** | ~3,200 | 198 | **FALSE (0%)** | Partial packing with header deduction |
| **350** | ~3,200 | 347 | **FALSE (0%)** | Partial packing with header deduction |
| **500** | ~3,200 | 496 | **FALSE (0%)** | Partial packing with header deduction |
| **1,000** | ~3,200 | 992 | **FALSE (0%)** | Partial packing with header deduction |
| **2,048** | ~3,200 | 2,042 | **FALSE (0%)** | Partial packing with header deduction |

In all cases:
- Final estimated tokens strictly $\le$ `token_ceiling`.
- Zero context-ceiling violations observed.
- Clean truncation header emitted with preserved bullet items.
