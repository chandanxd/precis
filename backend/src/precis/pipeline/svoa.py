from __future__ import annotations

from functools import lru_cache

from spacy import load
from spacy.language import Language
from spacy.tokens import Span, Token

from precis.graph.schema import Fact

__all__ = ["extract_facts"]

MODEL_NAME = "en_core_web_lg"

# ---------------------------------------------------------------------------
# Lexical resources
# ---------------------------------------------------------------------------

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

# Keep this list focused on predicates that introduce a source/claim.
# Evidential predicates such as "confirm" remain asserted rather than attributed.
_REPORTING_VERBS = {
    "say",
    "claim",
    "report",
    "argue",
    "state",
    "assert",
    "suggest",
    "announce",
    "declare",
    "note",
    "believe",
    "contend",
    "maintain",
    "explain",
    "mention",
    "remark",
    "allege",
    "insist",
    "stress",
    "emphasise",
    "emphasize",
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


# Common English phrasal-verb particles. spaCy may parse these as either
# ``prt`` or ``prep`` depending on the construction and model.
_PHRASAL_PARTICLES = {
    "about",
    "across",
    "ahead",
    "along",
    "around",
    "aside",
    "away",
    "back",
    "by",
    "down",
    "forth",
    "forward",
    "in",
    "off",
    "on",
    "out",
    "over",
    "past",
    "through",
    "together",
    "under",
    "up",
}

# ---------------------------------------------------------------------------
# spaCy model loading
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_facts(text: str, source_doc: str = "") -> list[Fact]:
    """Extract SVOA facts from coreference-resolved English text."""
    if not text or not text.strip():
        return []

    doc = get_nlp()(text)
    facts: list[Fact] = []

    for sentence_id, sentence in enumerate(doc.sents):
        facts.extend(_extract_from_sentence(sentence, source_doc, sentence_id))

    return _deduplicate_facts(facts)


# ---------------------------------------------------------------------------
# Per-sentence extraction
# ---------------------------------------------------------------------------


def _extract_from_sentence(
    sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """Extract the primary proposition and secondary embedded propositions."""
    root = _find_root(sentence)
    if root is None:
        return []

    facts: list[Fact] = []

    primary = _extract_primary_fact(root, sentence, source_doc, sentence_id)
    if primary is not None:
        facts.append(primary)

    facts.extend(_extract_coordination(root, sentence, source_doc, sentence_id))
    facts.extend(_extract_relative_clauses(sentence, source_doc, sentence_id))
    facts.extend(_extract_clausal_complements(root, sentence, source_doc, sentence_id))

    # Ditransitives are argument structures, not separate propositions. The
    # primary extractor already enriches their fact with recipient metadata.
    # Keep the helper for compatibility, but do not emit a duplicate fact.

    return facts


def _find_root(sentence: Span) -> Token | None:
    """Return the root token of a sentence, or None if not found."""
    for token in sentence:
        if token.dep_ == "ROOT" or token.head == token:
            return token
    return sentence.root if sentence else None


# ---------------------------------------------------------------------------
# Primary fact extraction
# ---------------------------------------------------------------------------


def _extract_primary_fact(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> Fact | None:
    """Extract the primary SVOA fact from a sentence."""
    if _is_copular(root):
        return _extract_copular(root, sentence, source_doc, sentence_id)

    # Some spaCy parses make the lexical complement the sentence root and
    # attach the copula as ``cop``. Others expose the copular token elsewhere
    # in the sentence. Recover that structure before falling back to SVOA.
    copular_token = next(
        (
            token
            for token in sentence
            if token is not root
            and token.lemma_.lower() in _COPULAR_VERBS
            and token.dep_ in {"cop", "aux", "ROOT"}
        ),
        None,
    )
    if copular_token is not None:
        return _extract_copular(root, sentence, source_doc, sentence_id)

    return _extract_svoa(root, sentence, source_doc, sentence_id)


def _extract_copular(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> Fact | None:
    """Extract copular/attributive propositions such as ``X is Y``."""
    predicate = _get_copular_predicate(root)

    # Some spaCy parses expose the copular verb as the root; others make the
    # complement the root and attach the copula with ``cop``. A few model
    # configurations are less consistent about the exact dependency labels,
    # so first locate the actual lexical copular token in the sentence.
    if predicate is root and root.lemma_.lower() not in _COPULAR_VERBS:
        predicate = next(
            (token for token in sentence if token.lemma_.lower() in _COPULAR_VERBS),
            root,
        )

    subject = _get_subject(predicate)
    if not subject:
        subject = _get_subject_from_sentence(root, sentence)

    # Complement-root parses can attach the subject to the complement rather
    # than the copular predicate.
    if not subject and predicate is not root:
        subject = _get_subject(root)

    if not subject:
        return None

    verb = _get_verb_phrase(predicate, include_negation=False)
    negated = _is_negated(predicate) or (predicate is not root and _is_negated(root))

    modality = _get_modality(predicate, sentence)
    attributed_to = _get_attribution(predicate)
    adjuncts = _extract_adjuncts(predicate)

    comp_text = None

    # Standard parse: X is [attribute/adjective/xcomp].
    for child in predicate.children:
        if child.dep_ in {"attr", "acomp", "xcomp", "oprd"}:
            comp_text = _get_span_text(child)
            break

    # Complement-root parse: [feasible] is ROOT with the copula attached to it.
    if not comp_text and predicate is not root:
        comp_text = root.text

    # Prepositional copular complement: X is [on the table].
    if not comp_text:
        for child in predicate.children:
            if child.dep_ == "prep":
                comp_text = _get_prepositional_phrase(child)
                break

    # If the parser attaches the complement directly to the root, recover it
    # from a non-subject, non-copular child.
    if not comp_text:
        for child in root.children:
            if child is predicate:
                continue
            if child.dep_ in {"attr", "acomp", "xcomp", "oprd"}:
                comp_text = _get_span_text(child)
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


def _extract_svoa(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> Fact | None:
    """Extract a standard Subject-Verb-Object-Adjunct proposition."""
    subject = _get_subject_from_sentence(root, sentence)
    if not subject:
        return None

    verb = _get_verb_phrase(root)
    negated = _is_negated(root)
    modality = _get_modality(root, sentence)
    attributed_to = _get_attribution(root)
    adjuncts = _extract_adjuncts(root)

    obj_text = _get_object(root)

    # Passive: the test/schema treats the by-agent as the object when no
    # direct object exists, e.g. "The bill was approved by parliament."
    if not obj_text and _is_passive(root):
        obj_text = _get_agent(root) or ""

    # Existential constructions can expose the semantic noun through attr.
    if not obj_text:
        for child in root.children:
            if child.dep_ in {"ccomp", "xcomp"}:
                obj_text = _get_span_text(child)
                break

    if not obj_text:
        for child in root.children:
            if child.dep_ == "prep":
                pobj = _get_prepositional_object(child)
                if pobj:
                    obj_text = _get_span_text(pobj)
                    break

    # Enrich ditransitive facts instead of creating a duplicate proposition.
    recipient = _get_recipient(root)
    if recipient:
        adjuncts.setdefault("recipient", []).append(recipient)

    return _build_fact(
        subject=subject,
        verb=verb,
        object=obj_text or "",
        adjuncts=adjuncts,
        negated=negated,
        modality=modality,
        attributed_to=attributed_to,
        source_doc=source_doc,
        sentence_id=sentence_id,
        raw_sentence=sentence.text,
    )


# ---------------------------------------------------------------------------
# Coordination extraction
# ---------------------------------------------------------------------------


def _extract_coordination(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """Extract additional facts from coordinated subjects, verbs, or objects."""
    facts: list[Fact] = []

    for conj in (token for token in sentence if token.dep_ == "conj"):
        head = conj.head

        # Coordinated subjects: "John and Mary ate pizza"
        if head.dep_ in {"nsubj", "nsubjpass"}:
            verb = head.head if head.head.pos_ in {"VERB", "AUX"} else root
            if verb.pos_ not in {"VERB", "AUX"}:
                continue

            subject = _get_span_text(conj)
            object_text = _get_object(verb) or ""
            if not object_text and _is_passive(verb):
                object_text = _get_agent(verb) or ""

            adjuncts = _extract_adjuncts(verb)
            recipient = _get_recipient(verb)
            if recipient:
                adjuncts.setdefault("recipient", []).append(recipient)

            facts.append(
                _build_fact(
                    subject=subject,
                    verb=_get_verb_phrase(verb),
                    object=object_text,
                    adjuncts=adjuncts,
                    negated=_is_negated(verb),
                    modality=_get_modality(verb, sentence),
                    attributed_to=_get_attribution(verb),
                    source_doc=source_doc,
                    sentence_id=sentence_id,
                    raw_sentence=sentence.text,
                )
            )

        # Coordinated verbs: "John ran and swam"
        elif head.pos_ in {"VERB", "AUX"} and head == root:
            subject = _get_subject(head) or _get_subject(root)
            if not subject:
                continue

            object_text = _get_object(conj) or ""
            adjuncts = _extract_adjuncts(conj)
            recipient = _get_recipient(conj)
            if recipient:
                adjuncts.setdefault("recipient", []).append(recipient)

            facts.append(
                _build_fact(
                    subject=subject,
                    verb=_get_verb_phrase(conj),
                    object=object_text,
                    adjuncts=adjuncts,
                    negated=_is_negated(conj) or _is_negated(head),
                    modality=_get_modality(conj, sentence),
                    attributed_to=_get_attribution(conj),
                    source_doc=source_doc,
                    sentence_id=sentence_id,
                    raw_sentence=sentence.text,
                )
            )

        # Coordinated objects: "John ate pizza and pasta"
        elif head.dep_ in {"obj", "dobj"}:
            verb = head.head
            if verb.pos_ not in {"VERB", "AUX"}:
                continue

            subject = _get_subject(verb)
            if not subject:
                continue

            adjuncts = _extract_adjuncts(verb)
            recipient = _get_recipient(verb)
            if recipient:
                adjuncts.setdefault("recipient", []).append(recipient)

            facts.append(
                _build_fact(
                    subject=subject,
                    verb=_get_verb_phrase(verb),
                    object=_get_span_text(conj),
                    adjuncts=adjuncts,
                    negated=_is_negated(verb),
                    modality=_get_modality(verb, sentence),
                    attributed_to=_get_attribution(verb),
                    source_doc=source_doc,
                    sentence_id=sentence_id,
                    raw_sentence=sentence.text,
                )
            )

    return facts


# ---------------------------------------------------------------------------
# Relative clause extraction
# ---------------------------------------------------------------------------


def _extract_relative_clauses(
    sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """Extract explicit and reduced relative-clause propositions."""
    facts: list[Fact] = []

    for token in sentence:
        if token.dep_ not in {"relcl", "acl"}:
            continue

        # acl is broad. Restrict this path to participial reduced relatives.
        if token.dep_ == "acl" and token.tag_ not in {"VBN", "VBG"}:
            continue

        antecedent = token.head
        antecedent_text = _get_antecedent_text(antecedent, reduced=token.dep_ == "acl")
        verb = _get_verb_phrase(token)
        negated = _is_negated(token)
        modality = _get_modality(token, sentence)
        adjuncts = _extract_adjuncts(token)

        object_text = _get_object(token) or ""

        if not object_text:
            for child in token.children:
                if child.dep_ in {"attr", "acomp", "xcomp", "ccomp"}:
                    object_text = _get_span_text(child)
                    break

        # Passive relative: "the man who was killed by police"
        if _is_passive(token):
            agent = _get_agent(token)
            if agent:
                facts.append(
                    _build_fact(
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
                )
                continue

        facts.append(
            _build_fact(
                subject=antecedent_text,
                verb=verb,
                object=object_text,
                adjuncts=adjuncts,
                negated=negated,
                modality=modality,
                source_doc=source_doc,
                sentence_id=sentence_id,
                raw_sentence=sentence.text,
            )
        )

    return facts


# ---------------------------------------------------------------------------
# Clausal complement extraction
# ---------------------------------------------------------------------------


def _extract_clausal_complements(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """Extract propositions embedded as ccomp/xcomp clauses."""
    facts: list[Fact] = []

    for child in root.children:
        if child.dep_ not in {"ccomp", "xcomp"}:
            continue

        if child.dep_ == "ccomp":
            subject = _get_subject(child) or _get_subject(root) or ""
        else:
            subject = _get_subject(root) or ""

        if not subject:
            continue

        facts.append(
            _build_fact(
                subject=subject,
                verb=_get_verb_phrase(child),
                object=_get_object(child) or "",
                adjuncts=_extract_adjuncts(child),
                negated=_is_negated(child)
                or (_is_negated(root) if child.dep_ == "xcomp" else False),
                modality=_get_modality(child, sentence),
                attributed_to=_get_attribution(child),
                source_doc=source_doc,
                sentence_id=sentence_id,
                raw_sentence=sentence.text,
            )
        )

    return facts


# ---------------------------------------------------------------------------
# Ditransitive helpers
# ---------------------------------------------------------------------------


def _extract_ditransitive(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """Compatibility helper for ditransitive detection.

    Ditransitive information is now attached to the primary fact through the
    ``recipient`` adjunct, so emitting another Fact here would duplicate the
    same proposition.
    """
    return []


def _get_recipient(root: Token) -> str | None:
    """Return the indirect recipient of a ditransitive verb."""
    direct_object = next(
        (child for child in root.children if child.dep_ in {"obj", "dobj"}),
        None,
    )

    # Preferred spaCy representation for "gave Mary a book".
    for child in root.children:
        if child.dep_ in {"dative", "iobj"}:
            return _get_span_text(child)

    # Some parses attach both nominal arguments as obj. In that case, choose
    # the nominal argument that occurs before the direct object.
    if direct_object is not None:
        candidates = [
            child
            for child in root.children
            if child.dep_ in {"obj", "dobj"}
            and child != direct_object
            and child.i < direct_object.i
        ]
        if candidates:
            return _get_span_text(candidates[-1])

    # Handle the prepositional variant: "gave a book to Mary".
    for child in root.children:
        if child.dep_ == "prep" and child.text.lower() == "to":
            pobj = _get_prepositional_object(child)
            if pobj:
                return _get_span_text(pobj)

    return None


# ---------------------------------------------------------------------------
# Lexical / predicate helpers
# ---------------------------------------------------------------------------


def _is_copular(root: Token) -> bool:
    """Return whether the root is a copular/attributive predicate."""
    if root.lemma_.lower() in _COPULAR_VERBS:
        return True

    # Only dependency structure identifies a child as the copula here.
    # Looking at every child lemma is unsafe: in
    # ``She claimed that the data was incorrect``, the ``was`` token is a
    # ccomp child, not part of the main copular predicate.
    return any(child.dep_ in {"attr", "acomp", "cop"} for child in root.children)


def _get_copular_predicate(root: Token) -> Token:
    """Return the lexical copular predicate when the complement is sentence root."""
    if root.lemma_.lower() in _COPULAR_VERBS:
        return root

    for child in root.children:
        if child.dep_ == "cop" or child.lemma_.lower() in _COPULAR_VERBS:
            return child

    return root


def _is_passive(root: Token) -> bool:
    """Return whether a predicate is syntactically passive."""
    return any(
        child.dep_ in {"nsubjpass", "auxpass", "agent"} for child in root.children
    ) or any(
        child.dep_ == "prep" and child.text.lower() == "by" for child in root.children
    )


def _is_negated(root: Token) -> bool:
    """Return whether the predicate or its core argument is negated."""
    for child in root.children:
        if child.dep_ == "neg":
            return True
        if child.text.lower() in _NEGATION_CUES:
            return True
        if child.dep_ in {"aux", "auxpass"} and child.text.lower().endswith("n't"):
            return True

    if any(
        token.text.lower() in {"not", "never", "neither", "nor"}
        for token in root.subtree
    ):
        return True

    # "There is no evidence" and ordinary "no + noun" constructions.
    for child in root.children:
        if child.dep_ in {"obj", "attr", "nsubj", "nsubjpass"}:
            for grandchild in child.children:
                if grandchild.dep_ == "det" and grandchild.text.lower() == "no":
                    return True

    return False


# ---------------------------------------------------------------------------
# Span helpers
# ---------------------------------------------------------------------------


def _get_span_text(token: Token) -> str:
    """Return the text spanned by a token's dependency subtree."""
    if token is None:
        return ""

    start = token.left_edge.i
    end = token.right_edge.i + 1
    return token.doc[start:end].text.strip()


def _get_prepositional_phrase(preposition: Token) -> str:
    """Return the complete prepositional phrase."""
    return _get_span_text(preposition)


def _get_prepositional_object(preposition: Token) -> Token | None:
    """Return the object of a preposition across spaCy dependency variants."""
    for child in preposition.children:
        if child.dep_ in {"pobj", "obj"}:
            return child
    return None


def _get_antecedent_text(token: Token, reduced: bool = False) -> str:
    """Return the noun phrase modified by a relative clause."""
    if not reduced:
        return _get_span_text(token)

    # For reduced relatives, exclude the acl itself from the antecedent span.
    start = token.left_edge.i
    end = token.i + 1
    return token.doc[start:end].text.strip()


# ---------------------------------------------------------------------------
# Argument helpers
# ---------------------------------------------------------------------------


def _get_subject_from_sentence(root: Token, sentence: Span) -> str | None:
    """Find a subject even when the parser attaches it to the complement."""
    subject = _get_subject(root)
    if subject:
        return subject

    # Complement-root copular parses can put the nsubj on the complement
    # while the copular verb is a ``cop`` child.
    for token in sentence:
        if token.dep_ in {"nsubj", "nsubjpass", "csubj", "csubjpass"}:
            return _get_span_text(token)

    return None


def _get_subject(root: Token) -> str | None:
    """Return the grammatical/semantic subject of a predicate."""
    for child in root.children:
        if child.dep_ in {"nsubj", "nsubjpass", "csubj", "csubjpass"}:
            return _get_span_text(child)

    # Existential construction: "There is no evidence..."
    for child in root.children:
        if child.dep_ == "attr" and child.pos_ in {"NOUN", "PROPN", "PRON"}:
            return _get_span_text(child)

    return None


def _get_object(root: Token) -> str | None:
    """Return the direct object of a predicate."""
    for child in root.children:
        if child.dep_ in {"obj", "dobj"}:
            return _get_span_text(child)
    return None


def _get_agent(root: Token) -> str | None:
    """Return the agent of a passive construction."""
    for child in root.children:
        if child.dep_ == "agent":
            pobj = _get_prepositional_object(child)
            if pobj:
                return _get_span_text(pobj)

        if child.dep_ == "prep" and child.text.lower() == "by":
            pobj = _get_prepositional_object(child)
            if pobj:
                return _get_span_text(pobj)

    return None


# ---------------------------------------------------------------------------
# Predicate helpers
# ---------------------------------------------------------------------------


def _get_verb_phrase(root: Token, *, include_negation: bool = True) -> str:
    """Return the predicate verb phrase in surface order."""
    tokens = {root}

    # Auxiliaries and negation.
    for child in root.children:
        if (
            child.dep_ in {"aux", "auxpass"}
            or include_negation
            and (child.dep_ == "neg" or child.text.lower() in _NEGATION_CUES)
        ):
            tokens.add(child)

    # Particles. ``off`` is unambiguous enough to include even when spaCy
    # attaches the following object beneath the particle.
    for child in root.children:
        if child.dep_ == "prt" or child.dep_ == "prep" and child.text.lower() == "off":
            tokens.add(child)

    # Passive parses can make the finite auxiliary the ROOT and the lexical
    # participle an ``obj`` or another non-aux child. Recover that participle.
    if root.lemma_.lower() in {"be", "have", "do"}:
        for child in root.children:
            if (
                child.pos_ in {"VERB", "AUX"}
                and child.tag_ in {"VBN", "VBG"}
                and child.lemma_.lower() not in _NEGATION_CUES
            ):
                tokens.add(child)

    return " ".join(token.text for token in sorted(tokens, key=lambda token: token.i))


def _is_phrasal_particle(token: Token) -> bool:
    """Return whether a token is a strong phrasal-verb particle candidate."""
    return token.text.lower() in {
        "off",
        "away",
        "back",
        "down",
        "up",
        "out",
        "over",
        "through",
    }


def _is_bare_particle(token: Token) -> bool:
    """Backward-compatible alias for the old particle helper."""
    return _is_phrasal_particle(token)


# ---------------------------------------------------------------------------
# Adjunct extraction
# ---------------------------------------------------------------------------


def _classify_adjunct(preposition: Token) -> str:
    """Classify a prepositional phrase using entity type before marker fallback."""
    marker = preposition.text.lower()
    pobj = _get_prepositional_object(preposition)

    if pobj is not None:
        span = list(pobj.subtree)

        if any(token.ent_type_ in {"DATE", "TIME"} for token in span):
            return "time"

        if any(token.ent_type_ in {"GPE", "LOC", "FAC"} for token in span):
            return "location"

    if marker in _CAUSAL_MARKERS:
        return "cause"
    if marker in _TEMPORAL_MARKERS:
        return "time"
    if marker in _SPATIAL_MARKERS:
        return "location"

    return "context"


def _extract_adjuncts(root: Token) -> dict[str, list[str]]:
    """Extract temporal, spatial, causal, contextual, and manner adjuncts."""
    adjuncts: dict[str, list[str]] = {}

    for child in root.children:
        if child.dep_ == "prep":
            # A passive "by" phrase is the agent, not an adjunct.
            if child.text.lower() == "by" and _is_passive(root):
                continue

            category = _classify_adjunct(child)
            phrase = _get_prepositional_phrase(child)
            adjuncts.setdefault(category, []).append(phrase)
            continue

        if child.dep_ in {"advmod", "npadvmod"}:
            if child.ent_type_ in {"DATE", "TIME"}:
                adjuncts.setdefault("time", []).append(child.text)
                continue

            if child.dep_ == "neg":
                continue

            adjuncts.setdefault("manner", []).append(child.text)
            continue

        if child.dep_ == "advcl":
            adjuncts.setdefault("context", []).append(_get_span_text(child))
            continue

        if child.dep_ == "amod" and child.head == root:
            adjuncts.setdefault("manner", []).append(child.text)

    return adjuncts


# ---------------------------------------------------------------------------
# Modality / attribution
# ---------------------------------------------------------------------------


def _get_modality(root: Token, sentence: Span) -> str:
    """Return the coarse epistemic/status modality of a proposition."""
    conditional_markers = {
        marker for marker in _CONDITIONAL_MARKERS if " " not in marker
    }

    if any(
        token.text.lower() in conditional_markers
        and token.dep_ in {"mark", "advmod", "prep", "cc"}
        for token in sentence
    ):
        return "conditional"

    if root.lemma_.lower() in _REPORTING_VERBS:
        return "attributed"

        # Only attribute when a reporting predicate is actually part of the
        # current proposition, rather than because an unrelated subordinate
        # clause happens to contain one.
    if any(token.lemma_.lower() in _REPORTING_VERBS for token in sentence) and any(
        token.lemma_.lower() in _REPORTING_VERBS
        and (token is root or token.head is root or root.head is token)
        for token in sentence
    ):
        return "attributed"

    if any(
        child.dep_ in {"aux", "auxpass"} and child.lemma_.lower() in _MODAL_VERBS
        for child in root.children
    ):
        return "hypothetical"

    if root.lemma_.lower() in _MODAL_VERBS:
        return "hypothetical"

    return "asserted"


def _get_attribution(root: Token) -> str | None:
    """Return the source of a proposition introduced by a reporting verb."""
    if root.lemma_.lower() not in _REPORTING_VERBS:
        return None
    return _get_subject(root)


# ---------------------------------------------------------------------------
# Fact construction / cleanup
# ---------------------------------------------------------------------------


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
    """Construct a Fact with consistent defaults."""
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


def _deduplicate_facts(facts: list[Fact]) -> list[Fact]:
    """Remove exact duplicate facts while preserving extraction order."""
    seen: set[tuple] = set()
    result: list[Fact] = []

    for fact in facts:
        key = (
            fact.subject,
            fact.verb,
            fact.object,
            tuple(sorted((key, tuple(value)) for key, value in fact.adjuncts.items())),
            fact.negated,
            fact.modality,
            fact.attributed_to,
            fact.sentence_id,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(fact)

    return result
