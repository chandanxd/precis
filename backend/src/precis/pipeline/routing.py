"""
Précis: Deterministic Intent Router.

Classifies incoming queries into logical paths:
- CONVERSATIONAL: greetings, small talk, pleasantries, assistant identity.
- GENERAL_KNOWLEDGE: questions requesting general concept explanations, programming help, etc.
- DOCUMENT_GROUNDED: queries asking about uploaded document content, tables, entities, or facts.
- AMBIGUOUS: under-specified queries with deictic references where intent depends on context.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from precis.pipeline.history import ChatMessage


class QueryIntent(str, Enum):
    """Intent categories for query routing."""

    CONVERSATIONAL = "conversational"
    GENERAL_KNOWLEDGE = "general_knowledge"
    DOCUMENT_GROUNDED = "document_grounded"
    AMBIGUOUS = "ambiguous"


# A greeting/pleasantry may be followed by at most three more words, and only
# if they are not a question or a request ("Hi, what did the report say?").
_NOT_SOCIAL = (
    r"(?:what|who|how|why|when|where|which|tell|show|list|give|explain|"
    r"summari[sz]e|find|can|could|does|do|did|is|are|was|were|please)"
)
_SOCIAL_TAIL = (
    r"([\s!.,?]+(?!.*\?)(?!" + _NOT_SOCIAL + r"\b)([\w']+[\s!.,?]*){0,3})?$"
)

# Exact or prefix greeting patterns
GREETING_PATTERNS = [
    r"^(hi|hello|hey|howdy|greetings|good\s+(morning|afternoon|evening|day))" + _SOCIAL_TAIL,
    r"^((hi|hello|hey)(\s+there)?[\s!.,]+)?(how(\s+are|\'s|\s+is)\s+you(\s+doing)?(\s+today)?|how('s|\s+is)\s+it\s+going|what('s|\s+is)\s+up)[\s!.,?]*$",
    r"^(who(\s+are|\'s|\s+is)\s+you|what(\s+are|\'s|\s+is)\s+you|what(\s+is|\'s|\'re)\s+your\s+name|what('s|\s+is)\s+your\s+name|tell\s+me\s+about\s+yourself)[\s!.,?]*$",
    r"^(what(\s+is|\'s)\s+your\s+(favorite|preferred|role|opinion)[\w\s]*)[\s!.,?]*$",
    r"^(can\s+you\s+hear\s+me|are\s+you\s+(there|online|an\s+ai))[\s!.,?]*$",
]

# Gratitude & pleasantry patterns
PLEASANTRY_PATTERNS = [
    r"^(thanks|thank\s+you(\s+very\s+much|\s+so\s+much)?|thx)" + _SOCIAL_TAIL,
    r"^(thanks,\s*that\s+helped|that\s+helped(\s+a\s+lot)?|great,\s*thanks)[\s!.,?]*$",
    r"^(bye|goodbye|see\s+you(\s+later)?|farewell|have\s+a\s+nice\s+day)[\s!.,?]*$",
    r"^(cool|awesome|nice|ok|okay|got\s+it|understood|sounds\s+good)" + _SOCIAL_TAIL,
    r"^(lol|haha+|hehe|lmao|wow|oops|hmm+|yay|good\s+night)" + _SOCIAL_TAIL,
]

# Casual requests and small talk that never need the documents, even when
# documents are ingested ("tell me a joke", "help me write an email").
CASUAL_REQUEST_PATTERNS = [
    r"^((can|could|would|will)\s+you\s+)?(please\s+)?(tell|give)\s+me\s+(a|an|another|one\s+more)\s+(joke|fun\s+fact|riddle|quote|pun)\b",
    r"^((can|could|would|will)\s+you\s+)?(please\s+)?(write|compose)\s+(me\s+)?(a|an)\s+(poem|story|song|haiku|limerick|joke|rap)\b",
    r"^((can|could|would|will)\s+you\s+)?(please\s+)?help\s+me\s+(write|draft|compose|plan|brainstorm)\b",
    r"^(what\s+can\s+you\s+do|what\s+are\s+you\s+capable\s+of|how\s+can\s+you\s+help(\s+me)?)\b",
    r"^(how('s|\s+is|\s+was)\s+your\s+(day|week|weekend|morning|evening))\b",
    r"^(do\s+you\s+(like|love|enjoy|dream|have\s+feelings))\b",
    r"^(i('m|\s+am)\s+(bored|tired|sad|happy|stressed|excited|back|fine|good|great|okay|ok))\b",
]

# Explicit document markers: queries containing these ALWAYS target documents
DOCUMENT_EXPLICIT_MARKERS = [
    r"\b(in|from|according\s+to|of)\s+(the|this|that|these|our)\s+(document|doc|text|file|report|pdf|passage|article|data|table|chart|list)\b",
    r"\b(uploaded|ingested|attached|provided)\s+(document|doc|text|file|table|data)\b",
    r"\b(the|this|that)\s+(document|report|file|text|table|article|chart|list)\s+(states|says|mentions|shows|reports|contains)\b",
    r"\b(what\s+does\s+(the|this|that)\s+(document|report|file|text|table|article|chart|list)\s+(state|say|mention|show|report|contain))\b",
    r"\b(what\s+is\s+in\s+the\s+(document|file|report|table))\b",
]

# Ambiguous deictic patterns (e.g. "What do you think about this?", "Why do you like it?", "What about it?")
AMBIGUOUS_DEICTIC_PATTERNS = [
    r"^(what\s+do\s+you\s+think\s+about\s+(this|that|it)|tell\s+me\s+more(\s+about\s+(this|that|it))?)[\s!.,?]*$",
    r"^(why\s+do\s+you\s+(like|prefer|think|choose)\s+(it|this|that))[\s!.,?]*$",
    r"^(what\s+about\s+(it|this|that)|and\s+then\?|why\s+(is\s+that|so)\?)[\s!.,?]*$",
    r"^(explain\s+(this|that|it)|elaborate(\s+on\s+(this|that|it))?)[\s!.,?]*$",
]

# Generic "what is / who is" style questions. These are only treated as general
# knowledge when no documents are ingested; otherwise they may be about the
# documents and must go through retrieval.
GENERIC_QUESTION_PATTERNS = [
    r"^(what\s+is\s+(a\s+|an\s+|the\s+)?[\w\s]+)[\s!.,?]*$",
    r"^(what\s+are\s+(a\s+|an\s+|the\s+)?[\w\s]+)[\s!.,?]*$",
    r"^(define\s+[\w\s]+)[\s!.,?]*$",
    r"^(who\s+is\s+[\w\s]+)[\s!.,?]*$",
    r"^(where\s+is\s+[\w\s]+)[\s!.,?]*$",
    r"^(when\s+was\s+[\w\s]+)[\s!.,?]*$",
    r"^(why\s+does\s+[\w\s]+)[\s!.,?]*$",
    r"^(how\s+do(es)?\s+[\w\s]+\s+work)[\s!.,?]*$",
    r"^(explain\s+how\s+(a\s+|an\s+|the\s+)?[\w\s]+\s+works?)[\s!.,?]*$",
    r"^(what\s+is\s+the\s+difference\s+between\s+[\w\s]+\s+and\s+[\w\s]+)[\s!.,?]*$",
]

# Unambiguously non-document requests (coding help, textbook trivia).
GENERAL_KNOWLEDGE_PATTERNS = [
    r"^(how\s+do\s+(i|you)\s+[\w\s]+in\s+(python|javascript|typescript|c\+\+|java|rust|go|bash|sql|html|css))[\s!.,?]*$",
    r"^(write\s+(a\s+)?(python|code|script|function|program)\s+(to|that)[\w\s]+)[\s!.,?]*$",
]


def has_explicit_document_marker(query: str) -> bool:
    """True when the query explicitly refers to the uploaded documents."""
    return any(re.search(p, query, re.IGNORECASE) for p in DOCUMENT_EXPLICIT_MARKERS)


def classify_query_intent(
    query: str,
    has_documents: bool = False,
    conversation_history: list[ChatMessage] | None = None,
) -> QueryIntent:
    """
    Classify user query intent into CONVERSATIONAL, GENERAL_KNOWLEDGE,
    DOCUMENT_GROUNDED, or AMBIGUOUS.
    """
    clean = query.strip()
    if not clean:
        return QueryIntent.CONVERSATIONAL

    sub_queries = [q.strip() for q in re.split(r'[?!]+|\.+(?=\s|$)', clean) if q.strip()]
    if not sub_queries:
        sub_queries = [clean]

    # 1. Check explicit document markers
    if has_explicit_document_marker(clean):
        return QueryIntent.DOCUMENT_GROUNDED

    # 2. Check greetings and pleasantries
    for pattern in GREETING_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return QueryIntent.CONVERSATIONAL

    for pattern in PLEASANTRY_PATTERNS + CASUAL_REQUEST_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return QueryIntent.CONVERSATIONAL

    # 3. Check ambiguous deictic references
    for pattern in AMBIGUOUS_DEICTIC_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            if not has_documents:
                # Without documents, resolve to conversational follow-up
                return QueryIntent.CONVERSATIONAL
            # If conversation history exists, inspect the recent turns
            if conversation_history:
                # A follow-up to an answer that was grounded in documents
                # must keep retrieving.
                if conversation_history[-1].role == "assistant" and getattr(
                    conversation_history[-1], "grounded", False
                ):
                    return QueryIntent.DOCUMENT_GROUNDED
                last_turns = " ".join(t.content for t in conversation_history[-2:])
                # If last turn explicitly talked about documents, stay in document path
                if any(re.search(m, last_turns, re.IGNORECASE) for m in DOCUMENT_EXPLICIT_MARKERS):
                    return QueryIntent.DOCUMENT_GROUNDED
                # If last turn was conversational, stay conversational
                return QueryIntent.CONVERSATIONAL
            return QueryIntent.AMBIGUOUS

    # 4. Check general knowledge patterns across sub-queries or full query
    def _is_general(sq: str) -> bool:
        patterns = GENERAL_KNOWLEDGE_PATTERNS
        if not has_documents:
            patterns = GENERIC_QUESTION_PATTERNS + patterns
        return any(re.search(p, sq, re.IGNORECASE) for p in patterns)

    if has_documents:
        # Every part of the query must be clearly non-document.
        general_match = all(_is_general(sq) for sq in sub_queries)
    else:
        general_match = any(_is_general(sq) for sq in sub_queries)

    if general_match:
        return QueryIntent.GENERAL_KNOWLEDGE

    # 5. Without documents there is nothing to retrieve: the model answers
    # from its own knowledge, using the conversation history for follow-ups.
    if not has_documents:
        return QueryIntent.GENERAL_KNOWLEDGE

    # 6. Contextual follow-up check:
    # If a query looks like a short follow-up (e.g. "What about the previous year?", "What about 2022?")
    # and previous history was document-grounded, it should be document grounded.
    if conversation_history:
        if re.search(r"^(what\s+about|how\s+about|and\s+in|and\s+for|what\s+of)\b", clean, re.IGNORECASE):
            return QueryIntent.DOCUMENT_GROUNDED

    # 7. Specific factual and domain questions default to DOCUMENT_GROUNDED;
    # the chat path then checks whether the documents are relevant at all.
    return QueryIntent.DOCUMENT_GROUNDED
