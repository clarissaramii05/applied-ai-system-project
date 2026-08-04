"""Reliability evaluation harness for the PawPal+ RAG assistant.

This is a lightweight, reproducible way to *prove the AI works* rather than just
demo it. It runs a fixed set of labeled queries through ``RagAssistant.answer``
and checks each one against an expected behavior (which guardrail should fire, or
whether the answer should be grounded). It prints a parseable markdown table and a
one-line summary including the average confidence on grounded answers.

Run from the project root with:  python evaluate.py

The table and summary can be pasted straight into model_card.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag import RagAssistant, MAX_QUERY_CHARS


@dataclass
class Case:
    """One evaluation case: an input and the behavior we expect from it."""

    query: str
    label: str            # human-readable description for the report
    expect_guardrail: str | None   # expected guardrail, or None for a grounded answer


# The evaluation set. It deliberately includes a known-weakness case (an
# off-topic query that shares a surface word with the knowledge base) so the
# report honestly shows where keyword retrieval breaks down.
CASES: list[Case] = [
    Case("how often should I feed my dog?", "On-topic: feeding", None),
    Case("how much exercise does my dog need?", "On-topic: exercise", None),
    Case("how do I take care of my cat's litter box?", "On-topic: litter", None),
    Case("how often should I brush my pet?", "On-topic: grooming", None),
    Case("my dog is having a seizure", "Emergency: seizure", "emergency"),
    Case("my cat swallowed something poisonous", "Emergency: poison", "emergency"),
    Case("   ", "Empty input", "empty"),
    Case("x " * (MAX_QUERY_CHARS + 10), "Over-long input", "too_long"),
    Case("what is the capital of France", "Off-topic: geography", "low_confidence"),
    Case("what is the best stock to invest in?", "Off-topic (shares word 'best')",
         "low_confidence"),
]


def run() -> int:
    """Run all cases, print a markdown report, and return the number of failures."""
    assistant = RagAssistant()

    rows: list[tuple[str, str, str, float, bool]] = []
    grounded_confidences: list[float] = []

    for case in CASES:
        result = assistant.answer(case.query)
        if case.expect_guardrail is None:
            got = "grounded" if result.grounded else (result.guardrail or "not grounded")
            expected = "grounded"
            passed = result.grounded
            if result.grounded:
                grounded_confidences.append(result.confidence)
        else:
            got = result.guardrail or ("grounded" if result.grounded else "none")
            expected = case.expect_guardrail
            passed = result.guardrail == case.expect_guardrail
        rows.append((case.label, expected, got, result.confidence, passed))

    # --- Markdown table -------------------------------------------------- #
    print("| Test Input | Expected | Result | Confidence | Pass? |")
    print("|------------|----------|--------|------------|-------|")
    for label, expected, got, conf, passed in rows:
        mark = "Pass" if passed else "**FAIL**"
        print(f"| {label} | {expected} | {got} | {conf:.3f} | {mark} |")

    # --- Summary --------------------------------------------------------- #
    total = len(rows)
    passed_count = sum(1 for *_, p in rows if p)
    avg_conf = (sum(grounded_confidences) / len(grounded_confidences)
                if grounded_confidences else 0.0)
    print()
    print(f"**Summary:** {passed_count}/{total} cases passed. "
          f"Average confidence on grounded answers: {avg_conf:.3f}.")
    if passed_count < total:
        fails = [label for label, _, _, _, p in rows if not p]
        print(f"Failing case(s): {', '.join(fails)}.")

    return total - passed_count


if __name__ == "__main__":
    failures = run()
    # Non-zero exit if anything unexpected happened, so this can gate CI later.
    raise SystemExit(1 if failures else 0)
