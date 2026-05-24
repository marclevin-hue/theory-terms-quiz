# Enhanced Question Lookup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add input mode detection, a mode badge, term overlap count, and dual-card results to the Question Lookup screen of the theory-terms-quiz app.

**Architecture:** All changes are confined to `/Users/Marc/Desktop/theory-terms-quiz/index.html`. The file contains inline CSS, HTML, and JS. We add one new JS function, extend two existing JS functions, add four new HTML elements, and add five new CSS rules. No build step, no framework, no new files.

**Tech Stack:** Vanilla HTML/CSS/JS, static file served via Vercel. Manual browser verification replaces unit tests (no test framework exists).

---

## File Map

| File | What changes |
|---|---|
| `index.html` (CSS section) | Add `.mode-badge`, `.mode-badge.verbatim`, `.mode-badge.stem-only`, `.lookup-result-card.dim`, `.dual-header` |
| `index.html` (HTML section) | Add `#result-mode-badge` span, `#result-term-overlap` p, `#lookup-dual-header` div, `#lookup-result-2` card block |
| `index.html` (JS section) | Add `hasAnswerChoices()`, extend `lookupQuestion()`, extend `renderLookupResult()` |

---

## Task 1: Add `hasAnswerChoices()` and wire mode flag

**Files:**
- Modify: `index.html` — JS section, `lookupQuestion()` function (search for `function lookupQuestion`)

- [ ] **Step 1: Add the detection function**

Locate the line `function lookupQuestion() {` and insert this function **immediately before** it:

```javascript
function hasAnswerChoices(raw) {
  return /select\s+one/i.test(raw) || /[''']?[ABCD]\.\s/m.test(raw);
}
```

- [ ] **Step 2: Capture the verbatim flag in lookupQuestion()**

Inside `lookupQuestion()`, find:
```javascript
const input = document.getElementById('lookup-textarea').value.trim();
if (!input) return;
```

Add one line after:
```javascript
const input = document.getElementById('lookup-textarea').value.trim();
if (!input) return;
const verbatim = hasAnswerChoices(input);
```

- [ ] **Step 3: Manual verification**

Open the site locally (`npx serve -p 4400 .`). Open the browser console. Paste a question with answer choices into the lookup textarea, then in the console run:
```javascript
hasAnswerChoices(document.getElementById('lookup-textarea').value)
// Expected: true
```
Clear and type a question stem only:
```javascript
hasAnswerChoices(document.getElementById('lookup-textarea').value)
// Expected: false
```

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add hasAnswerChoices() input mode detection"
```

---

## Task 2: Track second-best match in `lookupQuestion()`

**Files:**
- Modify: `index.html` — JS section, inside `lookupQuestion()`

- [ ] **Step 1: Replace the single-match scan with a two-match scan**

Find this block inside `lookupQuestion()`:
```javascript
let bestScore = -1;
let bestMatch = null;

for (const entry of QUESTION_BANK) {
  const entryTokens = new Set(tokenize(entry.q));
  const sim = cosineSimilarity(queryTokens, entryTokens);
  if (sim > bestScore) {
    bestScore = sim;
    bestMatch = entry;
  }
}

if (!bestMatch) return;

const conf = scoreConfidence(bestScore);
renderLookupResult(bestMatch, conf, bestScore);
```

Replace it with:
```javascript
let bestScore = -1, secondScore = -1;
let bestMatch = null, secondMatch = null;

for (const entry of QUESTION_BANK) {
  const entryTokens = new Set(tokenize(entry.q));
  const sim = cosineSimilarity(queryTokens, entryTokens);
  if (sim > bestScore) {
    secondScore = bestScore; secondMatch = bestMatch;
    bestScore = sim; bestMatch = entry;
  } else if (sim > secondScore) {
    secondScore = sim; secondMatch = entry;
  }
}

if (!bestMatch) return;

const conf = scoreConfidence(bestScore);
renderLookupResult(bestMatch, secondMatch, conf, bestScore, verbatim, queryTokens);
```

- [ ] **Step 2: Manual verification**

In the browser console after submitting a question, verify no JS errors appear in the console. The result should display exactly as before (render function signature change is handled in Task 3).

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: track second-best match in lookupQuestion()"
```

---

## Task 3: Add HTML elements for mode badge, term overlap, and second card

**Files:**
- Modify: `index.html` — HTML section, `#lookup-result` div

- [ ] **Step 1: Add mode badge to the result card header**

Find this in the HTML:
```html
<span class="lookup-cat-badge" id="result-category">—</span>
```

Replace with:
```html
<div style="display:flex; align-items:center; gap:8px;">
  <span class="lookup-cat-badge" id="result-category">—</span>
  <span class="mode-badge" id="result-mode-badge">—</span>
</div>
```

- [ ] **Step 2: Add term overlap line below the confidence row**

Find:
```html
          <p class="lookup-rationale-label">Matched question</p>
```

Insert immediately before it:
```html
          <p class="lookup-term-overlap" id="result-term-overlap"></p>

```

- [ ] **Step 3: Add dual-card header and second result card**

Find the closing of `#lookup-result`:
```html
        <button class="lookup-try-again" onclick="resetLookup()">← Try Another Question</button>
      </div>
```

Replace with:
```html
        <div id="lookup-dual-header" class="dual-header" style="display:none;">
          Couldn't find a confident match — here are the 2 closest questions in the database:
        </div>

        <div id="lookup-result-2" class="lookup-result-card dim" style="display:none; margin-top:12px;">
          <div class="lookup-result-header">
            <div class="lookup-answer-badge">
              <div class="lookup-answer-letter" id="result-letter-2">A</div>
              <div class="lookup-answer-meta">
                <span class="lookup-answer-label">2nd closest</span>
                <span class="lookup-answer-text" id="result-answer-text-2">—</span>
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="lookup-cat-badge" id="result-category-2">—</span>
              <span class="mode-badge" id="result-mode-badge-2">—</span>
            </div>
          </div>
          <p class="lookup-term-overlap" id="result-term-overlap-2"></p>
          <p class="lookup-rationale-label">Matched question</p>
          <p class="lookup-matched-q" id="result-matched-q-2">—</p>
          <p class="lookup-rationale-label">Rationale</p>
          <p class="lookup-rationale-text" id="result-rationale-2">—</p>
        </div>

        <button class="lookup-try-again" onclick="resetLookup()">← Try Another Question</button>
      </div>
```

- [ ] **Step 4: Manual verification**

Load the page. No visual changes should appear on the home screen or lookup input. Submit a lookup — the result card should look identical to before (new elements are either hidden or empty until Task 4 wires them up).

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add HTML for mode badge, term overlap, and second result card"
```

---

## Task 4: Add CSS for new elements

**Files:**
- Modify: `index.html` — CSS section (inside `<style>`)

- [ ] **Step 1: Add all new CSS rules**

Find the existing `.lookup-warn {` rule. Insert the following block immediately before it:

```css
    .mode-badge {
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      padding: 3px 9px;
      border-radius: 20px;
      text-transform: uppercase;
    }
    .mode-badge.verbatim {
      background: rgba(80,180,100,0.15);
      color: #6dbb80;
      border: 1px solid rgba(80,180,100,0.25);
    }
    .mode-badge.stem-only {
      background: rgba(212,145,58,0.15);
      color: var(--accent-lt);
      border: 1px solid rgba(212,145,58,0.25);
    }
    .lookup-term-overlap {
      font-size: 0.78rem;
      color: var(--muted);
      margin: 0 0 14px;
      padding: 0;
    }
    .dual-header {
      font-size: 0.83rem;
      color: var(--muted);
      font-style: italic;
      margin: 0 0 14px;
      line-height: 1.5;
    }
    .lookup-result-card.dim {
      opacity: 0.75;
    }
```

- [ ] **Step 2: Manual verification**

Load the page and submit any question. The result card should look identical to before — new CSS classes are not yet applied to visible elements (mode badge still shows "—", term overlap is empty).

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add CSS for mode badge, term overlap, dual-header, and dim card"
```

---

## Task 5: Rewrite `renderLookupResult()` with full new logic

**Files:**
- Modify: `index.html` — JS section, `renderLookupResult()` function

- [ ] **Step 1: Replace the entire renderLookupResult function**

Find and replace the complete `function renderLookupResult(match, conf, rawScore) { ... }` block with:

```javascript
function renderLookupResult(bestMatch, secondMatch, conf, rawScore, verbatim, queryTokens) {
  const isDual = rawScore < 0.45;

  // ── Helper: compute term overlap string ──────────────────────────────────
  function overlapText(match) {
    const entryTokens = new Set(tokenize(match.q));
    const x = [...queryTokens].filter(t => entryTokens.has(t)).length;
    const y = queryTokens.size;
    return 'Matched ' + x + ' of ' + y + ' key terms';
  }

  // ── Helper: set mode badge ────────────────────────────────────────────────
  function setModeBadge(el) {
    el.textContent = verbatim ? 'Verbatim paste' : 'Stem only';
    el.className = 'mode-badge ' + (verbatim ? 'verbatim' : 'stem-only');
  }

  // ── Populate primary card ─────────────────────────────────────────────────
  document.getElementById('result-letter').textContent = bestMatch.answer;
  document.getElementById('result-answer-text').textContent = 'Answer ' + bestMatch.answer;
  document.getElementById('result-category').textContent = bestMatch.category;
  document.getElementById('result-matched-q').textContent = bestMatch.q;
  document.getElementById('result-rationale').textContent = bestMatch.rationale;
  document.getElementById('result-term-overlap').textContent = overlapText(bestMatch);
  setModeBadge(document.getElementById('result-mode-badge'));

  // ── Confidence dots (single mode only) ───────────────────────────────────
  const confRow = document.querySelector('.conf-row');
  if (confRow) confRow.style.display = isDual ? 'none' : '';

  if (!isDual) {
    const dotsEl = document.getElementById('conf-dots');
    dotsEl.innerHTML = '';
    const colorClass = conf >= 4 ? 'high' : conf <= 2 ? 'low' : '';
    for (let i = 1; i <= 5; i++) {
      const dot = document.createElement('div');
      dot.className = 'conf-dot' + (i <= conf ? ' filled ' + colorClass : '');
      dotsEl.appendChild(dot);
    }
    const labels = ['','Very Low','Low','Moderate','High','Very High'];
    document.getElementById('conf-score-text').textContent = labels[conf] + ' (' + conf + '/5)';
  }

  // ── Warning banner: always hidden (threshold mutually exclusive) ──────────
  document.getElementById('lookup-warn').style.display = 'none';

  // ── Dual-card path ────────────────────────────────────────────────────────
  const dualHeader = document.getElementById('lookup-dual-header');
  const card2 = document.getElementById('lookup-result-2');

  if (isDual && secondMatch) {
    dualHeader.style.display = 'block';
    card2.style.display = 'block';

    document.getElementById('result-letter-2').textContent = secondMatch.answer;
    document.getElementById('result-answer-text-2').textContent = 'Answer ' + secondMatch.answer;
    document.getElementById('result-category-2').textContent = secondMatch.category;
    document.getElementById('result-matched-q-2').textContent = secondMatch.q;
    document.getElementById('result-rationale-2').textContent = secondMatch.rationale;
    document.getElementById('result-term-overlap-2').textContent = overlapText(secondMatch);
    setModeBadge(document.getElementById('result-mode-badge-2'));
  } else {
    dualHeader.style.display = 'none';
    card2.style.display = 'none';
  }

  // ── Show result, hide input ───────────────────────────────────────────────
  document.getElementById('lookup-input-area').style.display = 'none';
  document.getElementById('lookup-result').style.display = 'block';
}
```

- [ ] **Step 2: Update resetLookup() to also hide second card and dual header**

Find:
```javascript
function resetLookup() {
  document.getElementById('lookup-textarea').value = '';
  document.getElementById('lookup-input-area').style.display = 'block';
  document.getElementById('lookup-result').style.display = 'none';
}
```

Replace with:
```javascript
function resetLookup() {
  document.getElementById('lookup-textarea').value = '';
  document.getElementById('lookup-input-area').style.display = 'block';
  document.getElementById('lookup-result').style.display = 'none';
  document.getElementById('lookup-result-2').style.display = 'none';
  document.getElementById('lookup-dual-header').style.display = 'none';
}
```

- [ ] **Step 3: Manual verification — verbatim paste (high confidence)**

Paste a full exam question with A/B/C/D choices that is in the bank (e.g. the Gabriel veteran question). Submit. Verify:
- Green "Verbatim paste" badge appears next to category
- "Matched X of Y key terms" line appears below confidence
- Confidence dots still show (5 dots)
- Only one card shown
- No second card, no dual header

- [ ] **Step 4: Manual verification — stem only (high confidence)**

Paste just the question stem (no choices) for the same question. Submit. Verify:
- Amber "Stem only" badge appears
- Term overlap line present
- One card, confidence dots shown

- [ ] **Step 5: Manual verification — low confidence / not in bank**

Paste a question not in the bank (e.g. make one up). Submit. Verify:
- Dual header appears: "Couldn't find a confident match..."
- Two cards shown, second card is dimmed with "2nd closest" label
- Both cards show mode badge and term overlap
- Confidence dots hidden on both cards
- Old `#lookup-warn` banner is gone

- [ ] **Step 6: Manual verification — Try Another Question**

Click "← Try Another Question". Verify both cards and the dual header disappear and the textarea reappears cleanly.

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "feat: rewrite renderLookupResult() with mode badge, term overlap, dual-card path"
```

---

## Task 6: Final QA and deploy

- [ ] **Step 1: Full end-to-end smoke test**

Run through all four scenarios in order:
1. Full paste (verbatim, high confidence) → single card, green badge, dots visible
2. Stem only (high confidence) → single card, amber badge, dots visible
3. Full paste (not in bank) → dual cards, green badge on both, dots hidden
4. Stem only (not in bank) → dual cards, amber badge on both, dots hidden

Confirm "Try Another Question" resets cleanly after each.

- [ ] **Step 2: Check for JS console errors**

Open DevTools. Run through each scenario. Zero errors expected.

- [ ] **Step 3: Push to deploy**

```bash
git push origin main
```

Vercel auto-deploys. Visit `https://theory-terms-quiz.vercel.app` and verify the live site matches local.

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add index.html
git commit -m "fix: QA pass on enhanced question lookup"
git push origin main
```
