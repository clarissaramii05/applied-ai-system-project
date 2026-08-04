# 🐾 PawPal+ — A Pet-Care Planner with a Retrieval-Augmented AI Assistant

**PawPal+** helps a busy pet owner build a realistic daily care schedule and answer
everyday pet-care questions. It combines a deterministic scheduling engine with a
**Retrieval-Augmented Generation (RAG)** assistant that looks up guidance from a
curated knowledge base before it answers — so its advice is grounded in real notes,
cites its sources, and knows when to say "I don't know" or "see a vet."

**Why it matters:** most scheduling tools are blind — they arrange whatever you type
in without any domain knowledge. PawPal+ adds a knowledge layer that can *suggest* a
sensible starter routine for a species and *explain* care questions, while staying
safe (guardrails), transparent (logging), and honest (grounded, cited answers). It
runs fully offline with no API key.

---

## 📦 Original Project

The foundation is **PawPal+**, my project from Modules 1–3. Its original goal was to
turn a pet owner's list of care tasks (walks, feeding, meds, grooming, enrichment)
into an ordered daily plan that respects a time budget and task priorities, and to
*explain* why it chose that plan. That version — designed from a UML class diagram and
implemented in Python with a Streamlit UI and a pytest suite — already handled task
sorting, time-budget filtering, recurring tasks, and time-conflict detection. This
project extends it with the AI feature described below.

---

## 🧠 What the AI Feature Adds

A fully offline **RAG** feature (`rag.py`) that gives PawPal+ two new abilities:

- **Ask PawPal** — answer routine pet-care questions using retrieved, cited knowledge.
- **Suggest tasks** — propose a grounded starter routine for a dog or cat, which flows
  straight into the existing scheduler as real tasks.

It uses a pure-Python **TF-IDF + cosine-similarity** retriever over markdown docs in
`knowledge/` — no external model, no network, no API key.

---

## 🗺️ Architecture Overview

The system diagram lives in [`diagrams/uml.mmd`](diagrams/uml.mmd); the detailed class
diagram is in [`diagrams/class_diagram.mmd`](diagrams/class_diagram.mmd).

The app is organized in three layers:

1. **UI layer** (`app.py`, Streamlit) — collects owner/pet/task input, hosts the
   *Ask PawPal* box and *Suggest tasks* button, and renders the schedule.
2. **Core logic** (`pawpal_system.py`) — the domain model (`Owner`, `Pet`, `Task`) and
   the `Scheduler`, which sorts tasks by priority, fits them into the time budget, and
   explains its plan. This is unchanged from the original project except for one small,
   dependency-free hook (`Owner.add_suggested_tasks`).
3. **AI layer** (`rag.py`) — loads the `knowledge/` base, retrieves relevant sections,
   applies guardrails, logs activity, and returns grounded answers or task suggestions.

The key design point: **data flows one way and the core stays decoupled.** The AI layer
produces plain suggestion data; the core turns it into `Task` objects. `pawpal_system.py`
imports nothing from `rag.py`, so retrieval, file I/O, and logging stay isolated in the
AI layer while suggestions still feed the same `Scheduler` as hand-entered tasks.

```
knowledge/*.md ──▶ rag.py (retrieve + guardrails + logging)
                        │  answers          │ suggestions (plain data)
                        ▼                    ▼
                     app.py  ◀────────  pawpal_system.py (Owner/Pet/Task ▶ Scheduler)
```

---

## ⚙️ Setup Instructions

**Requirements:** Python 3.10+ (developed on 3.13).

```bash
# 1. Clone and enter the project
git clone https://github.com/clarissaramii05/applied-ai-system-project.git
cd applied-ai-system-project

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the tests (should report all passing)
python -m pytest

# 5. Launch the app
streamlit run app.py
```

The RAG feature needs no extra setup — it is standard-library only and reads the
knowledge base from `knowledge/`. Runtime activity is logged to `pawpal.log`.

---

## 💬 Sample Interactions

These are real outputs from the system. More (including the full test run and log
samples) are in [`assets/execution_evidence.md`](assets/execution_evidence.md).

### 1. Ask PawPal — a grounded, cited answer

```text
Input:  how much exercise does my dog need?

Output (confidence 0.234, grounded):
**Exercise and walks** (dogs.md)
Most adult dogs need at least 30 to 60 minutes of physical activity every day,
usually split across one or two walks. High-energy breeds such as Border Collies,
Huskies, and Shibas often need more ... a daily walk is usually a high priority task.

_Grounded in PawPal+'s pet-care notes. This is general guidance, not veterinary advice._
Sources: dogs.md
```

### 2. Ask PawPal — the emergency guardrail (retrieval skipped)

```text
Input:  my cat swallowed something poisonous

Output (guardrail = emergency):
This sounds like it could be an emergency. PawPal+ only helps plan routine care and
cannot handle urgent health problems. Please contact your veterinarian or an
emergency animal clinic right away.
```

### 3. Suggest tasks — grounded routine that feeds the scheduler

```text
Input:  click "✨ Suggest tasks for a dog"

Output (5 tasks parsed from dogs.md, then scheduled):
  Morning walk       | walk       | 30 min | high
  Breakfast          | feeding    | 10 min | high
  Dinner             | feeding    | 10 min | high
  Play and training  | enrichment | 20 min | medium
  Brushing           | grooming   | 15 min | low
```

### 4. The core scheduler explaining its plan

```text
  08:00-08:10  Breakfast          (10 min) [high]
  08:10-08:20  Feed Luna          (10 min) [high]
  08:20-08:50  Morning walk       (30 min) [high]
  08:50-09:15  Play/enrichment    (25 min) [medium]
  09:15-09:30  Nail trim          (15 min) [low]
  Time used: 90 / 90 min   |   Skipped (1): Brushing

Why this plan: ordered by priority (high first), then shortest duration.
- Kept Morning walk (30 min, high); 40 min left.
- Skipped Brushing (20 min, low); not enough time left.
```

---

## 🧩 Design Decisions & Trade-offs

- **Why RAG (over an agent, a fine-tuned model, or a testing harness)?** RAG added a
  genuinely *new* capability — answering questions and grounding suggestions in real
  knowledge — that the deterministic scheduler could never have, and it did so at a
  scale achievable without training data or an API key. An agentic layer would have
  mostly duplicated the planning the scheduler already does well.
- **Offline TF-IDF instead of an LLM/embeddings.** Trade-off: TF-IDF matches on shared
  *words*, so it can miss questions phrased very differently from the source text. In
  exchange, the app runs anywhere with zero dependencies, zero cost, and no API key —
  the right call for a portfolio project that must "just run."
- **Extractive, cited answers instead of generated prose.** The assistant returns
  retrieved text verbatim with its source. It reads less fluently than an LLM, but it
  *cannot hallucinate* — every sentence is traceable to a knowledge-base file.
- **Decoupled layers.** Keeping `pawpal_system.py` free of any `rag.py` import means the
  core stays testable and the AI feature is swappable. Suggestions cross the boundary as
  plain data through one small hook.
- **Greedy scheduler (inherited).** The scheduler fills the time budget by priority and
  never backtracks. It can occasionally make a locally-suboptimal choice (one 30-min
  high-priority task instead of two 15-min mediums), but it matches how a busy owner
  actually thinks and is easy to explain.

---

## ✅ Testing Summary

Run with `python -m pytest` (**19 tests pass**, `tests/test_pawpal.py` +
`tests/test_rag.py`) and `python evaluate.py` for a reliability report (**9/10 labeled
cases pass**). Full captured outputs are in
[`assets/execution_evidence.md`](assets/execution_evidence.md); the model card is in
[`model_card.md`](model_card.md).

**What works:**
- Core scheduling — sorting, time-budget filtering, recurrence, and conflict detection.
- RAG retrieval returns the correct knowledge-base section for on-topic questions.
- All four guardrails fire: emergency deflection, empty input, over-long input, and
  low-confidence "I don't know."
- Suggestion parsing rejects malformed lines, and suggested tasks flow through the core
  hook into a schedulable plan (the RAG-to-scheduler seam is tested end-to-end).

**What didn't work (yet) — an honest limitation:** because retrieval is keyword-based,
an off-topic query that happens to share a word with the knowledge base can still match.
For example, *"what is the best stock to invest in?"* matched a routine-care section on
the word **"best"** instead of being rejected. A stricter query like *"what is the
capital of France"* is correctly turned away. This is the core weakness of TF-IDF
(surface-word overlap, no semantic understanding) and would be the first thing I'd
address with real embeddings.

**What I learned:** guardrails and logging aren't extras — they're what make an AI
feature *trustworthy*. Testing that the system says "I don't know" and steps aside in an
emergency turned out to matter as much as testing that it gives good answers.

---

## 📝 Reflection

A brief note: the biggest lesson was that "adding AI" is a **design decision**, not just
a code change — choosing RAG over the alternatives and deciding where the boundary
between the AI layer and the core logic should sit mattered more than any single line of
implementation.

My full graded responsible-AI reflection — how I collaborated with AI, one helpful and
one flawed AI suggestion, and the system's limitations — is in
[`model_card.md`](model_card.md).

---

## 🗂️ Project Structure

```
applied-ai-system-final/
├── app.py                 # Streamlit UI (scheduler + Ask PawPal + Suggest tasks)
├── pawpal_system.py       # Core domain model + Scheduler + RAG integration hook
├── rag.py                 # RAG feature: retriever, guardrails, logging
├── knowledge/             # Pet-care knowledge base (markdown)
├── tests/                 # pytest suite (core + RAG)
├── diagrams/              # System diagram (uml.mmd) + class diagram
├── requirements.txt
└── pawpal.log             # Runtime log (git-ignored)
```
