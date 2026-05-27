# Exam Flashcards Module — Design Spec
**Date:** 2026-05-27 (rev 2 — post spec-review)
**Project:** theory-terms-quiz (single-file static HTML/CSS/JS app)
**Status:** Approved for implementation

---

## Overview

A new "Exam Flashcards" mode that converts the 924-entry QUESTION_BANK into concept-first flashcards. Unlike the existing Flash Cards mode (81 theory terms), this module teaches underlying clinical principles rather than surfacing raw exam questions. Each card distills a question into a reusable concept title (Side A) and a key learning takeaway (Side B).

---

## Goals

- Give the user a concept-first study mode derived from AATBS exam questions
- Reuse the existing `#screen-quiz` HTML and most FC engine code
- Add a missed-card resurface loop (new behavior — see Grading section)
- Allow filtering by the 6 quiz domains, a Practice Exams tile, or all cards
- Produce a human-reviewable card deck before shipping so the user can curate quality

---

## Architecture

### Approach: Extend existing FC engine

The existing `#screen-quiz` HTML is reused. `fcRenderCard()` gains a branch on `activeMode === 'qfc'` to bind concept card fields. The grading flow gains a new resurface loop (QFC-only). Everything else in the FC mode is unchanged.

### New Pieces

| Piece | Description |
|-------|-------------|
| Home tile | Full-width tile "Exam Flashcards" on `#screen-home` — same `grid-column: 1 / -1` row style as Question Lookup tile |
| `#screen-qfc-select` | Category selector: 8 tiles (6 domains + "Practice Exams" + "Mix All"), each showing live card count computed from `EXAM_CARDS` at render time |
| `startQFC(category)` | Filters `EXAM_CARDS` by category (or takes all), shuffles, sets `activeMode = 'qfc'`, populates `fcDeck`, resets `fcFlipped = false`, `fcIndex = 0`, `fcHistory = [0]`, `fcScores = []`, `qfcRight = 0`, `qfcWrong = 0`, `qfcOriginalLength = fcDeck.length`, updates `fc-prog-total`, calls `showScreen('screen-quiz')` |
| `EXAM_CARDS` array | New data structure embedded in `index.html`, produced by preprocessing pipeline |
| `fcRenderCard()` branch | When `activeMode === 'qfc'`: binds `card.concept_title` → `#fc-term`, `card.concept_explanation` → `#fc-theory`; updates face labels and nav mode label dynamically |
| Resurface loop | Added to `fcScore()` for QFC mode only: wrong/almost answers are appended to the end of `fcDeck` and re-encountered until scored correct |

### Data Flow

```
User taps "Exam Flashcards"
  → showScreen('screen-qfc-select')
User picks a domain (or Mix All)
  → startQFC(category)
  → filter EXAM_CARDS, shuffle
  → set activeMode = 'qfc', populate fcDeck
  → showScreen('screen-quiz')
fcRenderCard() detects activeMode === 'qfc', binds concept fields
User flips, grades → fcScore()
  → if 'wrong'/'almost': append card copy to end of fcDeck (resurface loop)
  → if 'right': advance normally
Session ends when fcIndex >= fcDeck.length - 1 with no pending resurfaces
  → endSession() shows summary with "Exam Flashcards" badge
```

---

## Card Format

### Side A (Front)
- **Face label** — dynamically set to `"Concept"` when `activeMode === 'qfc'` (replaces `"Term"`)
- **Concept title** — `card.concept_title` → `#fc-term` (e.g., *"Signs of Child Abuse"*)

### Side B (Back)
- **Face label** — dynamically set to `"Key Learning"` when `activeMode === 'qfc'` (replaces `"Theory"`)
- **Key learning** — `card.concept_explanation` → `#fc-theory` — 1–3 sentences explaining the clinical rule or principle

### Nav / Labels
- `quiz-nav-mode` span text: set to `"Exam Flashcards"` when `activeMode === 'qfc'`
- Target using `document.querySelector('#screen-quiz .quiz-nav-mode')` — the same class appears in `#screen-mc`, so a broad `querySelector` would hit the wrong element

### Fallback
Questions that don't distill cleanly into a reusable standalone concept are excluded (`keep: false`) during preprocessing. Expected yield: ~500–600 cards from 924 source entries.

---

## EXAM_CARDS Data Structure

```javascript
const EXAM_CARDS = [
  {
    id: 1,
    category: "Clinical Evaluation",   // exact string from QUESTION_BANK (see below)
    concept_title: "Signs of Child Abuse",
    concept_explanation: "When a child presents with clinginess, fearfulness, and social withdrawal, prioritize assessing for child abuse before pursuing a diagnosis or referral.",
    source_q: "A mother brings in her 6-year-old daughter..."  // for traceability; not shown on card
  },
  // ...
];
```

### Domain Category Strings — Exact Values from QUESTION_BANK

| Tile label | `category` value in EXAM_CARDS | Source count |
|---|---|---|
| Clinical Evaluation | `"Clinical Evaluation"` | 92 |
| Treatment | `"Treatment"` | 199 |
| Law & Ethics | `"Law & Ethics"` | 132 |
| Case Conceptualization | `"Case Conceptualization"` | 79 |
| Managing Crisis | `"Managing Crisis"` | 83 |
| Diagnostic Impression | `"Diagnostic Impression"` | 38 |
| Practice Exams | `"Practice Exam 1"` | 301 |

The preprocessing script receives these exact strings as the `category` value in its prompt. No normalization step needed.

---

## Grading & Resurfacing (QFC-specific behavior)

The existing FC mode uses two buttons ("✓ Right" / "✗ Wrong") and linear progression — `fcAdvance()` simply increments `fcIndex`; there is no resurfacing. This is unchanged.

**QFC adds a resurface loop** inside `fcScore()` when `activeMode === 'qfc'`:

```
fcScore('right')  → increment qfcRight counter, then fcAdvance() as normal
fcScore('wrong')  → increment qfcWrong counter, push a copy of fcDeck[fcIndex]
                    to end of fcDeck, THEN call fcAdvance()
                    (push must happen before fcAdvance to avoid premature end-of-deck)
```

**Score tracking:** QFC uses two running counters (`qfcRight`, `qfcWrong`) instead of the `fcScores` per-index array. This avoids out-of-bounds writes as `fcDeck` grows with resurfaced cards. `endSession()` receives `{ right: qfcRight, wrong: qfcWrong }` for QFC sessions; the badge and ring still work with right/wrong counts.

**Denominator display:** `fc-face-num` shows `${fcIndex + 1} / ${qfcOriginalLength}` — the denominator is frozen at the original deck length stored in `qfcOriginalLength` at session start. Resurfaced cards don't inflate the counter. (The progress bar `fc-prog-fill` continues to use `fcDeck.length` for an honest progress indicator.)

**Back button during resurfacing:** `fcBack()` is disabled once `fcIndex >= qfcOriginalLength` (i.e., once the user enters the resurface zone). This prevents double-scoring a slot and confusing stats. The Back button's `disabled` state is set in `fcRenderCard()` using the same check already there (`fcHistory.length <= 1`), extended to also disable when `activeMode === 'qfc' && fcIndex >= qfcOriginalLength`.

The "Got it / Almost / Missed it" language discussed during brainstorming maps onto the existing two-button UI as follows: the existing "✓ Right" = "Got it" and "✗ Wrong" = "Missed it / Almost". No new buttons are added.

### Play Again
`playAgain()` currently: `if (activeMode === 'fc') startFC(); else startMC();`

Add QFC branch: `else if (activeMode === 'qfc') showScreen('screen-qfc-select');`

"Play Again" after a QFC session returns the user to the category selector, not the same deck.

### Summary Screen Badge
`endSession()` badge currently has `fc` case and falls through to "Multiple Choice" for all else.

Add QFC case:
```javascript
if (activeMode === 'qfc') {
  badge.innerHTML = `<svg ...document-icon...></svg> Exam Flashcards`;
}
```

---

## Preprocessing Pipeline

### Purpose
One-time Python script that converts QUESTION_BANK entries to concept cards via Claude API.

### Input Preparation
Export the QUESTION_BANK JS array from `index.html` to a standalone `scripts/question_bank.json` file before running. This avoids complex HTML parsing.

### Script: `scripts/generate_exam_flashcards.py`

**Per-entry prompt to Claude:**
```
Given this exam question, its correct answer text, and its rationale, derive a concept flashcard.

Question: {q}
Correct answer text: {answerText_or_fallback}
Rationale: {rationale}
Category: {category}

Return JSON only:
{
  "concept_title": "Short noun phrase (max 6 words) naming the clinical concept tested. Examples: 'Signs of Child Abuse', 'Suicide Risk Factors', 'Mandated Reporting — IPV'.",
  "concept_explanation": "1–3 sentences. State the clinical rule or principle a student should memorize. Teach the concept, not the answer letter.",
  "keep": true or false  // false if the question tests procedural recall, specific statistics, or doesn't yield a reusable standalone principle
}
```

**answerText fallback:** If `answerText` is empty or missing (298/924 entries), substitute `"(answer text not available)"` in the prompt. Claude will use the rationale alone to derive the concept. If the rationale is also too thin to yield a concept, the script should set `keep: false`.

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
2. User reviews the file — edits `concept_title`/`concept_explanation`, flips `keep` to `false` to drop cards
3. User approves
4. Approved (`keep: true`) cards embedded as `EXAM_CARDS` array in `index.html`
5. `scripts/flashcards_review.json` and `scripts/question_bank.json` kept in repo for traceability but not served

---

## UI — Category Selector Screen (`#screen-qfc-select`)

- Back button → `goHome()`
- Nav mode label: `"Exam Flashcards"`
- Page title: "Exam Flashcards"
- Page subtitle: "Choose a domain to drill, or mix all"
- 8 tiles using `.mode-grid`:
  - 6 domain tiles (standard 2-column grid) — name + live card count (e.g., `"Clinical Evaluation · 142 cards"`)
  - 1 "Practice Exams" tile (standard grid)
  - 1 "Mix All" full-width tile (`grid-column: 1 / -1`, row layout) — shows total card count
- Card counts computed at render time: `EXAM_CARDS.filter(c => c.category === cat).length`
- Tapping any tile calls `startQFC(category)` or `startQFC('all')`

---

## What Is NOT Changing

- `#screen-quiz` HTML structure (no new elements added)
- `flipCard()`, `fcBack()`, `fcNext()`, `fcRenderStats()`, `fcAdvance()`
- Existing theory-term Flash Cards mode behavior
- Multiple Choice mode
- Question Lookup mode
- Key Terms by Diagnosis section

---

## Files Affected

| File | Change |
|------|--------|
| `index.html` | Add home tile; add `#screen-qfc-select` HTML + CSS; add `EXAM_CARDS` array; add `startQFC()` function; branch in `fcRenderCard()` for concept card binding + face/nav label updates; branch in `fcScore()` for QFC resurface loop; add QFC case in `playAgain()` and `endSession()` |
| `scripts/generate_exam_flashcards.py` | New — one-time preprocessing script |
| `scripts/question_bank.json` | New — QUESTION_BANK exported for script input |
| `scripts/flashcards_review.json` | New — review artifact (kept for traceability after embed) |

---

## Success Criteria

- User can reach a flashcard session within 2 taps from home
- Side A shows a clean concept title; Side B shows a clinical principle
- Wrong answers resurface until the user gets them right
- All 8 domain/mix tiles show accurate card counts
- Existing Flash Cards and Multiple Choice modes are unaffected
- ~500+ cards available across all domains after review curation
