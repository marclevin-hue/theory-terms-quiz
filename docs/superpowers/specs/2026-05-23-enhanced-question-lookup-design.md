# Enhanced Question Lookup — Design Spec
**Date:** 2026-05-23
**Project:** theory-terms-quiz (single-file static HTML/CSS/JS app)
**Status:** Approved by user

---

## Background

The Question Lookup feature currently assumes users paste a full AATBS exam question including the four answer choices (A–D). The preprocessor strips the choices before matching, so the engine works on the question stem only. However:

- Users may want to type or paste just the question stem (no choices)
- There is no signal in the UI that distinguishes these two input modes
- When no confident match is found, the UI shows one result with a warning — offering two candidates would help users identify which stored question is actually theirs

---

## Scope

Modifications are confined to `index.html`. No new files, no backend, no build step.

Changes touch:
- One new JS detection function (`hasAnswerChoices`)
- `lookupQuestion()` — compute second-best match, pass mode flag
- `renderLookupResult()` — accept new parameters, branch on single vs dual render
- HTML — two new element slots (mode badge, term overlap line, second result card)
- CSS — mode badge variants, second-card de-emphasis, dual-card container

No changes to the matching engine, preprocessing, confidence thresholds, or QUESTION_BANK.

---

## Components

### 1. Input Mode Detection

```js
function hasAnswerChoices(raw) {
  return /select\s+one/i.test(raw) || /['']?[ABCD]\.\s/m.test(raw);
}
```

Called once on the raw textarea value before preprocessing. Returns a boolean `verbatim` flag passed to the render function.

### 2. Mode Badge

Rendered inside the result card header, adjacent to the existing category badge.

| State | Label | Visual |
|---|---|---|
| Choices detected | `Verbatim paste` | Green-tinted pill |
| No choices | `Stem only` | Amber-tinted pill |

CSS classes: `.mode-badge.verbatim` and `.mode-badge.stem-only`.

### 3. Term Overlap Count

Rendered below the confidence row as a single line of muted text:

> *Matched 11 of 14 key terms*

Computation: `intersection(queryTokens, entryTokens).size` / `queryTokens.size`.
- Numerator: tokens in both query and matched entry
- Denominator: total meaningful tokens in the query (after stop-word removal)

Element id: `#result-term-overlap`

### 4. Single vs Dual Result Rendering

**Single result path** (`rawScore ≥ 0.45`):
- Existing result card layout, plus mode badge and term overlap line
- Confidence dots and score label unchanged

**Dual result path** (`rawScore < 0.45`):
- Existing warning banner is replaced by a subheader:
  > *"Couldn't find a confident match — here are the 2 closest questions in the database:"*
- Two stacked result cards rendered inside `#lookup-result`
- Card 1 (best match): full opacity, full styling
- Card 2 (second match): `opacity: 0.75`, slightly smaller answer badge, label "2nd closest"
- Confidence dots are hidden on both cards in dual mode — the two-card framing communicates uncertainty more honestly
- Mode badge and term overlap still shown on each card
- The existing `#lookup-warn` element is hidden in dual mode (subheader replaces it)

**Computing second match:**
In `lookupQuestion()`, track `bestScore`/`bestMatch` and `secondScore`/`secondMatch` in a single pass through QUESTION_BANK. Pass both to the render function.

### 5. Confidence Scale

No change. Thresholds and 1–5 dots remain identical. The mode badge and term overlap count carry the new confidence information.

---

## Data Flow

```
User submits textarea
  └─ hasAnswerChoices(raw)  →  verbatim: bool
  └─ preprocessQuery(raw)  →  cleaned stem
  └─ tokenize(cleaned)     →  queryTokens
  └─ scan QUESTION_BANK    →  bestMatch, bestScore, secondMatch, secondScore
  └─ scoreConfidence(bestScore)  →  conf (1–5)
  └─ renderLookupResult(bestMatch, secondMatch, conf, bestScore, verbatim, queryTokens)
       ├─ rawScore ≥ 0.45  →  single card + mode badge + term overlap
       └─ rawScore < 0.45  →  dual cards + subheader (no dots, no warn banner)
```

---

## Error / Edge Cases

| Case | Behaviour |
|---|---|
| Empty input | Early return, no change (existing behaviour) |
| Input with zero meaningful tokens after preprocessing | Early return (existing behaviour) |
| Only one entry in QUESTION_BANK | Dual path: show only the one card, no second card |
| Both matches have identical question text | Allowed — can happen with near-duplicate entries; user sees both |
| `queryTokens.size === 0` | Term overlap shows "Matched 0 of 0 key terms" — acceptable edge case |

---

## Out of Scope

- Semantic / embedding-based matching (requires backend)
- Changes to the 1–5 confidence scale or thresholds
- Changes to the QUESTION_BANK or preprocessing logic
- Mobile-optimised layout (desktop-primary per user decision)
