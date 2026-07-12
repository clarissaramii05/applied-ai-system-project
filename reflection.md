# PawPal+ Project Reflection

## 1. System Design

**Core user actions**

A pet owner using PawPal+ needs to be able to do three main things:

1. Add a pet care task. The owner types in a task like a walk, feeding, meds, enrichment, or grooming, and gives it a duration and a priority. They can also edit the task later if something changes. This is the info the app needs before it can plan anything.

2. Generate a daily plan. Once the tasks are in, the owner asks the app to build a schedule. The scheduler looks at the constraints, like how much time is available and how important each task is, and turns the list of tasks into an ordered daily plan.

3. See today's plan. The owner can look at the finished schedule laid out clearly, with the time, task, duration, and priority for each item. Ideally the app also explains why it picked that order and why it skipped anything when there was not enough time.

These three actions basically form the flow of the whole app, going from input to processing to output, and they shaped how I set up my classes.

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
