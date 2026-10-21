"""
Audit-only unit and safety tests for Experiment 4.4 extractor and context builder.

Tests the actual implementations in:
- scripts/diagnostic_list_extractor.py
- scripts/eval_experiment_4_3_gate2_runner.py (build_candidate_condition_b_context)
- scripts/eval_experiment_4_2_threshold.py (build_table_retention_context)
"""

import sys
from pathlib import Path

# Add project root and scripts
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SRC_DIR = REPO_ROOT / "backend" / "src"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pytest
from diagnostic_list_extractor import (
    ParsedListBlock,
    ParsedListItem,
    extract_lists_from_html,
    is_nav_or_boilerplate_list,
    render_list_to_markdown,
)
from eval_experiment_4_3_gate2_runner import (
    build_candidate_condition_b_context,
)
from eval_experiment_4_2_threshold import (
    build_table_retention_context,
    estimate_text_tokens,
)


# 1. Key-Value Lists
def test_key_value_list_extraction():
    html = """
    <ul>
      <li><strong>Prime Minister:</strong> Narendra Modi</li>
      <li><strong>President:</strong> Droupadi Murmu</li>
    </ul>
    """
    blocks = extract_lists_from_html(html)
    assert len(blocks) == 1
    assert not is_nav_or_boilerplate_list(blocks[0])
    rendered = render_list_to_markdown(blocks[0])
    assert "Prime Minister:" in rendered
    assert "Narendra Modi" in rendered
    assert "President:" in rendered


# 2. Ordered and Unordered Lists
def test_ordered_and_unordered_lists():
    html = """
    <ol>
      <li>First step</li>
      <li>Second step</li>
    </ol>
    <ul>
      <li>Bullet item</li>
    </ul>
    """
    blocks = extract_lists_from_html(html)
    assert len(blocks) == 2
    assert blocks[0].list_type == "ordered"
    assert blocks[1].list_type == "unordered"

    rendered_ol = render_list_to_markdown(blocks[0])
    rendered_ul = render_list_to_markdown(blocks[1])
    assert "1. First step" in rendered_ol
    assert "2. Second step" in rendered_ol
    assert "* Bullet item" in rendered_ul


# 3. Nested Lists
def test_nested_lists():
    html = """
    <ul>
      <li>Parent item
        <ul>
          <li>Child item 1</li>
          <li>Child item 2</li>
        </ul>
      </li>
    </ul>
    """
    blocks = extract_lists_from_html(html)
    assert len(blocks) >= 1
    rendered = "\n".join(render_list_to_markdown(b) for b in blocks)
    assert "Parent item" in rendered
    assert "Child item 1" in rendered


# 4. Malformed HTML
def test_malformed_html():
    html = """
    <ul>
      <li>Unclosed item 1
      <li>Unclosed item 2
      <div>Random unclosed div
    """
    blocks = extract_lists_from_html(html)
    assert len(blocks) == 1
    items = blocks[0].items
    assert len(items) >= 1
    assert "Unclosed item 1" in items[0].clean_text


# 5. Navigation Menus and Irrelevant Lists
def test_navigation_menu_filtering():
    nav_html = """
    <div class="navbox" id="mw-navigation">
      <ul class="vector-menu-content-list">
        <li><a href="/wiki/Main_Page">Home</a></li>
        <li><a href="/wiki/Contact">Contact</a></li>
        <li><a href="/wiki/Special:Random">Random article</a></li>
        <li><a href="/wiki/Help:Contents">Help</a></li>
      </ul>
    </div>
    """
    blocks = extract_lists_from_html(nav_html)
    assert len(blocks) == 1
    assert is_nav_or_boilerplate_list(blocks[0])


# 6. Negative Distractors
def test_negative_distractor_lists():
    html = """
    <div class="footer">
      <ul>
        <li>Privacy policy</li>
        <li>About Wikipedia</li>
        <li>Disclaimers</li>
        <li>Contact Wikipedia</li>
      </ul>
    </div>
    """
    blocks = extract_lists_from_html(html)
    assert len(blocks) == 1
    assert is_nav_or_boilerplate_list(blocks[0])


# 7. Repeated Entities and Duplicate List Entries
def test_repeated_entities():
    html = """
    <ul>
      <li>Winner: Player A</li>
      <li>Winner: Player A</li>
      <li>Runner-up: Player B</li>
    </ul>
    """
    blocks = extract_lists_from_html(html)
    assert len(blocks) == 1
    rendered = render_list_to_markdown(blocks[0])
    assert "Winner: Player A" in rendered
    assert "Runner-up: Player B" in rendered


# 8. Attribution and Entity Binding
def test_attribution_entity_binding():
    html = """
    <ul>
      <li>Director -- Christopher Nolan</li>
      <li>Producer -- Emma Thomas</li>
    </ul>
    """
    blocks = extract_lists_from_html(html)
    assert len(blocks) == 1
    rendered = render_list_to_markdown(blocks[0])
    assert "Director -- Christopher Nolan" in rendered
    assert "Producer -- Emma Thomas" in rendered


# 9. Prose Preservation and Displacement
def test_prose_preservation():
    html = """
    <p>Namibia gained independence in 1990.</p>
    <ul>
      <li>Ministry of Sport: Erastus Utoni</li>
    </ul>
    """
    query = "minister of youth in namibia"
    ctx, telem = build_candidate_condition_b_context(html, query, token_ceiling=2048)
    assert "### Clean Prose:" in ctx
    assert "Namibia gained independence in 1990." in ctx
    assert "### Structured List:" in ctx
    # Prose must precede the list
    prose_idx = ctx.find("### Clean Prose:")
    list_idx = ctx.find("### Structured List:")
    assert prose_idx < list_idx


# 10. Empty or Malformed Extraction Output
def test_empty_or_malformed_input():
    ctx, telem = build_candidate_condition_b_context("", "query", token_ceiling=2048)
    assert ctx == ""
    assert telem["zero_context"]

    ctx_ws, telem_ws = build_candidate_condition_b_context("   \n\t  ", "query", token_ceiling=2048)
    assert ctx_ws == ""
    assert telem_ws["zero_context"]


# 11. Context Budget Enforcement & Boundary Cases
def test_context_budget_enforcement():
    # Construct a massive list that exceeds 2048 tokens
    large_items = "".join(f"<li>Item {i}: Some detailed description with padding text words words words</li>\n" for i in range(300))
    html = f"<ul>{large_items}</ul>"
    query = "test query"
    ctx, telem = build_candidate_condition_b_context(html, query, token_ceiling=500)
    toks = estimate_text_tokens(ctx)
    assert not telem["ceiling_violation"]
    assert telem["total_context_estimated_tokens"] <= 500
    # Note: Full serialized context may include section header tokens (e.g. ~20 tokens)
    assert toks <= 530


# 12. HTML Escaping and Untrusted Source Text
def test_html_escaping_and_special_chars():
    html = """
    <ul>
      <li>&lt;Special Tag&gt; &amp; "Quotes"</li>
      <li>Price: $100 &gt; $50</li>
    </ul>
    """
    blocks = extract_lists_from_html(html)
    assert len(blocks) == 1
    rendered = render_list_to_markdown(blocks[0])
    assert "<Special Tag>" in rendered or "&lt;Special Tag&gt;" in rendered
    assert "Price:" in rendered


# 13. Audit of the Three D-to-E Regressions
def test_regression_case_3f5983b2():
    # Namibian youth minister: nested list structure
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
    ctx, telem = build_candidate_condition_b_context(html, query, token_ceiling=2048)
    assert "Erastus Utoni" in ctx
    assert "Agnes Tjongarero" in ctx
    assert telem["total_context_estimated_tokens"] < 2048


def test_regression_case_ef634417():
    # Scorpions song: table + songwriters list
    html = """
    <table>
      <tr><th>Rock You Like a Hurricane</th></tr>
      <tr><td>Single by Scorpions</td></tr>
    </table>
    <ul>
      <li>Rudolf Schenker</li>
      <li>Klaus Meine</li>
      <li>Herman Rarebell</li>
    </ul>
    """
    query = "who sings the song rock you like a hurricane"
    ctx, telem = build_candidate_condition_b_context(html, query, token_ceiling=2048)
    assert "Single by Scorpions" in ctx
    assert "Rudolf Schenker" in ctx
    assert "Klaus Meine" in ctx


def test_regression_case_8f1f9bd9():
    # Thomas definition: table with NO lists
    html = """
    <table>
      <tr><th>Thomas</th></tr>
      <tr><td>Word / name</td><td>Aramaic</td></tr>
      <tr><td>Meaning</td><td>twin</td></tr>
    </table>
    """
    query = "what is the definition of the name thomas"
    ctx, telem = build_candidate_condition_b_context(html, query, token_ceiling=2048)
    assert telem["content_list_blocks_found"] == 0
    assert "twin" in ctx
