# Exam Flashcards Module — Design Spec
**Date:** 2026-05-27
**Project:** theory-terms-quiz (single-file static HTML/CSS/JS app)
**Status:** Approved for implementation

---

## Overview

A new "Exam Flashcards" mode that converts the 924-entry QUESTION_BANK into concept-first flashcards. Unlike the existing Flash Cards mode (81 theory terms), this module teaches underlying clinical principles rather than surfacing raw exam questions. Each card distills a question into a reusable concept title (Side A) and a key learning takeaway (Side B).

---

## Goals

- Give the user a concept-first study mode derived from AATBS exam questions
- Reuse the existing flashcard UI (flip interaction, grading, resurfacing) with zero changes to existing logic
- Allow filtering by the 6 quiz domains or mixing all cards
- Produce a human-reviewable card deck before shipping, so the user can curate quality

---

## Architecture

### Option Selected: Extend existing FC engine (Option A from brainstorm)

The existing `#screen-quiz`, flip logic, grade buttons, and missed-card resurfacing loop are reused unchanged. A branch on `activeMode === 'qfc'` in the card renderer switches between theory-term and exam-concept card templates.

### New Pieces

| Piece | Description |
|-------|-------------|
| Home tile | Full-width tile "Exam Flashcards" on `#screen-home`, same style as Question Lookup tile |
| `#screen-qfc-select` | Category selector screen with 7 tiles (6 domains + "Mix All"), each showing card count |
| `startQFC(category)` | Filters `EXAM_CARDS` by category, shuffles, sets `activeMode = 'qfc'`, populates `fcDeck`, calls `showScreen('screen-quiz')` |
| `EXAM_CARDS` array | New data structure embedded in the HTML, produced by the preprocessing pipeline |
| Card renderer branch | `activeMode === 'qfc'` check in existing flip/render functions to show concept title / concept explanation instead of term name / theory |

### Data Flow

```
User taps "Exam Flashcards"
  → showScreen('screen-qfc-select')
User picks a domain (or Mix All)
  → startQFC(category)
  → filter EXAM_CARDS, shuffle
  → set activeMode = 'qfc', populate fcDeck
  → showScreen('screen-quiz')
Existing flip/grade/resurface logic runs unchanged
```

---

## Card Format

### Side A (Front)
- **Domain label** — small uppercase muted text (e.g., "Clinical Evaluation")
- **Concept title** — large serif text, same visual weight as theory term cards (e.g., "Signs of Child Abuse")

### Side B (Back)
- **Key learning** — 1–3 sentences explaining the principle or clinical rule distilled from the correct answer + rationale (e.g., "When a child presents with clinginess, fearfulness, and social withdrawal, assess for child abuse before pursuing diagnosis or referral.")
- No raw answer choices shown — the back teaches the concept, not the answer letter

### Fallback
Questions that don't distill cleanly into a reusable, standalone concept are excluded (`keep: false`). Expected yield: ~500–600 cards from 924 source entries.

---

## EXAM_CARDS Data Structure

```javascript
const EXAM_CARDS = [
  {
    id: 1,
    category: "Clinical Evaluation",       // matches the 6 AATBS quiz domains
    concept_title: "Signs of Child Abuse",
    concept_explanation: "When a child presents with clinginess, fearfulness, and social withdrawal, prioritize assessing for child abuse before pursuing a diagnosis or referral.",
    source_q: "A mother brings in her 6-year-old daughter..."  // kept for traceability, not shown on card
  },
  // ...
];
```

### Domain Categories (exact strings)
1. `"Clinical Evaluation"`
2. `"Treatment"`
3. `"Law and Ethics"`
4. `"Case Conceptualization"`
5. `"Managing Crisis Situations"`
6. `"Developing a Diagnostic Impression"`

---

## Preprocessing Pipeline

### Purpose
One-time Python script that converts QUESTION_BANK entries to concept cards via Claude API.

### Script: `scripts/generate_flashcards.py`

**Input:** All 924 entries from QUESTION_BANK (extracted from `index.html` or a separate JSON export)

**Per-entry prompt to Claude:**
```
Given this exam question, its correct answer, and its rationale, derive a concept flashcard.

Question: {q}
Correct answer: {answerText}
Rationale: {rationale}
Category: {category}

Return JSON:
{
  "concept_title": "Short noun phrase naming the clinical concept being tested (e.g. 'Signs of Child Abuse', 'Suicide Risk Factors', 'Mandated Reporting — IPV'). Max 6 words.",
  "concept_explanation": "1–3 sentence takeaway a student should memorize. Teach the rule or principle, not the answer letter.",
  "keep": true/false  // false if the question tests trivia, procedure recall, or doesn't yield a reusable concept
}
```

**Output:** `scripts/flashcards_review.json`
```json
[
  {
    "id": 1,
    "category": "Clinical Evaluation",
    "concept_title": "Signs of Child Abuse",
    "concept_explanation": "...",
    "source_q": "...",
    "keep": true
  }
]
```

### Review Workflow
1. Script runs → produces `scripts/flashcards_review.json`
2. User reviews the file — edits titles, flips `keep: false` for unwanted cards
3. User approves
4. Approved cards are embedded as `EXAM_CARDS` array in `index.html`

---

## UI — Category Selector Screen (`#screen-qfc-select`)

- Back button → `goHome()`
- Page title: "Exam Flashcards"
- Page subtitle: "Choose a domain to drill or mix all questions"
- 7 tiles in a grid layout (matches `.mode-grid` style):
  - 6 domain tiles — name + card count (e.g., "Clinical Evaluation · 142 cards")
  - 1 "Mix All" full-width tile — total card count
- Tapping any tile calls `startQFC(category)` or `startQFC('all')`

---

## Grading & Resurfacing

Identical to existing FC mode:
- Three grade buttons: Got it / Almost / Missed it
- "Got it" → card removed from deck
- "Almost" / "Missed it" → card appended to end of deck
- Session ends when all cards graded "Got it"
- Summary screen shows score (same as existing FC summary)

---

## What Is NOT Changing

- `#screen-quiz` HTML structure
- `flipCard()`, `gradeFC()`, deck-resurfacing logic
- Existing theory-term Flash Cards mode
- Multiple Choice mode
- Question Lookup mode
- Key Terms by Diagnosis section

---

## Files Affected

| File | Change |
|------|--------|
| `index.html` | Add home tile, `#screen-qfc-select` HTML, CSS for selector screen, `EXAM_CARDS` array, `startQFC()` function, renderer branch in existing FC functions |
| `scripts/generate_flashcards.py` | New — one-time preprocessing script |
| `scripts/flashcards_review.json` | New — review artifact (not committed to repo after embed) |

---

## Success Criteria

- User can tap "Exam Flashcards" from home and pick a domain within 2 taps
- Cards flip, grade, and resurface identically to existing FC mode
- Each card teaches a principle, not a trivia answer
- Domain tiles show accurate card counts
- ~500+ cards available across all 6 domains
