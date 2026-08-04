# Model Card — PawPal+ RAG Assistant

This is where I write up how I tested the AI feature and think through the responsible
side of it: what it can't do, how it could go wrong, and how I worked with AI to build it.

- **System:** PawPal+, my pet-care planner, plus a RAG assistant
- **AI part:** `rag.py` — offline TF-IDF retrieval over a small pet-care knowledge base
- **What it's for:** answering routine pet-care questions and suggesting care tasks
- **What it's not for:** diagnosing anything, emergencies, or real medical advice

---

## Reliability & Evaluation

I tested the AI three ways instead of just eyeballing it: automated tests, a confidence
score on every answer, and logging so I can see what it actually did.

### Automated tests

`python -m pytest` runs 19 tests (`tests/test_pawpal.py` and `tests/test_rag.py`) and
they all pass. They check that retrieval finds the right section, that every guardrail
fires, that bad suggestion lines get skipped, and that a suggested task actually makes it
into the scheduler.

### Confidence score

Every answer comes back with a confidence number, which is just the cosine similarity of
the best-matching section (0 to 1). On-topic questions land clearly above my `0.05`
cutoff, and off-topic ones drop to basically 0 and get turned away. I show the number in
the app and write it to the log.

### Evaluation harness

I wrote `evaluate.py` so I could run a set of questions I already know the right answer
for and see how many the AI gets right. Here's the latest run:

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

### Short summary

9 out of 10 evaluation cases passed, and all 19 unit tests passed. Confidence on the
grounded answers averaged about 0.27. The one it got wrong was "what is the best stock
to invest in?" — it should have said "I don't know" but instead matched a pet-care
section because both contained the word "best." Every safety guardrail worked, and every
real pet question got a grounded answer with a source. Honestly the app got more reliable
after I added the low-confidence guardrail and the eval script, because that's what
showed me the keyword problem in the first place.

### Logging and error handling

Everything the AI does gets logged to `pawpal.log`: the question, what it pulled up and
the scores, which guardrail fired, and how many tasks it suggested. I also wrapped the
entry points in try/except, so if something breaks (like a missing file) the user just
gets a message instead of the whole app crashing.

---

## Limitations and Biases

- It matches on words, not meaning. It's TF-IDF, so if you ask a question using totally
  different words than my docs use, it might miss it. And like the test above shows, it
  can match the wrong thing just because a common word overlaps.
- It only knows what's in my knowledge base. Right now that's five files covering dogs
  and cats and normal everyday care. It doesn't know anything about other animals, breed
  or age specifics, or anything I didn't write down. So there's a bias toward whatever I
  happened to include.
- The answers are copied straight from the docs, so sometimes you get a whole section
  when only part of it actually answers the question.
- A high confidence score just means the words matched well. It does not mean the advice
  is right for someone's specific pet.

---

## Could It Be Misused, and How I'd Prevent That

- Someone might lean on it instead of calling a vet. To handle that, I check for
  emergency words (bleeding, poison, seizure, choking, and so on) and send them straight
  to a vet before doing any lookup. Every normal answer also says it's general guidance,
  not veterinary advice, and if the app isn't confident it says "I don't know" instead of
  guessing.
- Since the answers come from my knowledge files, someone could edit those files to make
  it give bad advice. To make that harder to hide, the files are tracked in git, every
  answer says which file it came from so you can check it, and suggested tasks get
  validated (real duration, known category) before they're used.
- The confidence number could make it look more sure of itself than it is. That's why I'm
  spelling out here that it's just a word-similarity score, not a promise that the answer
  is correct.

---

## What Surprised Me While Testing

The thing that surprised me most was how easily an off-topic question got through. I
figured something like "what is the best stock to invest in?" would score basically zero,
but it came back at 0.19 and gave a real answer, all because the word "best" shows up in
"Pets do best with a steady routine." It made me realize a guardrail isn't actually safe
until you try to break it on purpose, and that a confidence score is about matching
words, not understanding the question. If I hadn't written the eval script I never would
have noticed.

---

## How I Worked With AI

I used an AI assistant (Claude) the whole way through — to help me pick which of the four
AI features made sense, to build the RAG feature, and to help with tests and docs. I made
the actual decisions and checked its work by running the tests, reading the log, and
trying to trip up the guardrails myself.

- **A time it helped:** when I couldn't decide whether to jam the RAG code into my
  existing files or keep it separate, it talked me through why keeping `pawpal_system.py`
  from importing `rag.py` at all — and just passing suggestions across as plain data
  through a small `add_suggested_tasks` method — would keep things cleaner and easier to
  test. That was a better call than my first idea of wiring it all together, and I went
  with it.

- **A time it was wrong:** it set my low-confidence cutoff at 0.05 and told me that was a
  reasonable value. It sounded fine, but it was too low — that's exactly why the "best
  stock" question snuck through and got an answer it should have refused. I only caught it
  when I ran my own eval and saw the FAIL. I decided to leave it documented as a known
  limitation instead of hiding it, and noted that switching to embedding-based search
  would be the real fix later.
