"""
Integrity and Fixture Tests for Experiment 4.3 Diagnostic List Extraction.

Tests all 5 minimal reproducible fixtures:
1. Key-value / entity-role binding lists
2. Nested hierarchical lists
3. Ordered ranked lists
4. Malformed / unclosed list markup
5. Negative boilerplate / navigation filtering
"""

from pathlib import Path
import pytest
import sys

# Add scripts to path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from diagnostic_list_extractor import (
    RobustListParser,
    extract_lists_from_html,
    is_nav_or_boilerplate_list,
    render_list_to_markdown,
)

FIXTURES_DIR = (
    SCRIPTS_DIR.parent
    / "results"
    / "diagnostic_experiment_4_v1"
    / "failure_attribution_20261010"
    / "extraction_fixtures"
)


class TestExperiment43Fixtures:

    def test_fixture_01_key_value_binding_and_qualifiers(self):
        """Verify entity-to-role binding and qualifier extraction."""
        fixture_path = FIXTURES_DIR / "fixture_01_key_value_list.html"
        assert fixture_path.exists(), f"Missing fixture {fixture_path}"

        html_content = fixture_path.read_text(encoding="utf-8")
        blocks = extract_lists_from_html(html_content)

        assert len(blocks) == 1
        b = blocks[0]
        assert b.list_type == "unordered"
        assert len(b.items) == 4

        # Item 0: Stephen Graham -- Detective Superintendent Dave Kelly
        it0 = b.items[0]
        assert it0.entity_binding is not None
        subj, role = it0.entity_binding
        assert subj == "Stephen Graham"
        assert role == "Detective Superintendent Dave Kelly"

        # Item 1: Kirk Douglas as Matt Morgan
        it1 = b.items[1]
        assert it1.entity_binding is not None
        subj1, role1 = it1.entity_binding
        assert subj1 == "Kirk Douglas"
        assert role1 == "Matt Morgan"

        # Item 3: Qualifiers preserved
        it3 = b.items[3]
        assert "UK" in it3.qualifiers or "US" in it3.qualifiers

    def test_fixture_02_nested_list_hierarchy(self):
        """Verify nested list prefixing and parent-child association."""
        fixture_path = FIXTURES_DIR / "fixture_02_nested_list.html"
        assert fixture_path.exists()

        html_content = fixture_path.read_text(encoding="utf-8")
        blocks = extract_lists_from_html(html_content)

        # There are 2 sub-lists within the main list
        assert len(blocks) >= 2
        # Check that children have parent prefix
        all_items = [it for b in blocks for it in b.items]
        new_england_items = [it for it in all_items if "New England" in it.parent_prefix]
        assert len(new_england_items) == 3
        states = [it.clean_text for it in new_england_items]
        assert any("Connecticut" in s for s in states)
        assert any("Massachusetts" in s for s in states)

    def test_fixture_03_ordered_rankings(self):
        """Verify ordered list indexing and ranking preservation."""
        fixture_path = FIXTURES_DIR / "fixture_03_ordered_list.html"
        assert fixture_path.exists()

        html_content = fixture_path.read_text(encoding="utf-8")
        blocks = extract_lists_from_html(html_content)

        assert len(blocks) == 1
        b = blocks[0]
        assert b.list_type == "ordered"
        assert len(b.items) == 6

        md = render_list_to_markdown(b)
        assert "1. China: 19%" in md
        assert "6. South Africa: 1%" in md

    def test_fixture_04_malformed_unclosed_tags(self):
        """Verify robust recovery from unclosed <li> tags without data loss."""
        fixture_path = FIXTURES_DIR / "fixture_04_malformed_list.html"
        assert fixture_path.exists()

        html_content = fixture_path.read_text(encoding="utf-8")
        blocks = extract_lists_from_html(html_content)

        assert len(blocks) == 1
        b = blocks[0]
        assert len(b.items) == 3

        texts = [it.clean_text for it in b.items]
        assert any("Spencer Treat Clark" in t for t in texts)
        assert any("Connie Nielsen" in t for t in texts)
        assert any("Joaquin Phoenix" in t for t in texts)

    def test_fixture_05_negative_boilerplate_filtering(self):
        """Verify that navigation boilerplate lists are filtered out while content lists remain."""
        fixture_path = FIXTURES_DIR / "fixture_05_negative_distractor_list.html"
        assert fixture_path.exists()

        html_content = fixture_path.read_text(encoding="utf-8")
        blocks = extract_lists_from_html(html_content)

        content_blocks = [b for b in blocks if not is_nav_or_boilerplate_list(b)]
        boilerplate_blocks = [b for b in blocks if is_nav_or_boilerplate_list(b)]

        assert len(content_blocks) == 1
        content_items = [it.clean_text for it in content_blocks[0].items]
        assert any("Travis Tritt" in t for t in content_items)
        assert any("Marty Stuart" in t for t in content_items)

        # Nav list must be identified as boilerplate
        assert len(boilerplate_blocks) >= 1
        nav_items = [it.clean_text for b in boilerplate_blocks for it in b.items]
        assert "Home" in nav_items or "Terms of Service" in nav_items
