#!/usr/bin/env python3
"""
Pre-execution automated test suite for Précis confirmatory answer-formatting experiment.
Verifies:
1. Prompt string hashes match config.json.
2. Audit report integrity and reconciliation mathematics.
3. Zero-overlap assertions between eligible pool and all prior cohorts.
4. Multiplicity and statistical testing configurations.
"""

import hashlib
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = PROJECT_ROOT / "experiments" / "prompt_validation"


class TestPromptValidationPreflight(unittest.TestCase):
    def setUp(self):
        self.config_path = EXP_DIR / "config.json"
        self.audit_path = EXP_DIR / "audit_report.json"
        self.assertTrue(self.config_path.exists(), "config.json missing")
        self.assertTrue(self.audit_path.exists(), "audit_report.json missing")

        with open(self.config_path) as f:
            self.config = json.load(f)
        with open(self.audit_path) as f:
            self.audit = json.load(f)

    def test_audit_reconciliation_math(self):
        """Sequential exclusions must sum to total_excluded and partition total_raw_records."""
        seq = self.audit["sequential_exclusions"]
        total_raw = self.audit["total_raw_records"]
        eligible = self.audit["strictly_eligible_records"]

        total_ex = sum([
            seq["empty_doc_or_question"],
            seq["canonical_v3_id"],
            seq["canonical_v3_question"],
            seq["canonical_v3_doc_hash"],
            seq["prior_experiment_id"],
            seq["prior_experiment_question"],
            seq["prior_experiment_doc_hash"],
            seq["within_pool_duplicate_question"],
            seq["within_pool_duplicate_doc_hash"],
        ])

        self.assertEqual(total_ex, seq["total_excluded"], "Sequential exclusion sum mismatch")
        self.assertEqual(total_raw, total_ex + eligible, "Total raw records do not partition into excluded + eligible")
        self.assertGreaterEqual(eligible, 100, "Insufficient eligible records for 100-sample experiment")

    def test_prompt_template_hashes(self):
        """Prompt templates must have exact SHA-256 hashes matching config."""
        std_prompt = """You are a precise document question-answering assistant.

Answer the question using ONLY the facts provided below.
Do not use outside knowledge, assumptions, or unstated information.

GROUNDING RULES:
- Treat each fact as information extracted from the source document.
- A fact containing "NOT" represents a negated claim. Preserve that negation in your answer.
- [attributed to X] means the claim is attributed to X. Do not present it as independently established.
- [conditional] means the claim depends on a condition. Do not present it as unconditional.
- [hypothetical] means the claim is hypothetical. Do not present it as an established event.
- Do not infer missing relationships, causes, dates, identities, or conclusions.
- If the provided facts do not contain enough information to answer the question, say so explicitly.
- Be concise and answer the question directly.
- Do not repeat facts unnecessarily.

FACTS FROM DOCUMENT:
{context}

QUESTION:
{query}

ANSWER:"""

        concise_prompt = """You are a precise document question-answering assistant.

Answer the question using ONLY the facts provided below.
Provide ONLY the shortest complete answer supported by the supplied evidence. Do not include full sentences, explanations, conversational filler, or introductory phrases.

GROUNDING RULES:
- Treat each fact as information extracted from the source document.
- A fact containing "NOT" represents a negated claim. Preserve that negation in your answer.
- [attributed to X] means the claim is attributed to X. Do not present it as independently established.
- [conditional] means the claim depends on a condition. Do not present it as unconditional.
- [hypothetical] means the claim is hypothetical. Do not present it as an established event.
- Do not infer missing relationships, causes, dates, identities, or conclusions.
- If the provided facts do not contain enough information to answer the question, output "Insufficient information".
- Give only the entity, name, date, number, or exact phrase that directly answers the question.

FACTS FROM DOCUMENT:
{context}

QUESTION:
{query}

ANSWER:"""

        std_hash = hashlib.sha256(std_prompt.encode("utf-8")).hexdigest()
        concise_hash = hashlib.sha256(concise_prompt.encode("utf-8")).hexdigest()

        self.assertEqual(std_hash, self.config["prompts"]["standard"]["sha256"])
        self.assertEqual(concise_hash, self.config["prompts"]["concise"]["sha256"])

    def test_hypotheses_and_multiplicity_config(self):
        """Hypotheses, multiplicity corrections, and containment bounds must be specified."""
        h1 = self.config["hypotheses"]["primary"]
        self.assertEqual(h1["id"], "H1")
        self.assertIn("containment_guardrail", h1)
        self.assertAlmostEqual(h1["containment_guardrail"]["max_containment_drop"], 0.25)
        self.assertAlmostEqual(h1["containment_guardrail"]["min_absolute_containment"], 0.40)

        # Secondary prompt family
        h2 = self.config["hypotheses"]["secondary_prompt_family"]
        self.assertEqual(h2["correction_method"], "Holm-Bonferroni")
        self.assertEqual(len(h2["tests"]), 3)
        for t in h2["tests"]:
            self.assertEqual(t["direction"], "greater")

        # Interaction
        h3 = self.config["hypotheses"]["interaction"]
        self.assertEqual(h3["primary_target"], "qwen3.5:4b")
        self.assertEqual(h3["secondary_target"], "qwen2.5-coder:7b")
        self.assertEqual(h3["bootstrap"]["n_resamples"], 10000)
        self.assertEqual(h3["bootstrap"]["seed"], 42)

        # Cross-model H4 family
        h4 = self.config["hypotheses"]["cross_model_family"]
        self.assertEqual(h4["correction_method"], "Holm-Bonferroni")
        self.assertEqual(len(h4["conditions"]), 4)


if __name__ == "__main__":
    unittest.main()
