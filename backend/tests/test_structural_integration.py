"""
Unit, integration, and regression test suite for Précis Structural Retention.

Validates:
- Feature flag behavior and safe failure modes (PRECIS_ENABLE_LIST_EXTRACTION).
- Disabled-mode byte-level compatibility with existing table retention.
- Context budget accounting, header/separator deduction, and boundary ceilings.
- Conservative table-list overlap deduplication.
- Evidence-level regression safeguards for 3f5983b2, ef634417, and 8f1f9bd9.
- Robust handling of malformed markup, empty input, and navigation boilerplate.
"""

import os
from pathlib import Path
import pytest

from precis.pipeline.structural import (
    FLAG_NAME,
    StructuralDocumentParser,
    build_structural_context,
    deduplicate_table_list_overlap,
    estimate_text_tokens,
    extract_lists_from_html,
    is_list_extraction_enabled,
    is_nav_or_boilerplate_list,
    parse_feature_flag,
)

# Import historical reference from scripts for disabled-mode compatibility verification
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
import sys
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from eval_experiment_4_2_threshold import build_table_retention_context


# ==============================================================================
# 1. Feature Flag Tests
# ==============================================================================

class TestFeatureFlagConfiguration:

    def test_default_is_disabled(self, monkeypatch):
        monkeypatch.delenv(FLAG_NAME, raising=False)
        assert not is_list_extraction_enabled()
        assert not is_list_extraction_enabled(None)

    @pytest.mark.parametrize("val", ["1", "true", "TRUE", "True", "yes", "YES", "on", "ON", True])
    def test_truthy_flag_values(self, monkeypatch, val):
        if isinstance(val, str):
            monkeypatch.setenv(FLAG_NAME, val)
            assert is_list_extraction_enabled()
        assert is_list_extraction_enabled(override=val)

    @pytest.mark.parametrize("val", ["0", "false", "FALSE", "False", "no", "NO", "off", "OFF", "", False])
    def test_falsy_flag_values(self, monkeypatch, val):
        if isinstance(val, str):
            monkeypatch.setenv(FLAG_NAME, val)
            assert not is_list_extraction_enabled()
        assert not is_list_extraction_enabled(override=val)

    @pytest.mark.parametrize("invalid_val", ["maybe", "enabled", "disabled", "2", "-1", "none", "null"])
    def test_invalid_string_values_fail_safely(self, monkeypatch, invalid_val):
        monkeypatch.setenv(FLAG_NAME, invalid_val)
        with pytest.raises(ValueError, match="Invalid string value"):
            is_list_extraction_enabled()
        with pytest.raises(ValueError, match="Invalid string value"):
            parse_feature_flag(invalid_val)

    def test_invalid_type_fails_safely(self):
        with pytest.raises(ValueError, match="Invalid type"):
            parse_feature_flag([True])
        with pytest.raises(ValueError, match="Invalid type"):
            parse_feature_flag({"enabled": True})

    def test_explicit_override_precedence(self, monkeypatch):
        # Environment is enabled, but override is False -> disabled
        monkeypatch.setenv(FLAG_NAME, "true")
        assert not is_list_extraction_enabled(override=False)

        # Environment is disabled, but override is True -> enabled
        monkeypatch.setenv(FLAG_NAME, "false")
        assert is_list_extraction_enabled(override=True)


# ==============================================================================
# 2. Disabled-Mode Compatibility Verification
# ==============================================================================

class TestDisabledModeCompatibility:

    @pytest.fixture
    def representative_fixtures(self):
        return [
            # 1. Pure prose
            ("<p>The capital of France is Paris. Paris is on the Seine river.</p>", "what is the capital of france"),
            # 2. Single table
            ("""<table>
                  <tr><th>Country</th><th>Capital</th></tr>
                  <tr><td>France</td><td>Paris</td></tr>
                  <tr><td>Germany</td><td>Berlin</td></tr>
                </table>""", "what is the capital of germany"),
            # 3. Mixed prose and table
            ("""<p>Overview of European countries.</p>
                <table>
                  <tr><th>Country</th><th>Population</th></tr>
                  <tr><td>France</td><td>67 million</td></tr>
                </table>""", "population of france"),
            # 4. Document with table and lists
            ("""<table>
                  <tr><th>Name</th><th>Role</th></tr>
                  <tr><td>Alice</td><td>Engineer</td></tr>
                </table>
                <ul>
                  <li>Bob: Manager</li>
                  <li>Charlie: Designer</li>
                </ul>""", "who is the engineer"),
            # 5. Empty document
            ("", "empty query"),
        ]

    def test_disabled_mode_matches_condition_d(self, representative_fixtures):
        for raw_html, query in representative_fixtures:
            # Pre-integration reference (Condition D from eval_experiment_4_2_threshold)
            ref_ctx, ref_telem = build_table_retention_context(
                raw_doc=raw_html,
                query=query,
                table_threshold=0.0,
                max_table_tokens=500,
                token_ceiling=2048,
            )

            # Production integration with feature flag disabled
            prod_ctx, prod_telem = build_structural_context(
                raw_doc=raw_html,
                query=query,
                table_threshold=0.0,
                max_table_tokens=500,
                token_ceiling=2048,
                enable_list_extraction=False,
            )

            # Context text must be byte-for-byte identical
            assert prod_ctx == ref_ctx

            # Structured list header must NEVER appear in disabled mode
            assert "### Structured List:" not in prod_ctx
            assert "### Structured List (Budget Truncated):" not in prod_ctx

            # Telemetry verification
            assert not prod_telem["list_extraction_enabled"]
            assert prod_telem["selected_tables_count"] == ref_telem["selected_tables_count"]
            assert prod_telem["packed_rows_count"] == ref_telem["packed_rows_count"]
            assert prod_telem["ceiling_violation"] == ref_telem["ceiling_violation"]
            assert prod_telem["zero_context"] == ref_telem["zero_context"]

            # No list telemetry keys leaking into disabled mode
            assert "content_list_blocks_found" not in prod_telem
            assert "list_blocks_packed" not in prod_telem


# ==============================================================================
# 3. Context-Budget Accounting & Boundary Tests
# ==============================================================================

class TestContextBudgetAccounting:

    def test_header_and_separator_tokens_accounted_for(self):
        # Massive list that will trigger partial truncation
        items = "".join(f"<li>Item {i}: Some detailed description text with word padding padding</li>\n" for i in range(100))
        html = f"<ul>{items}</ul>"
        query = "test query"

        ceiling = 300
        ctx, telem = build_structural_context(
            raw_doc=html,
            query=query,
            token_ceiling=ceiling,
            enable_list_extraction=True,
        )

        final_toks = estimate_text_tokens(ctx)
        # Strict invariant: context MUST NOT exceed ceiling
        assert final_toks <= ceiling
        assert not telem["ceiling_violation"]
        assert telem["list_blocks_packed"] >= 1
        assert "### Structured List (Budget Truncated):" in ctx

    @pytest.mark.parametrize("ceiling", [200, 350, 500, 1000, 2048])
    def test_strict_ceiling_enforcement_across_scales(self, ceiling):
        items = "".join(f"<li>Section {i}: Extensive details for item {i} with facts facts facts</li>\n" for i in range(200))
        html = f"<p>Lead introductory prose.</p><ul>{items}</ul>"
        query = "extensive details"

        ctx, telem = build_structural_context(
            raw_doc=html,
            query=query,
            token_ceiling=ceiling,
            enable_list_extraction=True,
        )

        final_toks = estimate_text_tokens(ctx)
        assert final_toks <= ceiling
        assert not telem["ceiling_violation"]

    def test_zero_remaining_budget_handling(self):
        # Prose fills the budget completely
        words = "word " * 400
        html = f"<p>{words}</p><ul><li>Should not be packed</li></ul>"
        query = "test"

        ctx, telem = build_structural_context(
            raw_doc=html,
            query=query,
            token_ceiling=250,
            enable_list_extraction=True,
        )

        final_toks = estimate_text_tokens(ctx)
        assert final_toks <= 250
        assert "Should not be packed" not in ctx
        assert telem["list_blocks_packed"] == 0

    def test_empty_lists_and_whitespace_input(self):
        ctx_empty, telem_empty = build_structural_context("", "query", enable_list_extraction=True)
        assert ctx_empty == ""
        assert telem_empty["zero_context"]

        ctx_ws, telem_ws = build_structural_context("   \n\t  ", "query", enable_list_extraction=True)
        assert ctx_ws == ""
        assert telem_ws["zero_context"]

        ctx_empty_ul, telem_empty_ul = build_structural_context("<ul></ul>", "query", enable_list_extraction=True)
        assert ctx_empty_ul == ""
        assert telem_empty_ul["zero_context"]


# ==============================================================================
# 4. Table-List Overlap Deduplication
# ==============================================================================

class TestTableListDeduplication:

    def test_exact_duplicate_list_is_suppressed(self):
        html = """
        <table>
          <tr><th>Band</th><th>Member</th></tr>
          <tr><td>Scorpions</td><td>Klaus Meine</td></tr>
          <tr><td>Scorpions</td><td>Rudolf Schenker</td></tr>
        </table>
        <ul>
          <li>Klaus Meine</li>
          <li>Rudolf Schenker</li>
        </ul>
        """
        query = "who are the members of scorpions"
        ctx, telem = build_structural_context(html, query, enable_list_extraction=True)

        # Table contains members
        assert "| Klaus Meine |" in ctx
        assert "| Rudolf Schenker |" in ctx
        # Standalone list should be deduplicated
        assert telem["deduplicated_list_blocks_count"] >= 1
        assert "### Structured List:" not in ctx

    def test_novel_list_evidence_is_preserved(self):
        html = """
        <table>
          <tr><th>Band</th><th>Album</th></tr>
          <tr><td>Scorpions</td><td>Love at First Sting</td></tr>
        </table>
        <ul>
          <li>Founded: 1965</li>
          <li>Origin: Hanover, Germany</li>
        </ul>
        """
        query = "when was scorpions founded"
        ctx, telem = build_structural_context(html, query, enable_list_extraction=True)

        assert "Love at First Sting" in ctx
        # List contains novel facts (1965, Hanover) not in the table
        assert "Founded: 1965" in ctx
        assert "Origin: Hanover, Germany" in ctx
        assert "### Structured List:" in ctx

    def test_partial_overlap_threshold(self):
        html = """
        <table>
          <tr><th>Item</th></tr>
          <tr><td>Alpha</td></tr>
        </table>
        <ul>
          <li>Alpha</li>
          <li>Beta</li>
          <li>Gamma</li>
          <li>Delta</li>
        </ul>
        """
        # Only 1 of 4 items duplicates the table (25% overlap < 80% threshold)
        query = "list items"
        ctx, telem = build_structural_context(html, query, enable_list_extraction=True)
        assert "Alpha" in ctx
        assert "Beta" in ctx
        assert "Gamma" in ctx
        assert "Delta" in ctx


# ==============================================================================
# 5. Evidence-Level Regression Safeguards
# ==============================================================================

class TestRegressionSafeguards:

    def test_regression_3f5983b2_namibian_minister_evidence(self):
        """
        Case 3f5983b2: 'who is the minister of youth in namibia'
        Gold: Erastus Utoni
        Evidence requirement:
        - Erastus Utoni must be preserved as the minister.
        - Deputy Agnes Tjongarero must retain subordinate context and not obscure Erastus Utoni.
        """
        html = """
        <p>Cabinet of Namibia</p>
        <ul>
          <li>Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni
            <ul>
              <li>Deputy : Agnes Tjongarero</li>
            </ul>
          </li>
        </ul>
        """
        query = "who is the minister of youth in namibia"
        ctx, telem = build_structural_context(html, query, enable_list_extraction=True)

        assert "Erastus Utoni" in ctx
        assert "Minister of Sport , Youth and National Service" in ctx
        # Confirm nesting prefix identifies Deputy as subordinate to the ministry
        assert "Agnes Tjongarero" in ctx
        assert "Deputy" in ctx

    def test_regression_ef634417_scorpions_song_evidence(self):
        """
        Case ef634417: 'who sings the song rock you like a hurricane'
        Gold: Scorpions
        Evidence requirement:
        - The performing band 'Scorpions' must be preserved in context.
        - Redundant songwriters list already in the table must be deduplicated
          to avoid salience distortion.
        """
        html = """
        <table>
          <tr><th>Rock You Like a Hurricane</th><th>Col_2</th></tr>
          <tr><td>Single by Scorpions</td><td></td></tr>
          <tr><td>Songwriter ( s )</td><td>Rudolf Schenker Klaus Meine Herman Rarebell</td></tr>
        </table>
        <ul>
          <li>Rudolf Schenker</li>
          <li>Klaus Meine</li>
          <li>Herman Rarebell</li>
        </ul>
        """
        query = "who sings the song rock you like a hurricane"
        ctx, telem = build_structural_context(html, query, enable_list_extraction=True)

        # Performer is preserved in table
        assert "Single by Scorpions" in ctx
        # Standalone list of songwriters duplicates table cells and must be deduplicated
        assert telem["deduplicated_list_blocks_count"] >= 1
        assert "### Structured List:" not in ctx

    def test_regression_8f1f9bd9_thomas_definition_evidence(self):
        """
        Case 8f1f9bd9: 'what is the definition of the name thomas'
        Gold: twin
        Evidence requirement:
        - Meaning 'twin' must be preserved in table representation.
        - Context has 0 list blocks and must match disabled mode.
        """
        html = """
        <table>
          <tr><th>Thomas</th><th>Col_2</th></tr>
          <tr><td>Word / name</td><td>Aramaic</td></tr>
          <tr><td>Meaning</td><td>twin</td></tr>
        </table>
        """
        query = "what is the definition of the name thomas"
        ctx_enabled, telem_enabled = build_structural_context(html, query, enable_list_extraction=True)
        ctx_disabled, telem_disabled = build_structural_context(html, query, enable_list_extraction=False)

        assert "twin" in ctx_enabled
        assert "Aramaic" in ctx_enabled
        # In the absence of lists, enabled and disabled contexts must be identical
        assert ctx_enabled == ctx_disabled
        assert telem_enabled["content_list_blocks_found"] == 0


# ==============================================================================
# 6. HTML Edge Cases & Resiliency
# ==============================================================================

class TestHTMLEdgeCases:

    def test_malformed_unclosed_tags(self):
        html = """
        <div>
          <ul>
            <li>Unclosed item 1
            <li>Unclosed item 2
            <div>Stray unclosed tag
        """
        blocks = extract_lists_from_html(html)
        assert len(blocks) == 1
        items = blocks[0].items
        assert len(items) == 2
        assert "Unclosed item 1" in items[0].clean_text
        assert "Unclosed item 2" in items[1].clean_text

    def test_navigation_and_boilerplate_filtering(self):
        nav_html = """
        <ul class="nav">
          <li>Home</li>
          <li>About Us</li>
          <li>Contact</li>
          <li>Privacy Policy</li>
        </ul>
        """
        blocks = extract_lists_from_html(nav_html)
        assert len(blocks) == 1
        assert is_nav_or_boilerplate_list(blocks[0])

    def test_html_entity_decoding_and_escaping(self):
        html = """
        <ul>
          <li>Special &amp; Unique: 100 &lt; 200</li>
          <li>Quotes: &quot;Precise&quot; &amp; &apos;Clean&apos;</li>
        </ul>
        """
        query = "test"
        ctx, _ = build_structural_context(html, query, enable_list_extraction=True)
        assert "Special & Unique: 100 < 200" in ctx
        assert 'Quotes: "Precise" & \'Clean\'' in ctx
