"""Tests for the RAG feature and its integration with the core scheduler.

Run from the project root with:  python -m pytest

These cover the three things that make the AI feature trustworthy:
- Retrieval actually finds the right knowledge-base section for a question.
- The guardrails (emergency, empty, over-long, low-confidence) all fire.
- Suggested tasks are parsed correctly and flow through the core Owner hook
  into real Task objects the Scheduler can plan.
"""

from rag import RagAssistant, TaskSpec, MAX_QUERY_CHARS
from pawpal_system import (
    Owner, Pet, Scheduler, Category, Priority,
    build_tasks_from_specs,
)


# A single assistant over the real knowledge base is enough for these tests.
assistant = RagAssistant()


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #

def test_retrieval_finds_relevant_chunk():
    """A feeding question should retrieve a feeding-related section, top-ranked."""
    hits = assistant.kb.retrieve("how often should I feed my dog", top_k=3)
    assert hits, "expected at least one retrieved chunk"
    top = hits[0]
    assert "feed" in (top.chunk.title + top.chunk.text).lower()
    assert top.score > 0


def test_answer_is_grounded_and_cited():
    """A normal question returns a grounded answer that cites a source file."""
    result = assistant.answer("how much exercise does a dog need")
    assert result.grounded is True
    assert result.guardrail is None
    assert result.sources  # at least one .md source cited
    assert all(s.endswith(".md") for s in result.sources)


# --------------------------------------------------------------------------- #
# Guardrails
# --------------------------------------------------------------------------- #

def test_emergency_query_is_deflected():
    """Emergency wording must skip retrieval and point to a vet."""
    result = assistant.answer("my dog is bleeding and not breathing")
    assert result.guardrail == "emergency"
    assert result.grounded is False
    assert "vet" in result.text.lower()


def test_empty_query_guardrail():
    """An empty question is rejected, not sent to the retriever."""
    result = assistant.answer("   ")
    assert result.guardrail == "empty"
    assert result.grounded is False


def test_overlong_query_guardrail():
    """A question past the length cap is rejected safely."""
    result = assistant.answer("x " * (MAX_QUERY_CHARS + 10))
    assert result.guardrail == "too_long"
    assert result.grounded is False


def test_off_topic_query_low_confidence():
    """An unrelated question returns an honest 'I don't know', not a bad match."""
    result = assistant.answer("how do I file my taxes")
    assert result.guardrail == "low_confidence"
    assert result.grounded is False


# --------------------------------------------------------------------------- #
# Task suggestions
# --------------------------------------------------------------------------- #

def test_suggest_tasks_for_dog_returns_specs():
    """Dog suggestions come back grounded in dogs.md with sane fields."""
    specs = assistant.suggest_tasks("dog")
    assert specs, "expected suggested tasks for a dog"
    assert all(isinstance(s, TaskSpec) for s in specs)
    assert all(s.source == "dogs.md" for s in specs)
    assert all(s.duration_minutes > 0 for s in specs)


def test_suggest_tasks_unknown_species_is_empty():
    """An unsupported species yields no suggestions rather than invented ones."""
    assert assistant.suggest_tasks("dragon") == []


def test_parse_task_line_rejects_malformed():
    """A malformed suggestion line is skipped, not turned into a broken spec."""
    assert assistant._parse_task_line("- just a note", source="x.md") is None
    assert assistant._parse_task_line("- a | b | notanumber | high", source="x.md") is None


# --------------------------------------------------------------------------- #
# Integration with the core scheduler (the RAG <-> core seam)
# --------------------------------------------------------------------------- #

def test_specs_convert_to_tasks_via_core_builder():
    """build_tasks_from_specs maps enum strings correctly and skips bad rows."""
    specs = [
        TaskSpec("Walk", "walk", 30, "high", "dogs.md"),
        TaskSpec("Bad", "walk", 0, "high", "dogs.md"),        # zero duration -> skipped
        TaskSpec("Weird", "nonsense", 15, "urgent", "x.md"),  # unknown enums -> defaulted
    ]
    tasks = build_tasks_from_specs(specs)
    assert len(tasks) == 2  # the zero-duration row is dropped
    walk = tasks[0]
    assert walk.category is Category.WALK
    assert walk.priority is Priority.HIGH
    # Unknown category/priority fall back to safe defaults instead of crashing.
    assert tasks[1].category is Category.ENRICHMENT
    assert tasks[1].priority is Priority.MEDIUM


def test_owner_hook_attaches_suggestions_and_they_schedule():
    """Suggestions routed through Owner.add_suggested_tasks become schedulable tasks."""
    owner = Owner("Jordan", available_minutes=60)
    pet = Pet("Mochi", species="dog")
    specs = assistant.suggest_tasks("dog")

    added = owner.add_suggested_tasks(pet, specs)

    assert added, "expected tasks to be added"
    assert pet.list_tasks() == added  # attached to the pet
    # And they flow into the scheduler like any other task.
    scheduler = Scheduler(pet.list_tasks(), owner.available_minutes)
    plan = scheduler.generate_plan(__import__("datetime").date.today())
    assert plan.entries, "suggested tasks should produce a plan"
