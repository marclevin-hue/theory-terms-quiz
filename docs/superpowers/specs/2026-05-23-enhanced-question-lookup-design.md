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

Display is **raw counts**, not a ratio:
- X = `[...queryTokens].filter(t => entryTokens.has(t)).length` (intersection count)
- Y = `queryTokens.size` (total meaningful query tokens after stop-word removal)
- String: `"Matched " + X + " of " + Y + " key terms"`

`queryTokens` is a `Set<string>`, produced by wrapping the array returned from `tokenize()` in `new Set(...)`. This is already done in the existing `lookupQuestion()` call (`new Set(tokenize(cleaned))`). The same Set is passed to `renderLookupResult()` for overlap computation.

`entryTokens` for each match is computed identically: `new Set(tokenize(entry.q))`.

Element id: `#result-term-overlap`

### 4. Single vs Dual Result Rendering

**Single result path** (`rawScore ≥ 0.45`):
- Existing result card layout, plus mode badge and term overlap line
- Confidence dots and score label unchanged

**Dual result path** (`rawScore < 0.45`):
- Existing `#lookup-warn` banner is hidden (`display:none`); a subheader replaces it:
  > *"Couldn't find a confident match — here are the 2 closest questions in the database:"*
- Two stacked result cards rendered inside `#lookup-result`
- Card 1 (best match): full opacity, full styling
- Card 2 (second match): `opacity: 0.75`, slightly smaller answer badge, label "2nd closest"
- Confidence dots (`#conf-dots`) and score text (`#conf-score-text`) are hidden on both cards in dual mode — the two-card framing communicates uncertainty more honestly than a score would
- `scoreConfidence()` is still called (for potential future use) but its return value is not rendered in dual mode
- Mode badge and term overlap still shown on each card

**Single result path** (`rawScore ≥ 0.45`):
- `#lookup-warn` is always hidden in single-card path, because the warning threshold (`rawScore < 0.45`) and single-card threshold (`rawScore ≥ 0.45`) are mutually exclusive by definition
- Confidence dots and score label rendered as today

**Computing second match:**
In `lookupQuestion()`, track `bestScore`/`bestMatch` and `secondScore`/`secondMatch` in a single pass through QUESTION_BANK. Pass both to the render function.

### 5. Confidence Scale

No change. Thresholds and 1–5 dots remain identical. The mode badge and term overlap count carry the new confidence information.

---

## Data Flow

```
User submits textarea
  └─ hasAnswerChoices(raw)         →  verbatim: bool
  └─ preprocessQuery(raw)          →  cleaned stem
  └─ new Set(tokenize(cleaned))    →  queryTokens: Set<string>
  └─ scan QUESTION_BANK            →  bestMatch, bestScore, secondMatch, secondScore
  └─ scoreConfidence(bestScore)    →  conf: 1–5 (computed but only rendered in single-card path)
  └─ renderLookupResult(bestMatch, secondMatch, conf, bestScore, verbatim, queryTokens)
       ├─ rawScore ≥ 0.45  →  single card
       │    ├─ answer badge, category badge, mode badge
       │    ├─ confidence dots + score label (conf)
       │    ├─ term overlap (X of Y from queryTokens ∩ new Set(tokenize(bestMatch.q)))
       │    ├─ matched question text, rationale
       │    └─ #lookup-warn: hidden (threshold mutually exclusive with single path)
       └─ rawScore < 0.45  →  dual cards
            ├─ subheader replaces #lookup-warn
            ├─ Card 1: full opacity — answer, mode badge, term overlap, matched Q, rationale
            ├─ Card 2: 0.75 opacity — same fields, "2nd closest" label
            └─ confidence dots: hidden on both cards
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
