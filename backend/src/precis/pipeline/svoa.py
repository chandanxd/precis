from __future__ import annotations

from functools import lru_cache

from spacy import load
from spacy.language import Language
from spacy.tokens import Span, Token

from precis.graph.schema import Fact

__all__ = ["extract_facts"]

MODEL_NAME = "en_core_web_lg"


# Lexical resources

_COPULAR_VERBS = {
    "be",
    "become",
    "appear",
    "remain",
    "seem",
    "look",
    "sound",
    "feel",
    "smell",
    "taste",
}
_NEGATION_CUES = {
    "not",
    "never",
    "no",
    "neither",
    "nor",
    "n't",
    "cannot",
    "cant",
    "wont",
    "wouldnt",
    "couldnt",
    "shouldnt",
    "dont",
    "doesnt",
    "didnt",
    "isnt",
    "arent",
    "wasnt",
    "werent",
    "hasnt",
    "havent",
    "hadnt",
}
_TEMPORAL_MARKERS = {
    "on",
    "in",
    "during",
    "after",
    "before",
    "since",
    "until",
    "by",
    "at",
    "from",
    "to",
    "between",
    "within",
    "throughout",
    "over",
    "under",
    "ago",
    "later",
    "earlier",
    "today",
    "tomorrow",
    "yesterday",
    "now",
    "then",
    "soon",
    "recently",
    "lately",
    "formerly",
    "previously",
    "subsequently",
    "eventually",
    "finally",
    "initially",
    "originally",
}
_SPATIAL_MARKERS = {
    "in",
    "at",
    "near",
    "from",
    "to",
    "across",
    "through",
    "into",
    "onto",
    "upon",
    "within",
    "outside",
    "inside",
    "above",
    "below",
    "under",
    "over",
    "between",
    "among",
    "around",
    "behind",
    "beside",
    "beyond",
    "down",
    "up",
    "off",
    "out",
    "away",
    "here",
    "there",
    "everywhere",
    "somewhere",
    "nowhere",
}
_CAUSAL_MARKERS = {
    "because",
    "due",
    "since",
    "as",
    "owing",
    "for",
    "therefore",
    "thus",
    "hence",
    "consequently",
    "accordingly",
    "resulting",
    "causing",
    "leading",
    "stemming",
    "arising",
    "result",
    "effect",
    "outcome",
}
_CONDITIONAL_MARKERS = {
    "if",
    "unless",
    "provided",
    "assuming",
    "suppose",
    "whether",
    "given",
    "granted",
    "presuming",
    "in case",
    "on condition",
    "as long as",
    "so long as",
}
_REPORTING_VERBS = {
    "say",
    "said",
    "claim",
    "claimed",
    "report",
    "reported",
    "argue",
    "argued",
    "state",
    "stated",
    "assert",
    "asserted",
    "suggest",
    "suggested",
    "announce",
    "announced",
    "declare",
    "declared",
    "note",
    "noted",
    "believe",
    "believed",
    "contend",
    "contended",
    "maintain",
    "maintained",
    "acknowledge",
    "acknowledged",
    "admit",
    "admitted",
    "confirm",
    "confirmed",
    "deny",
    "denied",
    "explain",
    "explained",
    "mention",
    "mentioned",
    "remark",
    "remarked",
    "indicate",
    "indicated",
    "reveal",
    "revealed",
    "disclose",
    "disclosed",
    "affirm",
    "affirmed",
    "allege",
    "alleged",
    "insist",
    "insisted",
    "observe",
    "observed",
    "point out",
    "pointed out",
    "stress",
    "stressed",
    "emphasise",
    "emphasised",
    "emphasize",
    "emphasized",
}
_MODAL_VERBS = {
    "might",
    "could",
    "would",
    "may",
    "should",
    "shall",
    "can",
    "will",
    "must",
    "ought",
    "need",
    "dare",
    "used",
}


# spaCy model loading


@lru_cache(maxsize=1)
def get_nlp() -> Language:
    """Load and cache the spaCy pipeline."""
    try:
        return load(MODEL_NAME)
    except OSError as exc:
        raise RuntimeError(
            f"spaCy model '{MODEL_NAME}' is not installed. "
            f"Install it with: python -m spacy download {MODEL_NAME}"
        ) from exc


# Public API


def extract_facts(text: str, source_doc: str = "") -> list[Fact]:
    """
    Extract Fact objects from coreference-resolved English text.

    The input is expected to be the output of Stage 1 (coreference resolution).
    A sentence may produce zero or more facts.
    """
    if not text or not text.strip():
        return []

    doc = get_nlp()(text)
    facts: list[Fact] = []

    for sentence_id, sentence in enumerate(doc.sents):
        sentence_facts = _extract_from_sentence(sentence, source_doc, sentence_id)
        facts.extend(sentence_facts)

    return facts


# Per-sentence extraction


def _extract_from_sentence(
    sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """Extract all facts from a single sentence."""
    root = _find_root(sentence)
    if root is None:
        return []

    facts: list[Fact] = []

    # Primary SVOA proposition
    primary = _extract_primary_fact(root, sentence, source_doc, sentence_id)
    if primary is not None:
        facts.append(primary)

    # Additional propositions from coordination
    facts.extend(_extract_coordination(root, sentence, source_doc, sentence_id))

    # Relative clauses
    facts.extend(_extract_relative_clauses(sentence, source_doc, sentence_id))

    # Clausal complements (reported speech, mental states)
    facts.extend(_extract_clausal_complements(root, sentence, source_doc, sentence_id))

    # Ditransitive / indirect objects
    facts.extend(_extract_ditransitive(root, sentence, source_doc, sentence_id))

    return facts


def _find_root(sentence: Span) -> Token | None:
    """Return the root token of a sentence, or None if not found."""
    for token in sentence:
        if token.dep_ == "ROOT" or token.head == token:
            return token
    return sentence.root if sentence else None


# Primary fact extraction


def _extract_primary_fact(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> Fact | None:
    """Extract the primary SVOA fact from a sentence."""
    if _is_copular(root):
        return _extract_copular(root, sentence, source_doc, sentence_id)
    return _extract_svoa(root, sentence, source_doc, sentence_id)


# Copular / attributive extraction


def _extract_copular(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> Fact | None:
    """
    Extract facts from copular constructions:
        "X is Y"       → subject=X, verb=is, object=Y
        "X became Y"   → subject=X, verb=became, object=Y
        "X seems happy"→ subject=X, verb=seems, object=happy
    """
    subject = _get_subject(root)
    if not subject:
        return None

    verb = _get_verb_phrase(root)
    negated = _is_negated(root)
    modality = _get_modality(root, sentence)
    attributed_to = _get_attribution(root)
    adjuncts = _extract_adjuncts(root)

    # Try to find the predicative complement
    # Order of preference: attr > acomp > xcomp > dobj > pobj of prep
    comp_text = None

    # 1. Direct attribute (nsubj + attr)
    for child in root.children:
        if child.dep_ == "attr":
            comp_text = _get_span_text(child)
            break

    # 2. Adjectival complement
    if not comp_text:
        for child in root.children:
            if child.dep_ == "acomp":
                comp_text = _get_span_text(child)
                break

    # 3. Open clausal complement ("He seems to know")
    if not comp_text:
        for child in root.children:
            if child.dep_ == "xcomp":
                comp_text = _get_span_text(child)
                break

    # 4. Prepositional complement ("The book is on the table")
    if not comp_text:
        for child in root.children:
            if child.dep_ == "prep":
                comp_text = _get_prepositional_phrase(child)
                break

    # 5. Adverbial modifier as fallback ("He is here")
    if not comp_text:
        for child in root.children:
            if child.dep_ in {"advmod", "npadvmod"} and child.ent_type_ not in {
                "DATE",
                "TIME",
            }:
                comp_text = child.text
                break

    if not comp_text:
        return None

    return _build_fact(
        subject=subject,
        verb=verb,
        object=comp_text,
        adjuncts=adjuncts,
        negated=negated,
        modality=modality,
        attributed_to=attributed_to,
        source_doc=source_doc,
        sentence_id=sentence_id,
        raw_sentence=sentence.text,
    )


# Standard SVOA extraction


def _extract_svoa(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> Fact | None:
    """
    Extract standard Subject-Verb-Object-Adjunct facts.
    Handles active voice, passive voice, and various argument structures.
    """
    subject = _get_subject(root)
    if not subject:
        return None

    verb = _get_verb_phrase(root)
    negated = _is_negated(root)
    modality = _get_modality(root, sentence)
    attributed_to = _get_attribution(root)
    adjuncts = _extract_adjuncts(root)

    # Try to find object
    obj_text = _get_object(root)

    # If no direct object, try clausal complement
    if not obj_text:
        for child in root.children:
            if child.dep_ in {"ccomp", "xcomp"}:
                obj_text = _get_span_text(child)
                break

    # If still no object, try prepositional object as fallback
    if not obj_text:
        for child in root.children:
            if child.dep_ == "prep":
                for grandchild in child.children:
                    if grandchild.dep_ == "pobj":
                        obj_text = _get_span_text(grandchild)
                        break
                if obj_text:
                    break

    # For intransitive verbs, we allow no object
    if not obj_text:
        obj_text = ""

    return _build_fact(
        subject=subject,
        verb=verb,
        object=obj_text,
        adjuncts=adjuncts,
        negated=negated,
        modality=modality,
        attributed_to=attributed_to,
        source_doc=source_doc,
        sentence_id=sentence_id,
        raw_sentence=sentence.text,
    )


# Coordination extraction


def _extract_coordination(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """
    Extract facts from coordinated subjects, verbs, or objects.

    Examples:
        "John and Mary ate pizza" → two facts with same verb/object
        "John ate pizza and drank water" → two facts with same subject
        "John ate pizza and pasta" → two facts with same subject/verb
    """
    facts: list[Fact] = []

    # Find conjunctions attached to the root or its children
    conj_tokens = [t for t in sentence if t.dep_ == "conj"]

    for conj in conj_tokens:
        # Determine what is being conjoined by looking at the head
        head = conj.head

        # Coordinated subjects: "John and Mary ran"
        if head.dep_ in {"nsubj", "nsubjpass"}:
            # The head is a subject; conj is another subject with same predicate
            # Find the verb (root of the sentence)
            verb = head.head if head.head.pos_ in {"VERB", "AUX"} else root
            if verb.pos_ not in {"VERB", "AUX"}:
                continue

            subj_text = _get_span_text(conj)
            verb_phrase = _get_verb_phrase(verb)
            obj_text = _get_object(verb) or ""
            negated = _is_negated(verb)
            modality = _get_modality(verb, sentence)
            adjuncts = _extract_adjuncts(verb)

            fact = _build_fact(
                subject=subj_text,
                verb=verb_phrase,
                object=obj_text,
                adjuncts=adjuncts,
                negated=negated,
                modality=modality,
                source_doc=source_doc,
                sentence_id=sentence_id,
                raw_sentence=sentence.text,
            )
            facts.append(fact)

        # Coordinated verbs: "John ran and swam"
        elif head.pos_ in {"VERB", "AUX"} and head == root:
            subj_text = _get_subject(head) or _get_subject(root) or ""
            if not subj_text:
                continue

            verb_phrase = _get_verb_phrase(conj)
            obj_text = _get_object(conj) or _get_object(head) or ""
            negated = _is_negated(conj) or _is_negated(head)
            modality = _get_modality(conj, sentence)
            adjuncts = _extract_adjuncts(conj)

            fact = _build_fact(
                subject=subj_text,
                verb=verb_phrase,
                object=obj_text,
                adjuncts=adjuncts,
                negated=negated,
                modality=modality,
                source_doc=source_doc,
                sentence_id=sentence_id,
                raw_sentence=sentence.text,
            )
            facts.append(fact)

        # Coordinated objects: "John ate pizza and pasta"
        elif head.dep_ == "obj":
            verb = head.head
            if verb.pos_ not in {"VERB", "AUX"}:
                continue

            subj_text = _get_subject(verb) or ""
            if not subj_text:
                continue

            verb_phrase = _get_verb_phrase(verb)
            obj_text = _get_span_text(conj)
            negated = _is_negated(verb)
            modality = _get_modality(verb, sentence)
            adjuncts = _extract_adjuncts(verb)

            fact = _build_fact(
                subject=subj_text,
                verb=verb_phrase,
                object=obj_text,
                adjuncts=adjuncts,
                negated=negated,
                modality=modality,
                source_doc=source_doc,
                sentence_id=sentence_id,
                raw_sentence=sentence.text,
            )
            facts.append(fact)

    return facts


# Relative clause extraction


def _extract_relative_clauses(
    sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """
    Extract facts from relative clauses.

    Example: "The man who discovered penicillin was a scientist"
    → Fact(subject="The man", verb="discovered", object="penicillin")
    """
    facts: list[Fact] = []

    for token in sentence:
        if token.dep_ != "relcl":
            continue

        # token is the relative clause verb (e.g., "discovered")
        # token.head is the noun being modified (e.g., "man")
        antecedent = token.head
        antecedent_text = _get_span_text(antecedent)

        # The relative clause verb becomes the predicate
        verb = _get_verb_phrase(token)
        negated = _is_negated(token)
        modality = _get_modality(token, sentence)
        adjuncts = _extract_adjuncts(token)

        # Try to find object of the relative clause verb
        obj_text = _get_object(token) or ""

        # If no direct object, look for other complements
        if not obj_text:
            for child in token.children:
                if child.dep_ in {"attr", "acomp", "xcomp", "ccomp"}:
                    obj_text = _get_span_text(child)
                    break

        # Handle "The man who was killed by police"
        if not obj_text and any(child.dep_ == "agent" for child in token.children):
            # Passive relative - the antecedent is the object
            # The agent becomes the subject
            agent = _get_agent(token)
            if agent:
                fact = _build_fact(
                    subject=agent,
                    verb=verb,
                    object=antecedent_text,
                    adjuncts=adjuncts,
                    negated=negated,
                    modality=modality,
                    source_doc=source_doc,
                    sentence_id=sentence_id,
                    raw_sentence=sentence.text,
                )
                facts.append(fact)
                continue

        # Standard relative clause: antecedent is the subject
        fact = _build_fact(
            subject=antecedent_text,
            verb=verb,
            object=obj_text,
            adjuncts=adjuncts,
            negated=negated,
            modality=modality,
            source_doc=source_doc,
            sentence_id=sentence_id,
            raw_sentence=sentence.text,
        )
        facts.append(fact)

    return facts


# Clausal complement extraction


def _extract_clausal_complements(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """
    Extract facts from clausal complements (reported speech, mental states).

    Example: "She said that he left" → Fact(subject="he", verb="left", object="")
    Example: "He believes the market will crash" → Fact(subject="market", verb="will crash", object="")
    """
    facts: list[Fact] = []

    for child in root.children:
        if child.dep_ not in {"ccomp", "xcomp"}:
            continue

        # ccomp: clausal complement with internal subject
        # xcomp: open clausal complement (no internal subject, shares with parent)

        if child.dep_ == "ccomp":
            # Find the subject within the complement clause
            comp_subj = _get_subject(child)
            if not comp_subj:
                # Sometimes the subject is the same as the matrix clause (e.g., "He wants to go")
                comp_subj = _get_subject(root) or ""

            comp_verb = _get_verb_phrase(child)
            comp_obj = _get_object(child) or ""
            negated = _is_negated(child)
            modality = _get_modality(child, sentence)
            adjuncts = _extract_adjuncts(child)

            fact = _build_fact(
                subject=comp_subj,
                verb=comp_verb,
                object=comp_obj,
                adjuncts=adjuncts,
                negated=negated,
                modality=modality,
                source_doc=source_doc,
                sentence_id=sentence_id,
                raw_sentence=sentence.text,
            )
            facts.append(fact)

        elif child.dep_ == "xcomp":
            # Open clausal complement - subject is shared with matrix clause
            comp_subj = _get_subject(root) or ""
            comp_verb = _get_verb_phrase(child)
            comp_obj = _get_object(child) or ""
            negated = _is_negated(child) or _is_negated(root)
            modality = _get_modality(child, sentence)
            adjuncts = _extract_adjuncts(child)

            fact = _build_fact(
                subject=comp_subj,
                verb=comp_verb,
                object=comp_obj,
                adjuncts=adjuncts,
                negated=negated,
                modality=modality,
                source_doc=source_doc,
                sentence_id=sentence_id,
                raw_sentence=sentence.text,
            )
            facts.append(fact)

    return facts


# Ditransitive extraction


def _extract_ditransitive(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """
    Extract facts from ditransitive verbs (verbs with both direct and indirect objects).

    Example: "John gave Mary a book"
    → Fact(subject="John", verb="gave", object="a book", adjuncts={"recipient": "Mary"})
    """
    facts: list[Fact] = []

    # Check if this verb has a dative child
    dative = None
    for child in root.children:
        if child.dep_ == "dative":
            dative = child
            break

    if not dative:
        return facts

    subject = _get_subject(root)
    if not subject:
        return facts

    verb = _get_verb_phrase(root)
    dobj = _get_object(root)
    negated = _is_negated(root)
    modality = _get_modality(root, sentence)
    adjuncts = _extract_adjuncts(root)

    # Add the dative as a recipient adjunct
    recipient_text = _get_span_text(dative)
    if "recipient" not in adjuncts:
        adjuncts["recipient"] = [recipient_text]
    else:
        adjuncts["recipient"].append(recipient_text)

    fact = _build_fact(
        subject=subject,
        verb=verb,
        object=dobj or "",
        adjuncts=adjuncts,
        negated=negated,
        modality=modality,
        source_doc=source_doc,
        sentence_id=sentence_id,
        raw_sentence=sentence.text,
    )
    facts.append(fact)

    return facts


# Lexical helpers


def _is_copular(root: Token) -> bool:
    """Return whether the root is a copular verb."""
    return root.lemma_.lower() in _COPULAR_VERBS


def _is_negated(root: Token) -> bool:
    """Return whether the predicate is negated."""
    # Check direct negation children
    for child in root.children:
        if child.dep_ == "neg":
            return True
        if child.text.lower() in _NEGATION_CUES:
            return True
        if child.dep_ == "aux" and child.text.lower().endswith("n't"):
            return True
        if child.dep_ == "aux" and child.lemma_.lower() in {
            "not",
            "no",
            "never",
            "neither",
            "nor",
        }:
            return True

    # Check negation in the verb text itself
    if "n't" in root.text.lower() or "not" in root.text.lower():
        return True

    # Check for "no" as determiner of object
    for child in root.children:
        if child.dep_ == "obj":
            for grandchild in child.children:
                if grandchild.dep_ == "det" and grandchild.text.lower() == "no":
                    return True

    return False


# Span helpers


def _get_span_text(token: Token) -> str:
    """Return the text spanned by a token's subtree."""
    if token is None:
        return ""
    start = token.left_edge.i
    end = token.right_edge.i + 1
    return token.doc[start:end].text.strip()


def _get_prepositional_phrase(preposition: Token) -> str:
    """Return the full text of a prepositional phrase."""
    return _get_span_text(preposition)


# Argument helpers


def _get_subject(root: Token) -> str | None:
    """Return the sentence subject, if present."""
    for child in root.children:
        if child.dep_ in {"nsubj", "nsubjpass", "csubj", "csubjpass"}:
            return _get_span_text(child)
    return None


def _get_object(root: Token) -> str | None:
    """Return the direct object, if present."""
    for child in root.children:
        if child.dep_ == "obj":
            return _get_span_text(child)
        # Also check for dobj (older spaCy versions)
        if child.dep_ == "dobj":
            return _get_span_text(child)
    return None


def _get_agent(root: Token) -> str | None:
    """Return the agent of a passive construction, if present."""
    for child in root.children:
        if child.dep_ == "agent":
            for grandchild in child.children:
                if grandchild.dep_ == "pobj":
                    return _get_span_text(grandchild)

        if child.dep_ == "prep" and child.text.lower() == "by":
            for grandchild in child.children:
                if grandchild.dep_ in {"pobj", "obj"}:
                    return _get_span_text(grandchild)

    return None


# Predicate helpers


def _get_verb_phrase(root: Token) -> str:
    """Return the verb phrase headed by the root, including auxiliaries and particles."""
    parts: list[str] = []

    # Collect auxiliaries before the main verb
    auxiliaries = []
    for child in root.children:
        if child.dep_ in {"aux", "auxpass"} and child.i < root.i:
            auxiliaries.append(child)

    # Sort by token position
    auxiliaries.sort(key=lambda t: t.i)

    for aux in auxiliaries:
        parts.append(aux.text)

    parts.append(root.text)

    # Particle (phrasal verb)
    for child in sorted(root.children, key=lambda t: t.i):
        if child.dep_ == "prt":
            parts.append(child.text)

    return " ".join(parts)


# Adjunct extraction


def _classify_adjunct(preposition: Token) -> str:
    """Return the semantic category of a prepositional phrase."""
    marker = preposition.text.lower()

    if marker in _TEMPORAL_MARKERS:
        return "time"
    if marker in _SPATIAL_MARKERS:
        return "location"
    if marker in _CAUSAL_MARKERS:
        return "cause"
    return "context"


def _extract_adjuncts(root: Token) -> dict[str, list[str]]:
    """Extract adjunct information attached to the predicate."""
    adjuncts: dict[str, list[str]] = {}

    for child in root.children:
        # Prepositional phrase
        if child.dep_ == "prep":
            category = _classify_adjunct(child)
            phrase = _get_prepositional_phrase(child)
            if category not in adjuncts:
                adjuncts[category] = []
            adjuncts[category].append(phrase)
            continue

        # Temporal adverbs and noun phrases
        if child.dep_ in {"advmod", "npadvmod"}:
            if child.ent_type_ in {"DATE", "TIME"}:
                if "time" not in adjuncts:
                    adjuncts["time"] = []
                adjuncts["time"].append(child.text)
                continue

            # Manner adverbs (not negation, not temporal)
            if child.dep_ == "neg":
                continue  # Negation is handled separately

            if "manner" not in adjuncts:
                adjuncts["manner"] = []
            adjuncts["manner"].append(child.text)
            continue

        # Adverbial clause modifiers
        if child.dep_ == "advcl":
            if "context" not in adjuncts:
                adjuncts["context"] = []
            adjuncts["context"].append(_get_span_text(child))
            continue

        # Adjectival modifiers that provide manner/quality
        if child.dep_ == "amod" and child.head == root:
            if "manner" not in adjuncts:
                adjuncts["manner"] = []
            adjuncts["manner"].append(child.text)

    return adjuncts


# Modality detection


def _get_modality(root: Token, sentence: Span) -> str:
    """Return the epistemic modality of a proposition."""

    # Conditional propositions
    for token in sentence:
        if token.text.lower() in _CONDITIONAL_MARKERS and token.dep_ in {
            "mark",
            "advmod",
            "prep",
            "cc",
        }:
            return "conditional"

    # Attributed propositions (reporting verbs)
    if root.lemma_.lower() in _REPORTING_VERBS:
        return "attributed"

    # Hypothetical propositions (modal verbs)
    for child in root.children:
        if child.dep_ in {"aux", "auxpass"} and child.lemma_.lower() in _MODAL_VERBS:
            return "hypothetical"

    # Check if the root itself is a modal
    if root.lemma_.lower() in _MODAL_VERBS:
        return "hypothetical"

    return "asserted"


def _get_attribution(root: Token) -> str | None:
    """Return the source of an attributed proposition, if present."""
    if root.lemma_.lower() not in _REPORTING_VERBS:
        return None
    return _get_subject(root)


# Fact builder


def _build_fact(
    *,
    subject: str,
    verb: str,
    object: str,
    adjuncts: dict[str, list[str]] | None = None,
    negated: bool = False,
    modality: str = "asserted",
    attributed_to: str | None = None,
    disjunctive: bool = False,
    source_doc: str = "",
    sentence_id: int = 0,
    raw_sentence: str = "",
) -> Fact:
    """Construct a Fact with sensible defaults."""
    return Fact(
        subject=subject,
        verb=verb,
        object=object,
        adjuncts=adjuncts or {},
        negated=negated,
        modality=modality,
        attributed_to=attributed_to,
        disjunctive=disjunctive,
        sdh_score=0.0,
        embedding=[],
        source_doc=source_doc,
        sentence_id=sentence_id,
        raw_sentence=raw_sentence,
    )
