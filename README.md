# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

============================================
  Today's Schedule for Jordan
  Saturday, July 11, 2026
============================================
  08:00-08:10  Breakfast          (10 min) [high]
  08:10-08:20  Feed Luna          (10 min) [high]
  08:20-08:50  Morning walk       (30 min) [high]
  08:50-09:15  Play/enrichment    (25 min) [medium]
  09:15-09:30  Nail trim          (15 min) [low]
--------------------------------------------
  Time used: 90 / 90 min
  Skipped (1): Brushing
============================================

Why this plan:
Planning with a 90 minute budget.
Tasks are ordered by priority (high first), then shortest duration.
- Kept Breakfast (10 min, high); 80 min left.
- Kept Feed Luna (10 min, high); 70 min left.
- Kept Morning walk (30 min, high); 40 min left.
- Kept Play/enrichment (25 min, medium); 15 min left.
- Kept Nail trim (15 min, low); 0 min left.
- Skipped Brushing (20 min, low); not enough time left.


## Testing PawPal+ 

Run the full test suite from the project root with:

```bash
python -m pytest
```

**What the tests cover** (`tests/test_pawpal.py`):

- **Task completion** — `mark_done()` flips a task's status to done.
- **Adding tasks** — adding a task to a pet grows that pet's task list.
- **Recurrence logic** — completing a `DAILY` task spawns a new task due the next
  day, a `WEEKLY` task spawns one due seven days later, and a `ONCE` task creates
  no follow-up.
- **Sorting correctness** — `sort_by_time()` returns tasks in chronological order.
- **Conflict detection** — `detect_conflicts()` flags tasks scheduled at the same
  time and reports no conflict when times do not overlap.

Test output:

```
python -m pytest
========================== test session starts ===========================
platform win32 -- Python 3.13.1, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\clari\OneDrive\work\ai110-module2show-pawpal-starter
plugins: anyio-4.14.1
collected 8 items                                                         

tests\test_pawpal.py ........                                       [100%]

=========================== 8 passed in 0.13s ============================
```

**Confidence Level: (4/5)**

All 8 tests pass and they cover the core scheduling behaviors (sorting, recurrence,
conflict detection, task management). I held back the fifth star because the suite
does not yet test edge cases like an empty task list, tasks that are longer than the
whole time budget, or overlapping tasks across different pets, and `generate_plan()`
itself is exercised through `main.py` rather than by an automated test.

## 📐 Smarter Scheduling

Each scheduling feature and the method that implements it (all in `pawpal_system.py`):

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `Scheduler.sort_tasks()` | `sort_by_time()` orders tasks chronologically by their `"HH:MM"` time attribute (zero-padded strings sort in clock order). `sort_tasks()` orders by priority (high first), then shortest duration as a tie-breaker. |
| Filtering | `Owner.filter_by_pet()`, `Owner.filter_by_status()`, `Scheduler.filter_by_time()` | Filter tasks by pet name or completion status, or keep only the tasks that fit inside the time budget. |
| Conflict handling | `Scheduler.detect_conflicts()` | Treats each task as a `[start, start + duration)` interval and flags any that overlap, for the same pet or different pets. Returns a list of warning messages instead of raising, so the app keeps running. |
| Recurring tasks | `Task.mark_done()`, `Task.next_occurrence()` | Completing a `DAILY` or `WEEKLY` task auto-creates the next occurrence with its `due_date` advanced by `timedelta` (one day / one week). `ONCE` tasks do not repeat. |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
