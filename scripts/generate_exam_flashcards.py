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
