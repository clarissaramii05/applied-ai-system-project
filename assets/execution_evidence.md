# Execution Evidence — PawPal+

Reproducible command outputs and interaction logs, captured from the running system.
Everything here can be regenerated with the commands shown. Environment: Python 3.14,
pytest 9.1.

---

## 1. Test suite — `python -m pytest -v`

```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
rootdir: applied-ai-system-final
collected 19 items

tests/test_pawpal.py::test_task_completion_changes_status PASSED         [  5%]
tests/test_pawpal.py::test_adding_task_increases_pet_task_count PASSED   [ 10%]
tests/test_pawpal.py::test_completing_daily_task_spawns_next_day PASSED  [ 15%]
tests/test_pawpal.py::test_completing_weekly_task_spawns_next_week PASSED [ 21%]
tests/test_pawpal.py::test_one_off_task_does_not_recur PASSED            [ 26%]
tests/test_pawpal.py::test_sort_by_time_returns_chronological_order PASSED [ 31%]
tests/test_pawpal.py::test_detect_conflicts_flags_duplicate_times PASSED [ 36%]
tests/test_pawpal.py::test_detect_conflicts_returns_empty_when_no_overlap PASSED [ 42%]
tests/test_rag.py::test_retrieval_finds_relevant_chunk PASSED            [ 47%]
tests/test_rag.py::test_answer_is_grounded_and_cited PASSED              [ 52%]
tests/test_rag.py::test_emergency_query_is_deflected PASSED              [ 57%]
tests/test_rag.py::test_empty_query_guardrail PASSED                     [ 63%]
tests/test_rag.py::test_overlong_query_guardrail PASSED                  [ 68%]
tests/test_rag.py::test_off_topic_query_low_confidence PASSED            [ 73%]
tests/test_rag.py::test_suggest_tasks_for_dog_returns_specs PASSED       [ 78%]
tests/test_rag.py::test_suggest_tasks_unknown_species_is_empty PASSED    [ 84%]
tests/test_rag.py::test_parse_task_line_rejects_malformed PASSED         [ 89%]
tests/test_rag.py::test_specs_convert_to_tasks_via_core_builder PASSED   [ 94%]
tests/test_rag.py::test_owner_hook_attaches_suggestions_and_they_schedule PASSED [100%]

============================= 19 passed in 0.07s ==============================
```

---

## 2. Reliability evaluation — `python evaluate.py`

```
| Test Input | Expected | Result | Confidence | Pass? |
|------------|----------|--------|------------|-------|
| On-topic: feeding | grounded | grounded | 0.157 | Pass |
| On-topic: exercise | grounded | grounded | 0.234 | Pass |
| On-topic: litter | grounded | grounded | 0.497 | Pass |
| On-topic: grooming | grounded | grounded | 0.192 | Pass |
| Emergency: seizure | emergency | emergency | 0.000 | Pass |
| Emergency: poison | emergency | emergency | 0.000 | Pass |
| Empty input | empty | empty | 0.000 | Pass |
| Over-long input | too_long | too_long | 0.000 | Pass |
| Off-topic: geography | low_confidence | low_confidence | 0.000 | Pass |
| Off-topic (shares word 'best') | low_confidence | grounded | 0.187 | **FAIL** |

Summary: 9/10 cases passed. Average confidence on grounded answers: 0.270.
Failing case(s): Off-topic (shares word 'best').
```

The single FAIL is a documented limitation (keyword retrieval matching the shared word
"best"); see `model_card.md`.

---

## 3. Interaction log — the RAG assistant

Captured by calling `rag.get_assistant()` directly.

### 3a. Grounded, cited answer

```
>>> ask( 'how often should I feed my dog?' )
guardrail = None | grounded = True | confidence = 0.157
**How often to feed** (feeding.md)
Most adult dogs and cats do well on two meals a day, spaced roughly morning and
evening. Young puppies and kittens need more frequent meals, usually three or four
times a day, because their small stomachs cannot hold a full day of food at once.
Older pets can usually stay on two meals a day unless a vet advises otherwise.

**Feeding** (dogs.md)
Adult dogs are typically fed twice a day, in the morning and the evening. Puppies
under six months usually need three or four smaller meals a day ...

_Grounded in PawPal+'s pet-care notes. This is general guidance, not veterinary advice._
sources = ['feeding.md', 'dogs.md']
```

### 3b. Emergency guardrail (retrieval skipped)

```
>>> ask( 'my dog is having a seizure' )
guardrail = emergency | grounded = False | confidence = 0.0
This sounds like it could be an emergency. PawPal+ only helps plan routine care and
cannot handle urgent health problems. Please contact your veterinarian or an
emergency animal clinic right away.
```

### 3c. Grounded task suggestions (feed the scheduler)

```
>>> suggest_tasks("dog")
  Morning walk | walk | 30 min | high  (from dogs.md)
  Breakfast | feeding | 10 min | high  (from dogs.md)
  Dinner | feeding | 10 min | high  (from dogs.md)
  Play and training | enrichment | 20 min | medium  (from dogs.md)
  Brushing | grooming | 15 min | low  (from dogs.md)
```

---

## 4. Log file sample — `pawpal.log`

The RAG feature logs every query, retrieval, guardrail, and suggestion batch:

```
INFO pawpal.rag: Loaded 22 chunks from 5 files in .../knowledge
INFO pawpal.rag: Answered 'how often should I feed my dog?' using feeding.md#How often to feed, dogs.md#Feeding, dogs.md#Enrichment and play (confidence 0.1570).
WARNING pawpal.rag: Emergency guardrail triggered by term 'seizure'.
INFO pawpal.rag: No confident match for 'what is the capital of France' (best score 0.0).
INFO pawpal.rag: Suggested 5 task(s) for species 'dog' from dogs.md.
```
