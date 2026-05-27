# Exam Flashcards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a concept-first Exam Flashcards mode that distills 900+ QUESTION_BANK entries into clinical principle cards, filterable by 7 domains, with a missed-card resurface loop.

**Architecture:** Extend the existing FC engine in `index.html` — `fcRenderCard()` and `fcScore()` gain a branch on `activeMode === 'qfc'`. A one-time Python+Claude API script preprocesses QUESTION_BANK entries into `EXAM_CARDS`. The `#screen-qfc-select` category picker and a new `startQFC()` function are the only new structural pieces. The `#screen-quiz` HTML is reused unchanged.

**Tech Stack:** Single-file HTML/CSS/JS (`index.html`, ~3400 lines), Python 3 + `anthropic` library (preprocessing script only), `npx serve -p 4400 .` for local dev.

**Spec:** `docs/superpowers/specs/2026-05-27-exam-flashcards-design.md`

---

## File Map

| File | Status | What changes |
|------|--------|-------------|
| `index.html` | Modify | Home tile, `#screen-qfc-select` HTML, CSS, `EXAM_CARDS` array, `showQFCSelect()`, `renderQFCSelect()`, `startQFC()`, `qfc*` state variables, branches in `fcRenderCard()` / `fcScore()` / `fcNext()` / `fcRenderStats()` / `fcAdvance()` / `playAgain()` / `endSession()` |
| `scripts/generate_exam_flashcards.py` | Create | One-time preprocessing script |
| `scripts/question_bank.json` | Create | QUESTION_BANK exported for script input |
| `scripts/flashcards_review.json` | Create (generated) | Human-review artifact; later used for embed |

---

## ⚠️ Human Gate: Task 3

Task 3 produces `scripts/flashcards_review.json` for Marc to review. **Tasks 4–9 can proceed in parallel** — they build the full UI using a stub `EXAM_CARDS` array. Task 10 replaces the stub with the approved data. Do not block UI work on the review gate.

---

## Task 1: Export QUESTION_BANK to JSON

**Files:**
- Create: `scripts/question_bank.json`

- [ ] **Step 1: Create `scripts/` directory and export QUESTION_BANK**

Run from the project root:
```bash
mkdir -p scripts
node -e "
const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
const match = html.match(/const QUESTION_BANK = (\[[\s\S]*?\n\];)/);
if (!match) { console.error('QUESTION_BANK not found'); process.exit(1); }
const data = eval(match[1]);
fs.writeFileSync('scripts/question_bank.json', JSON.stringify(data, null, 2));
console.log('Exported', data.length, 'entries');
"
```

Expected output:
```
Exported 924 entries
```

- [ ] **Step 2: Verify the output**

```bash
python3 -c "
import json
with open('scripts/question_bank.json') as f:
    data = json.load(f)
cats = {}
for e in data:
    cats[e.get('category','?')] = cats.get(e.get('category','?'), 0) + 1
for k, v in sorted(cats.items(), key=lambda x: -x[1]):
    print(f'  {v:4d}  {k}')
print(f'Total: {len(data)}')
"
```

Expected output (exact counts):
```
  301  Practice Exam 1
  199  Treatment
  132  Law & Ethics
   92  Clinical Evaluation
   83  Managing Crisis
   79  Case Conceptualization
   38  Diagnostic Impression
Total: 924
```

- [ ] **Step 3: Commit**

```bash
git add scripts/question_bank.json
git commit -m "chore: export QUESTION_BANK to scripts/question_bank.json for preprocessing"
```

---

## Task 2: Write preprocessing script

**Files:**
- Create: `scripts/generate_exam_flashcards.py`

- [ ] **Step 1: Install anthropic library if needed**

```bash
pip3 install anthropic 2>/dev/null || pip install anthropic
python3 -c "import anthropic; print('anthropic OK')"
```

- [ ] **Step 2: Create the script**

Create `scripts/generate_exam_flashcards.py`:

```python
#!/usr/bin/env python3
"""
One-time preprocessing script.
Reads scripts/question_bank.json, calls Claude API per entry,
outputs scripts/flashcards_review.json for human review.

Usage:
  ANTHROPIC_API_KEY=<key> python3 scripts/generate_exam_flashcards.py

Optional: resume a partial run (skips already-processed entries):
  ANTHROPIC_API_KEY=<key> python3 scripts/generate_exam_flashcards.py --resume
"""

import json, os, sys, time, re
import anthropic

INPUT  = "scripts/question_bank.json"
OUTPUT = "scripts/flashcards_review.json"

SYSTEM_PROMPT = """You are an MFT licensing exam study assistant. 
For each exam question you receive, derive a concept flashcard.
Return ONLY valid JSON — no markdown, no prose."""

def make_prompt(entry):
    q        = entry.get("q", "").strip()
    ans_text = entry.get("answerText", "").strip() or "(answer text not available)"
    rationale = entry.get("rationale", "").strip()
    category  = entry.get("category", "").strip()
    return f"""Given this MFT licensing exam question, its correct answer text, and its rationale, derive a concept flashcard.

Question: {q}
Correct answer text: {ans_text}
Rationale: {rationale}
Category: {category}

Return JSON only (no markdown fences):
{{
  "concept_title": "Short noun phrase, max 6 words, naming the clinical concept being tested. Examples: 'Signs of Child Abuse', 'Suicide Risk Factors', 'Mandated Reporting — IPV', 'DBT Skills for BPD'. Be specific.",
  "concept_explanation": "1–3 sentences. State the clinical rule or principle a student should memorize. Teach the concept, not the answer letter. Start with the key fact.",
  "keep": true
}}

Set keep to false ONLY if the question tests obscure procedural trivia, specific numerical statistics, or is so context-dependent it yields no reusable standalone principle."""

def extract_json(text):
    """Extract JSON from response, handling minor formatting issues."""
    text = text.strip()
    # Strip markdown fences if present
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    resume = "--resume" in sys.argv

    with open(INPUT) as f:
        entries = json.load(f)

    # Load existing output if resuming
    results = []
    processed_ids = set()
    if resume and os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            results = json.load(f)
        processed_ids = {r["id"] for r in results}
        print(f"Resuming: {len(processed_ids)} already processed.")

    client = anthropic.Anthropic(api_key=api_key)
    total  = len(entries)
    errors = 0

    for i, entry in enumerate(entries):
        entry_id = i + 1
        if entry_id in processed_ids:
            continue

        print(f"[{entry_id}/{total}] {entry.get('category','?')} — {entry.get('q','')[:60]}...")

        try:
            response = client.messages.create(
                model="claude-haiku-4-5",  # if this errors, substitute claude-haiku-4-6 or claude-3-5-haiku-latest
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": make_prompt(entry)}]
            )
            card = extract_json(response.content[0].text)
            results.append({
                "id":                  entry_id,
                "category":            entry.get("category", ""),
                "concept_title":       card.get("concept_title", ""),
                "concept_explanation": card.get("concept_explanation", ""),
                "source_q":            entry.get("q", "")[:200],
                "keep":                bool(card.get("keep", True))
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1
            results.append({
                "id":                  entry_id,
                "category":            entry.get("category", ""),
                "concept_title":       "",
                "concept_explanation": "",
                "source_q":            entry.get("q", "")[:200],
                "keep":                False,
                "error":               str(e)
            })

        # Save after every 50 entries (crash-safe)
        if len(results) % 50 == 0:
            with open(OUTPUT, "w") as f:
                json.dump(results, f, indent=2)
            print(f"  → Checkpoint saved ({len(results)} entries)")

        # Gentle rate limiting
        time.sleep(0.3)

    # Final save
    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2)

    kept   = sum(1 for r in results if r.get("keep"))
    print(f"\nDone. {len(results)} processed, {kept} kept, {errors} errors.")
    print(f"Review file: {OUTPUT}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit the script**

```bash
git add scripts/generate_exam_flashcards.py
git commit -m "chore: add exam flashcard preprocessing script"
```

---

## Task 3: Run script + Human Review Gate ⚠️

**Files:**
- Create: `scripts/flashcards_review.json` (generated)

- [ ] **Step 1: Run the preprocessing script**

```bash
ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY ~/.claude/settings.json 2>/dev/null | head -1 | grep -oP '(?<=: ")[^"]+' || echo "") \
  python3 scripts/generate_exam_flashcards.py
```

If the API key isn't in settings.json, set it directly:
```bash
ANTHROPIC_API_KEY=sk-ant-... python3 scripts/generate_exam_flashcards.py
```

The script saves a checkpoint every 50 entries. If interrupted, resume with:
```bash
ANTHROPIC_API_KEY=... python3 scripts/generate_exam_flashcards.py --resume
```

Expected final output:
```
Done. 924 processed, ~550–650 kept, 0 errors.
Review file: scripts/flashcards_review.json
```

- [ ] **Step 2: Human review** *(Marc does this)*

Open `scripts/flashcards_review.json`. For each entry:
- Edit `concept_title` if the label is vague or wrong
- Edit `concept_explanation` if the principle is unclear
- Set `"keep": false` to drop any card that isn't useful

Things to look for:
- Titles that are too generic ("Therapy Approach", "Assessment") — make them specific
- Explanations that describe a scenario rather than state a rule — rewrite to be declarative
- Duplicate concept titles across entries — keep the best one, drop the others
- Entries where `keep` is `true` but the concept is weak — flip to `false`

- [ ] **Step 3: Commit the reviewed file**

```bash
git add scripts/flashcards_review.json
git commit -m "chore: add reviewed exam flashcards deck (human-curated)"
```

> **Proceed to Tasks 4–9 while waiting for review, using the stub EXAM_CARDS array added in Task 7.**

---

## Task 4: Add CSS for `#screen-qfc-select`

**Files:**
- Modify: `index.html` (CSS section, line ~1120 near `</style>`)

- [ ] **Step 1: Add CSS before `</style>`**

Find the closing `</style>` tag (line ~1120) and add before it:

```css
    /* ── EXAM FLASHCARD SELECTOR ── */
    #screen-qfc-select {
      justify-content: flex-start;
      padding-top: 28px;
      padding-left: 10px;
      padding-right: 10px;
      width: 100vw;
    }

    .qfc-select-body {
      width: 100%;
      max-width: 680px;
    }
```

- [ ] **Step 2: Verify no CSS parse errors**

Open `http://localhost:4400` (run `npx serve -p 4400 .` if not running). Existing screens should look identical.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add CSS for exam flashcard selector screen"
```

---

## Task 5: Add home tile for Exam Flashcards

**Files:**
- Modify: `index.html` (home screen `.mode-grid`, ~line 1269)

- [ ] **Step 1: Add tile after the Key Terms by Diagnosis tile**

Find this exact two-line sequence (the Key Terms tile's closing `</div>` followed by the mode-grid closing `</div>`):
```html
      </div>
    </div>

    <div class="home-rule"></div>
```

Insert the new tile between those two closing `</div>` tags — after the Key Terms tile closes, before `.mode-grid` closes:

```html
      <div class="mode-tile" onclick="showQFCSelect()" style="grid-column: 1 / -1; display: flex; flex-direction: row; align-items: center; gap: 18px; padding: 22px 26px;">
        <div class="mode-icon" style="margin-bottom: 0; flex-shrink: 0;">
          <svg viewBox="0 0 18 18" fill="none" stroke="var(--accent-lt)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="1" y="2" width="16" height="14" rx="2"/>
            <line x1="5" y1="7" x2="13" y2="7"/>
            <line x1="5" y1="11" x2="10" y2="11"/>
          </svg>
        </div>
        <div>
          <div class="mode-name">Exam Flashcards</div>
          <div class="mode-desc">Concept-first cards distilled from 900+ exam questions — drill by domain or mix all</div>
        </div>
      </div>
```

- [ ] **Step 2: Verify visually**

Refresh `http://localhost:4400`. The home screen should show a 5th full-width tile "Exam Flashcards". Tapping it will error (function not yet defined) — that's expected.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add Exam Flashcards home tile"
```

---

## Task 6: Add `#screen-qfc-select` HTML

**Files:**
- Modify: `index.html` (after `#screen-diagnosis-terms` closes, ~line 1825)

- [ ] **Step 1: Find the insertion point**

Find this unique three-line sequence near the end of the `<body>`:
```html
  </section>

</div>
<script>
```
(the last `</section>`, the outer `</div>`, then `<script>`). Insert the new screen between `</section>` and `</div>`.

- [ ] **Step 2: Add the screen HTML**

```html
  <!-- ════════════ EXAM FLASHCARD SELECTOR ════════════ -->
  <section id="screen-qfc-select" class="screen">
    <nav class="quiz-nav">
      <button class="quiz-nav-home" onclick="goHome()">
        <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M1 7l6-6 6 6"/><path d="M2.5 5.5V13h3.5V9h2v4h3.5V5.5"/>
        </svg>
        Home
      </button>
      <span class="quiz-nav-mode">Exam Flashcards</span>
    </nav>
    <div class="qfc-select-body">
      <p class="home-eyebrow">Exam Flashcards</p>
      <h1 class="home-title">Choose a <em>Domain</em></h1>
      <p class="home-sub">Choose a domain to drill, or mix all questions together</p>
      <div class="mode-grid" id="qfc-domain-grid">
        <!-- Populated by renderQFCSelect() -->
      </div>
    </div>
  </section>
```

- [ ] **Step 3: Verify no HTML parse errors**

Refresh `http://localhost:4400`. All existing screens still work. The new screen isn't visible yet (no JS to show it).

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add #screen-qfc-select HTML"
```

---

## Task 7: Add EXAM_CARDS stub, QFC state, and navigation functions

**Files:**
- Modify: `index.html` (JS section)

This task wires up navigation and proves the selector screen renders correctly with a small stub deck. Real data is substituted in Task 10.

- [ ] **Step 1: Add QFC state variables**

Find (line ~1970):
```javascript
let activeMode = null; // 'fc' | 'mc'
```

Add after it:
```javascript
// ── QFC STATE ─────────────────────────────────────────────────────────────────
let qfcRight          = 0;
let qfcWrong          = 0;
let qfcOriginalLength = 0;
```

- [ ] **Step 2: Add EXAM_CARDS stub array**

Find the line `const QUESTION_BANK = [` (line ~2229). Insert the stub immediately before it:

```javascript
// ── EXAM CARDS (stub — replaced in Task 10 with full preprocessed deck) ───────
const EXAM_CARDS = [
  { id:1, category:"Clinical Evaluation",    concept_title:"Signs of Child Abuse",         concept_explanation:"When a child presents with fearfulness, clinginess, or withdrawal, prioritize assessing for abuse before pursuing a diagnosis or referral.", source_q:"" },
  { id:2, category:"Clinical Evaluation",    concept_title:"Suicide Risk: Active Plan",    concept_explanation:"A client with an active suicide plan requires immediate action — initiate a 5150 (involuntary hold). Safety contracts alone are insufficient when a lethal plan exists.", source_q:"" },
  { id:3, category:"Treatment",              concept_title:"DBT for BPD",                  concept_explanation:"Dialectical Behavior Therapy (DBT), developed by Marsha Linehan, is the evidence-based treatment for Borderline Personality Disorder. It targets mindfulness, interpersonal effectiveness, distress tolerance, and emotion regulation.", source_q:"" },
  { id:4, category:"Treatment",              concept_title:"ERP for OCD",                  concept_explanation:"Exposure and Response Prevention (ERP) is the gold-standard treatment for OCD. It is combined with SSRIs for moderate-to-severe presentations. Psychoeducation for client and family reduces accommodation behaviors.", source_q:"" },
  { id:5, category:"Law & Ethics",           concept_title:"Mandated Reporting — IPV",     concept_explanation:"When children are present during intimate partner violence, the therapist has reasonable suspicion of harm and must file a child abuse report — even if the children were not directly assaulted.", source_q:"" },
  { id:6, category:"Law & Ethics",           concept_title:"Minor Consent — Buprenorphine","concept_explanation":"Per AB 816 (effective Jan 1, 2024), minors 16 and older may independently consent to buprenorphine-based medication-assisted treatment for opioid use disorder outside a licensed narcotic treatment program.", source_q:"" },
  { id:7, category:"Case Conceptualization", concept_title:"Bowen: Family Role in Problems","concept_explanation":"In Murray Bowen's extended family systems therapy, each member is encouraged to identify their own role in the presenting problem rather than blaming others.", source_q:"" },
  { id:8, category:"Managing Crisis",        concept_title:"Rape: Medical Before Legal",   concept_explanation:"Following a sexual assault, the first clinical priority is ensuring the client receives a medical examination — before addressing emotional processing or legal decisions.", source_q:"" },
  { id:9, category:"Diagnostic Impression",  concept_title:"Adjustment Disorder Criteria", concept_explanation:"Adjustment Disorder requires an identifiable psychosocial stressor with symptoms beginning within 3 months of onset. Symptoms must be clinically significant but not meet criteria for another disorder.", source_q:"" },
  { id:10,category:"Practice Exam 1",        concept_title:"Hopelessness as Suicide Predictor","concept_explanation":"Hopelessness is the single strongest predictor of suicide risk — more so than depression severity alone. Flag it immediately and assess for plan, means, and intent.", source_q:"" },
];
```

- [ ] **Step 3: Add `showQFCSelect()`, `renderQFCSelect()`, and `startQFC()` functions**

Find `function showDiagnosisTerms()` and add after it:

```javascript
function showQFCSelect() {
  renderQFCSelect();
  showScreen('screen-qfc-select');
}

function renderQFCSelect() {
  const DOMAINS = [
    { label: 'Clinical Evaluation',    cat: 'Clinical Evaluation' },
    { label: 'Treatment',              cat: 'Treatment' },
    { label: 'Law & Ethics',           cat: 'Law & Ethics' },
    { label: 'Case Conceptualization', cat: 'Case Conceptualization' },
    { label: 'Managing Crisis',        cat: 'Managing Crisis' },
    { label: 'Diagnostic Impression',  cat: 'Diagnostic Impression' },
    { label: 'Practice Exams',         cat: 'Practice Exam 1' },
  ];
  const grid  = document.getElementById('qfc-domain-grid');
  const total = EXAM_CARDS.length;

  let html = DOMAINS.map(d => {
    const count = EXAM_CARDS.filter(c => c.category === d.cat).length;
    return `<div class="mode-tile" onclick="startQFC('${d.cat}')">
      <div class="mode-name">${d.label}</div>
      <div class="mode-desc">${count} card${count !== 1 ? 's' : ''}</div>
    </div>`;
  }).join('');

  html += `<div class="mode-tile" onclick="startQFC('all')" style="grid-column: 1 / -1; display:flex; flex-direction:row; align-items:center; gap:18px; padding:22px 26px;">
    <div>
      <div class="mode-name">Mix All</div>
      <div class="mode-desc">All ${total} cards shuffled together</div>
    </div>
  </div>`;

  grid.innerHTML = html;
}

function startQFC(category) {
  const pool = category === 'all'
    ? EXAM_CARDS
    : EXAM_CARDS.filter(c => c.category === category);

  activeMode        = 'qfc';
  // IMPORTANT: spread into a new array so shuffle() doesn't mutate EXAM_CARDS
  fcDeck            = shuffle([...pool]);
  fcIndex           = 0;
  fcFlipped         = false;
  fcScores          = [];
  fcHistory         = [0];
  qfcRight          = 0;
  qfcWrong          = 0;
  qfcOriginalLength = fcDeck.length;

  document.getElementById('fc-prog-total').textContent = fcDeck.length;
  showScreen('screen-quiz');
  fcRenderCard();
  fcRenderStats();
}
```

- [ ] **Step 4: Verify selector screen**

Refresh `http://localhost:4400`. Tap "Exam Flashcards" on the home screen. You should see `#screen-qfc-select` with 8 tiles. Each domain tile should show a card count (most will be 1–2 from the stub). "Mix All" should show 10.

Tap a domain tile — the flashcard screen should open. The card front should show "Term" (not yet "Concept") and stub content. That's expected — the label branch is Task 8.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add EXAM_CARDS stub, QFC state, showQFCSelect, renderQFCSelect, startQFC"
```

---

## Task 8: Branch `fcRenderCard()` for QFC mode

**Files:**
- Modify: `index.html` — `fcRenderCard()` function (~line 2036)

- [ ] **Step 1: Replace `fcRenderCard()`**

Find the entire existing `fcRenderCard()` function and replace it:

```javascript
function fcRenderCard() {
  const card = fcDeck[fcIndex];

  if (activeMode === 'qfc') {
    document.getElementById('fc-term').textContent   = card.concept_title;
    document.getElementById('fc-theory').textContent = card.concept_explanation;
    document.getElementById('fc-prog-num').textContent  = fcIndex + 1;
    document.getElementById('fc-face-num').textContent  = `${fcIndex + 1} / ${qfcOriginalLength}`;
    document.querySelector('#screen-quiz .card-front .face-label').textContent = 'Concept';
    document.querySelector('#screen-quiz .card-back  .face-label').textContent = 'Key Learning';
    document.querySelector('#screen-quiz .quiz-nav-mode').textContent          = 'Exam Flashcards';
  } else {
    document.getElementById('fc-term').textContent   = card.term;
    document.getElementById('fc-theory').textContent = card.theory;
    document.getElementById('fc-prog-num').textContent  = fcIndex + 1;
    document.getElementById('fc-face-num').textContent  = `${fcIndex + 1} / ${fcDeck.length}`;
    document.querySelector('#screen-quiz .card-front .face-label').textContent = 'Term';
    document.querySelector('#screen-quiz .card-back  .face-label').textContent = 'Theory';
    document.querySelector('#screen-quiz .quiz-nav-mode').textContent          = 'Flash Cards';
  }

  const el = document.getElementById('fc-card');
  if (fcFlipped) {
    el.classList.add('is-flipped');
    document.getElementById('fc-btn-correct').classList.remove('hidden');
    document.getElementById('fc-btn-wrong').classList.remove('hidden');
  } else {
    el.classList.remove('is-flipped');
    document.getElementById('fc-btn-correct').classList.add('hidden');
    document.getElementById('fc-btn-wrong').classList.add('hidden');
  }
  // Back disabled at start OR once we're in resurface zone (QFC only)
  document.getElementById('fc-btn-back').disabled =
    fcHistory.length <= 1 || (activeMode === 'qfc' && fcIndex >= qfcOriginalLength);
  document.getElementById('fc-prog-fill').style.width = (fcIndex / fcDeck.length * 100) + '%';
}
```

- [ ] **Step 2: Verify QFC card rendering**

Refresh. Start an Exam Flashcards session (any domain). Verify:
- Front face label reads **"Concept"**
- Back face label reads **"Key Learning"**
- Nav bar reads **"Exam Flashcards"**
- Card front shows `concept_title`, back shows `concept_explanation`

Then start a regular Flash Cards session (theory terms). Verify:
- Front label reads **"Term"** again
- Nav reads **"Flash Cards"** again
- Term/theory content is correct

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: branch fcRenderCard for QFC mode — concept labels and face text"
```

---

## Task 9: Add QFC resurface loop + fix grading, stats, play-again, summary

**Files:**
- Modify: `index.html` — `fcScore()`, `fcRenderStats()`, `fcAdvance()`, `playAgain()`, `endSession()`

- [ ] **Step 1: Replace `fcScore()` and add a QFC guard to `fcNext()`**

Find:
```javascript
function fcScore(result) {
  fcScores[fcIndex] = result;
  fcAdvance();
}

function fcNext() {
  if (fcScores[fcIndex] === null) fcScores[fcIndex] = 'skip';
  fcAdvance();
}
```

Replace with:
```javascript
function fcScore(result) {
  if (activeMode === 'qfc') {
    if (result === 'right') {
      qfcRight++;
    } else {
      qfcWrong++;
      // Push BEFORE calling fcAdvance — otherwise deck length hasn't grown yet
      // and fcAdvance() would fire end-of-session prematurely.
      // Spread into a new object: EXAM_CARDS entries are flat so this is safe.
      fcDeck.push({ ...fcDeck[fcIndex] });
    }
    fcAdvance();
  } else {
    fcScores[fcIndex] = result;
    fcAdvance();
  }
}

function fcNext() {
  if (activeMode !== 'qfc') {
    // QFC has no skip — Next button advances without recording
    if (fcScores[fcIndex] === null) fcScores[fcIndex] = 'skip';
  }
  fcAdvance();
}
```

- [ ] **Step 2: Replace `fcRenderStats()`**

Find:
```javascript
function fcRenderStats() {
  document.getElementById('fc-cnt-right').textContent = fcScores.filter(s => s === 'right').length;
  document.getElementById('fc-cnt-wrong').textContent = fcScores.filter(s => s === 'wrong').length;
  document.getElementById('fc-cnt-skip').textContent  = fcScores.filter(s => s === 'skip').length;
}
```

Replace with:
```javascript
function fcRenderStats() {
  if (activeMode === 'qfc') {
    document.getElementById('fc-cnt-right').textContent = qfcRight;
    document.getElementById('fc-cnt-wrong').textContent = qfcWrong;
    document.getElementById('fc-cnt-skip').textContent  = 0;
  } else {
    document.getElementById('fc-cnt-right').textContent = fcScores.filter(s => s === 'right').length;
    document.getElementById('fc-cnt-wrong').textContent = fcScores.filter(s => s === 'wrong').length;
    document.getElementById('fc-cnt-skip').textContent  = fcScores.filter(s => s === 'skip').length;
  }
}
```

- [ ] **Step 3: Update `fcAdvance()` to pass the right scores to endSession**

Find:
```javascript
function fcAdvance() {
  if (fcIndex >= fcDeck.length - 1) { endSession(fcScores); return; }
```

Replace that one line with:
```javascript
function fcAdvance() {
  if (fcIndex >= fcDeck.length - 1) {
    endSession(activeMode === 'qfc' ? { right: qfcRight, wrong: qfcWrong } : fcScores);
    return;
  }
```

- [ ] **Step 4: Update `endSession()` to handle QFC scores object**

Find the start of `endSession`:
```javascript
async function endSession(scores) {
  const right    = scores.filter(s => s === 'right').length;
  const wrong    = scores.filter(s => s === 'wrong').length;
  const skip     = scores.filter(s => s === 'skip' || s === null).length;
  const answered = right + wrong;
  const pct      = answered > 0 ? Math.round((right / answered) * 100) : 0;
```

Replace **only those opening variable-assignment lines** (stop before `document.getElementById('fin-right')` — do NOT touch anything below). The surrounding animation and API-counter code is unchanged:
```javascript
async function endSession(scores) {
  // NOTE: activeMode is still 'qfc'/'fc'/'mc' here — it is only reset by the
  // next startFC/startMC/startQFC call. This branch relies on that assumption.
  let right, wrong, skip;
  if (activeMode === 'qfc') {
    // scores is { right: qfcRight, wrong: qfcWrong } for QFC sessions
    right = scores.right;
    wrong = scores.wrong;
    skip  = 0;
  } else {
    right = scores.filter(s => s === 'right').length;
    wrong = scores.filter(s => s === 'wrong').length;
    skip  = scores.filter(s => s === 'skip' || s === null).length;
  }
  const answered = right + wrong;
  const pct      = answered > 0 ? Math.round((right / answered) * 100) : 0;
```

- [ ] **Step 5: Add QFC case to the summary mode badge**

Find:
```javascript
  if (activeMode === 'fc') {
    badge.innerHTML = `<svg viewBox="0 0 18 18" ...> Flash Cards`;
  } else {
    badge.innerHTML = `<svg viewBox="0 0 18 18" ...> Multiple Choice`;
  }
```

Replace with:
```javascript
  if (activeMode === 'fc') {
    badge.innerHTML = `<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="1" y="3" width="16" height="12" rx="2"/><line x1="1" y1="7" x2="17" y2="7"/></svg> Flash Cards`;
  } else if (activeMode === 'qfc') {
    badge.innerHTML = `<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="1" y="2" width="16" height="14" rx="2"/><line x1="5" y1="7" x2="13" y2="7"/><line x1="5" y1="11" x2="10" y2="11"/></svg> Exam Flashcards`;
  } else {
    badge.innerHTML = `<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="4.5" cy="5" r="1.2" fill="currentColor" stroke="none"/><line x1="7.5" y1="5" x2="17" y2="5"/><circle cx="4.5" cy="9" r="1.2" fill="currentColor" stroke="none"/><line x1="7.5" y1="9" x2="17" y2="9"/><circle cx="4.5" cy="13" r="1.2" fill="currentColor" stroke="none"/><line x1="7.5" y1="13" x2="17" y2="13"/></svg> Multiple Choice`;
  }
```

- [ ] **Step 6: Update `playAgain()` for QFC**

Find:
```javascript
function playAgain() {
  if (activeMode === 'fc') startFC();
  else startMC();
}
```

Replace with:
```javascript
function playAgain() {
  if (activeMode === 'fc')  startFC();
  else if (activeMode === 'qfc') showQFCSelect(); // re-renders domain counts
  else startMC();
}
```

- [ ] **Step 7: Verify the full QFC flow with stub data**

Refresh `http://localhost:4400`. Walk through this checklist:

1. Home → tap "Exam Flashcards" → selector screen appears with 8 tiles ✓
2. Tap "Clinical Evaluation" → flashcard screen, front says **"Concept"**, nav says **"Exam Flashcards"** ✓
3. Tap card to flip → back says **"Key Learning"**, shows explanation ✓
4. Click **✓ Right** → advances to next card; right counter increments ✓
5. Go back to start a new session with multiple cards; click **✗ Wrong** on the first card → wrong counter increments; verify `fcDeck.length` grew by 1 (open DevTools console and type `fcDeck.length` before and after) ✓
6. Play through all stub cards until session ends → summary screen shows **"Exam Flashcards"** badge ✓
7. Click **Play Again** → returns to selector screen ✓
8. Start a regular **Flash Cards** session → front says **"Term"**, nav says **"Flash Cards"** — existing mode unaffected ✓

- [ ] **Step 8: Commit**

```bash
git add index.html
git commit -m "feat: add QFC resurface loop, grading stats, play-again, summary badge"
```

---

## Task 10: Embed full EXAM_CARDS from reviewed JSON

> **Prerequisite:** Task 3 (Marc's review) must be complete before this task.

**Files:**
- Modify: `index.html` — replace stub `EXAM_CARDS` with full approved deck
- Create: `scripts/embed_exam_cards.js` (one-time helper)

- [ ] **Step 1: Write the embed helper**

Create `scripts/embed_exam_cards.js`:
```javascript
// Converts flashcards_review.json (approved cards) to a JS const declaration
// Usage: node scripts/embed_exam_cards.js
const fs = require('fs');
const cards = JSON.parse(fs.readFileSync('scripts/flashcards_review.json', 'utf8'));
const kept  = cards.filter(c => c.keep && c.concept_title && c.concept_explanation);

// Remove fields not needed in the browser
const clean = kept.map(({ id, category, concept_title, concept_explanation }) =>
  ({ id, category, concept_title, concept_explanation })
);

const js = `const EXAM_CARDS = ${JSON.stringify(clean, null, 2)};`;
fs.writeFileSync('scripts/exam_cards_output.js', js);
console.log(`Written ${clean.length} cards to scripts/exam_cards_output.js`);
```

- [ ] **Step 2: Run it**

```bash
node scripts/embed_exam_cards.js
```

Expected: `Written ~550 cards to scripts/exam_cards_output.js`

- [ ] **Step 3: Replace the stub EXAM_CARDS in index.html**

In `index.html`, find and **select everything** from the comment line through the closing `];`:
```
// ── EXAM CARDS (stub — replaced in Task 10 with full preprocessed deck) ───────
const EXAM_CARDS = [
  ...10 stub entries...
];
```

Replace that entire block (comment + declaration + closing `];`) verbatim with the full contents of `scripts/exam_cards_output.js`, which begins with:
```javascript
const EXAM_CARDS = [
```
Add a replacement comment line above it:
```javascript
// ── EXAM CARDS ────────────────────────────────────────────────────────────────
const EXAM_CARDS = [ ...full data from exam_cards_output.js ... ];
```
Do **not** double the `const` keyword — `exam_cards_output.js` already contains it.

- [ ] **Step 4: Verify counts on selector screen**

Refresh `http://localhost:4400`. Tap "Exam Flashcards". Verify domain tiles show realistic card counts (e.g., Treatment should have 50–100+ cards, not 1–2).

- [ ] **Step 5: Commit**

```bash
git add index.html scripts/embed_exam_cards.js
git commit -m "feat: embed full EXAM_CARDS deck from reviewed preprocessing output"
```

---

## Task 11: Final QA + deploy

- [ ] **Step 1: Full regression check**

Open `http://localhost:4400` and verify each mode still works:

| Mode | Check |
|------|-------|
| Flash Cards | Start session, flip a card, grade right/wrong, reach summary |
| Multiple Choice | Start session, answer a question, reach summary |
| Question Lookup | Paste a question stem, get result |
| Key Terms by Diagnosis | Navigate to screen, scroll through all groups |
| Exam Flashcards | Pick a domain, flip cards, wrong answer resurfaces, session completes, Play Again → selector |

- [ ] **Step 2: Verify Mix All tile count**

On the selector screen, "Mix All" should show the total kept card count. Confirm it matches `EXAM_CARDS.length` in the console:
```javascript
// In browser DevTools console:
console.log(EXAM_CARDS.length);
```

- [ ] **Step 3: Push to deploy**

```bash
git push origin main
```

Vercel auto-deploys on push. Confirm at `https://theory-terms-quiz.vercel.app` within ~60 seconds.

- [ ] **Step 4: Smoke test on deployed URL**

Navigate to the live site. Tap Exam Flashcards, pick a domain, flip a card, confirm it works end-to-end in production.
