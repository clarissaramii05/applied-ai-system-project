"""Retrieval-Augmented Generation (RAG) for PawPal+.

This module is the app's AI feature. Instead of guessing, PawPal+ *retrieves*
real pet-care guidance from a small local knowledge base (``knowledge/*.md``)
before it answers a question or suggests care tasks. It is fully self-contained:
retrieval uses a pure-Python TF-IDF + cosine-similarity index (standard library
only, no network, no API key, no model download).

Two entry points are used by the rest of the app:

- ``RagAssistant.answer(query)`` -> a grounded, cited answer to a care question.
- ``RagAssistant.suggest_tasks(species)`` -> a list of ``TaskSpec`` suggestions
  parsed from the knowledge base, which the core logic turns into real ``Task``s.

Guardrails and logging wrap every call so the feature fails safe and leaves a
trace of what it did (see ``pawpal.log``).
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
# One module-level logger. We attach handlers once (guarding against re-import
# under Streamlit's re-run model) so we do not duplicate log lines. Everything
# the RAG feature does -- every query, what it retrieved, and which guardrail
# fired -- is logged here and to pawpal.log.

LOG_PATH = Path(__file__).resolve().parent / "pawpal.log"

logger = logging.getLogger("pawpal.rag")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        _file = logging.FileHandler(LOG_PATH, encoding="utf-8")
        _file.setFormatter(_fmt)
        logger.addHandler(_file)
    except OSError:
        # If the log file cannot be opened (e.g. read-only filesystem), keep
        # running with just the console handler rather than crashing the app.
        pass
    _console = logging.StreamHandler()
    _console.setFormatter(_fmt)
    logger.addHandler(_console)
    logger.propagate = False


# --------------------------------------------------------------------------- #
# Configuration / guardrail constants
# --------------------------------------------------------------------------- #

#: Where the knowledge base lives, relative to this file.
DEFAULT_KB_DIR = Path(__file__).resolve().parent / "knowledge"

#: Longest query we will accept, to bound work and reject junk input.
MAX_QUERY_CHARS = 500

#: A retrieval scoring below this cosine similarity is treated as "no good
#: match found" so we answer honestly instead of returning an irrelevant chunk.
MIN_RELEVANCE = 0.05

#: How many chunks to fold into a grounded answer.
DEFAULT_TOP_K = 3

#: Emergency phrases that must never be routed through normal Q&A. If any appear
#: in a query we short-circuit to a "see a vet" message. Kept deliberately broad;
#: a false positive here is safe (it just points the owner to a professional).
EMERGENCY_TERMS = (
    "not breathing", "can't breathe", "cant breathe", "trouble breathing",
    "choking", "seizure", "seizing", "collapsed", "collapse", "unconscious",
    "bleeding", "blood", "poison", "poisoned", "toxic", "swallowed",
    "hit by", "broken bone", "won't wake", "wont wake", "dying", "emergency",
)

#: A tiny stopword list -- enough to stop common words from dominating the
#: TF-IDF match without needing an external corpus.
STOPWORDS = frozenset("""
a an and are as at be by can do does for from get give giving had has have how
i if in into is it its many me my need needs of on or should so than that the
their them then there they this to too use very was we what when where which who
why will with you your
""".split())

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, and drop stopwords."""
    return [tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in STOPWORDS]


# --------------------------------------------------------------------------- #
# Data holders
# --------------------------------------------------------------------------- #

@dataclass
class Chunk:
    """One retrievable section of the knowledge base (a markdown ``##`` block)."""

    source: str          # file name, e.g. "dogs.md" -- used for citations
    title: str           # section heading, e.g. "Exercise and walks"
    text: str            # the section body
    tokens: list[str] = field(default_factory=list, repr=False)


@dataclass
class Retrieved:
    """A chunk paired with its relevance score for a particular query."""

    chunk: Chunk
    score: float


@dataclass
class TaskSpec:
    """A suggested task, grounded in the knowledge base.

    Plain data on purpose: ``rag.py`` stays free of any dependency on the core
    domain classes. ``pawpal_system`` is what turns a ``TaskSpec`` into a real
    ``Task`` (see ``build_tasks_from_specs``), keeping the layers decoupled.
    """

    name: str
    category: str
    duration_minutes: int
    priority: str
    source: str          # which KB file this suggestion came from


@dataclass
class Answer:
    """The result of answering a care question.

    ``guardrail`` names the guardrail that shaped the response, if any:
    ``"emergency"``, ``"empty"``, ``"too_long"``, or ``"low_confidence"``.
    ``sources`` lists the KB files the answer was grounded in.
    """

    text: str
    sources: list[str] = field(default_factory=list)
    guardrail: str | None = None
    grounded: bool = False


# --------------------------------------------------------------------------- #
# The retriever
# --------------------------------------------------------------------------- #

class KnowledgeBase:
    """Loads the markdown docs and builds a TF-IDF index over their sections."""

    def __init__(self, kb_dir: Path | str = DEFAULT_KB_DIR) -> None:
        self.kb_dir = Path(kb_dir)
        self.chunks: list[Chunk] = []
        self._idf: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []  # L2-normalized tf-idf per chunk
        self._load()
        self._index()

    # -- loading ----------------------------------------------------------- #

    def _load(self) -> None:
        """Read every ``*.md`` file and split it into ``##`` sections."""
        if not self.kb_dir.is_dir():
            logger.error("Knowledge base directory not found: %s", self.kb_dir)
            return
        for path in sorted(self.kb_dir.glob("*.md")):
            try:
                raw = path.read_text(encoding="utf-8")
            except OSError as exc:
                logger.error("Could not read %s: %s", path.name, exc)
                continue
            for title, body in self._split_sections(raw):
                text = body.strip()
                if not text:
                    continue
                self.chunks.append(
                    Chunk(source=path.name, title=title, text=text,
                          tokens=_tokenize(f"{title} {text}"))
                )
        logger.info("Loaded %d chunks from %d files in %s",
                    len(self.chunks),
                    len({c.source for c in self.chunks}),
                    self.kb_dir)

    @staticmethod
    def _split_sections(markdown: str) -> list[tuple[str, str]]:
        """Split a doc into (heading, body) pairs on ``##`` headings."""
        sections: list[tuple[str, str]] = []
        current_title = "Overview"
        buffer: list[str] = []
        for line in markdown.splitlines():
            if line.startswith("## "):
                if buffer:
                    sections.append((current_title, "\n".join(buffer)))
                    buffer = []
                current_title = line[3:].strip()
            elif line.startswith("# "):
                continue  # the document title; skip
            else:
                buffer.append(line)
        if buffer:
            sections.append((current_title, "\n".join(buffer)))
        return sections

    # -- indexing ---------------------------------------------------------- #

    def _index(self) -> None:
        """Compute smoothed IDF and an L2-normalized TF-IDF vector per chunk."""
        n = len(self.chunks)
        if n == 0:
            return
        df: Counter[str] = Counter()
        for chunk in self.chunks:
            df.update(set(chunk.tokens))
        # Smoothed idf so a term in every doc still gets a small positive weight.
        self._idf = {term: math.log((1 + n) / (1 + freq)) + 1.0
                     for term, freq in df.items()}
        self._vectors = [self._vectorize(chunk.tokens) for chunk in self.chunks]

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        """Build an L2-normalized TF-IDF vector from a token list."""
        if not tokens:
            return {}
        tf = Counter(tokens)
        vec = {term: count * self._idf.get(term, 0.0) for term, count in tf.items()}
        norm = math.sqrt(sum(w * w for w in vec.values()))
        if norm == 0:
            return {}
        return {term: w / norm for term, w in vec.items()}

    # -- retrieval --------------------------------------------------------- #

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[Retrieved]:
        """Return the ``top_k`` most relevant chunks, best first."""
        query_vec = self._vectorize(_tokenize(query))
        if not query_vec or not self._vectors:
            return []
        scored: list[Retrieved] = []
        for chunk, vec in zip(self.chunks, self._vectors):
            # Cosine similarity: both vectors are already L2-normalized, so the
            # dot product over shared terms is the cosine directly.
            score = sum(weight * vec.get(term, 0.0)
                        for term, weight in query_vec.items())
            if score > 0:
                scored.append(Retrieved(chunk=chunk, score=score))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]


# --------------------------------------------------------------------------- #
# The assistant (guardrails + logging live here)
# --------------------------------------------------------------------------- #

class RagAssistant:
    """Public API for the RAG feature: grounded answers and task suggestions."""

    def __init__(self, kb_dir: Path | str = DEFAULT_KB_DIR) -> None:
        self.kb = KnowledgeBase(kb_dir)

    # -- question answering ------------------------------------------------ #

    def answer(self, query: str, top_k: int = DEFAULT_TOP_K) -> Answer:
        """Answer a care question from the knowledge base, or fail safe.

        Never raises: every failure mode returns an ``Answer`` with a guardrail
        label so the UI can display something sensible and the log records why.
        """
        # Guardrail 1: input validation.
        cleaned = (query or "").strip()
        if not cleaned:
            logger.info("Query rejected (empty).")
            return Answer(text="Please type a pet-care question.",
                          guardrail="empty")
        if len(cleaned) > MAX_QUERY_CHARS:
            logger.info("Query rejected (too long: %d chars).", len(cleaned))
            return Answer(
                text="That question is a bit long. Try asking one thing at a time.",
                guardrail="too_long",
            )

        # Guardrail 2: emergency deflection -- never answer these from the KB.
        hit = self._emergency_hit(cleaned)
        if hit:
            logger.warning("Emergency guardrail triggered by term %r.", hit)
            return Answer(
                text=(
                    "This sounds like it could be an emergency. PawPal+ only "
                    "helps plan routine care and cannot handle urgent health "
                    "problems. Please contact your veterinarian or an emergency "
                    "animal clinic right away."
                ),
                guardrail="emergency",
            )

        # Retrieve.
        try:
            hits = self.kb.retrieve(cleaned, top_k=top_k)
        except Exception:  # pragma: no cover - defensive; retrieval is pure
            logger.exception("Retrieval failed for query %r.", cleaned)
            return Answer(
                text="Something went wrong looking that up. Please try again.",
                guardrail="error",
            )

        # Guardrail 3: low confidence -> answer honestly instead of forcing a
        # weak, possibly irrelevant match.
        if not hits or hits[0].score < MIN_RELEVANCE:
            best = round(hits[0].score, 4) if hits else 0.0
            logger.info("No confident match for %r (best score %s).", cleaned, best)
            return Answer(
                text=(
                    "I don't have guidance on that in my pet-care notes. I can "
                    "help with feeding, walks and exercise, grooming, litter, and "
                    "general routine care for dogs and cats."
                ),
                guardrail="low_confidence",
            )

        # Ground the answer in retrieved text (extractive -- no invented facts).
        sources = list(dict.fromkeys(h.chunk.source for h in hits))
        logger.info(
            "Answered %r using %s (top score %.4f).",
            cleaned,
            ", ".join(f"{h.chunk.source}#{h.chunk.title}" for h in hits),
            hits[0].score,
        )
        return Answer(
            text=self._compose(hits),
            sources=sources,
            grounded=True,
        )

    @staticmethod
    def _emergency_hit(query: str) -> str | None:
        """Return the first emergency term found in the query, or None."""
        low = query.lower()
        for term in EMERGENCY_TERMS:
            if term in low:
                return term
        return None

    @staticmethod
    def _compose(hits: list[Retrieved]) -> str:
        """Build a readable, cited answer purely from retrieved KB text."""
        parts = []
        for h in hits:
            parts.append(f"**{h.chunk.title}** ({h.chunk.source})\n{h.chunk.text}")
        body = "\n\n".join(parts)
        return (
            f"{body}\n\n"
            "_Grounded in PawPal+'s pet-care notes. This is general guidance, "
            "not veterinary advice._"
        )

    # -- task suggestions -------------------------------------------------- #

    def suggest_tasks(self, species: str) -> list[TaskSpec]:
        """Return suggested care tasks for a species, grounded in the KB.

        Reads the ``## Suggested daily tasks`` block from the matching species
        doc and parses its ``name | category | minutes | priority`` lines. If
        there is no doc for the species, returns an empty list (the caller
        decides how to message that) rather than inventing tasks.
        """
        doc = self._species_doc(species)
        if doc is None:
            logger.info("No suggestion doc for species %r.", species)
            return []

        specs: list[TaskSpec] = []
        for chunk in self.kb.chunks:
            if chunk.source != doc or "suggested" not in chunk.title.lower():
                continue
            for line in chunk.text.splitlines():
                spec = self._parse_task_line(line, source=doc)
                if spec is not None:
                    specs.append(spec)
        logger.info("Suggested %d task(s) for species %r from %s.",
                    len(specs), species, doc)
        return specs

    @staticmethod
    def _species_doc(species: str) -> str | None:
        """Map a free-text species to the KB file that covers it."""
        s = (species or "").strip().lower()
        if s in ("dog", "dogs", "puppy", "canine"):
            return "dogs.md"
        if s in ("cat", "cats", "kitten", "feline"):
            return "cats.md"
        return None

    @staticmethod
    def _parse_task_line(line: str, source: str) -> TaskSpec | None:
        """Parse one ``name | category | minutes | priority`` bullet, or None."""
        line = line.strip()
        if not line.startswith("-") or "|" not in line:
            return None
        parts = [p.strip() for p in line.lstrip("-").split("|")]
        if len(parts) != 4:
            logger.warning("Skipping malformed suggestion line: %r", line)
            return None
        name, category, minutes, priority = parts
        try:
            duration = int(minutes)
        except ValueError:
            logger.warning("Skipping suggestion with bad duration: %r", line)
            return None
        if duration <= 0:
            logger.warning("Skipping suggestion with non-positive duration: %r", line)
            return None
        return TaskSpec(
            name=name,
            category=category.lower(),
            duration_minutes=duration,
            priority=priority.lower(),
            source=source,
        )


# A module-level singleton is convenient for the Streamlit app, which re-runs
# top to bottom on every interaction; building the index once and reusing it
# keeps the UI responsive. Callers that want isolation (e.g. tests) can still
# construct their own RagAssistant with a custom kb_dir.
_ASSISTANT: RagAssistant | None = None


def get_assistant() -> RagAssistant:
    """Return a shared RagAssistant, building it on first use."""
    global _ASSISTANT
    if _ASSISTANT is None:
        _ASSISTANT = RagAssistant()
    return _ASSISTANT
