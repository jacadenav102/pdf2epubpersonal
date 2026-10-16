# Quick Reference: Cloud Services Visual Guide

## COST COMPARISON (300-page book)

```
$0          LlamaParse ▮▮▮▮▮▮▮▮▮▮
            Marker (OSS) ▮▮▮▮▮▮▮▮▮▮
$0.30-0.60  Azure AI ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
            LlamaParse ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
$0.40-0.80  Hybrid (Marker+Azure+Claude selective)
$1.50-3.00  Mathpix ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
$2.25-6.75  Gemini (full) ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
$2.40-3.90  Claude (full) ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
$3-9        Mistral ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
$4.50-30    AWS Textract ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
$5.30-8.30  GPT-4o (full) ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
$20-50+     Reducto ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
$45-90      Google Doc AI ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
```

---

## QUALITY SCORECARD (By Feature)

```
                    Structure  Text    Tables  Math   Footnotes  Spanish  Speed   Cost
                    ─────────  ──────  ──────  ─────  ─────────  ───────  ─────  ─────
LlamaParse          ████░░░░░  ████░░░ ████░░░ ██░░░  ███░░░░░░  ████░░░  ████░░ ★★★★★
Azure AI            ████░░░░░  ████░░░ ████░░░ ██░░░  ███░░░░░░  ████░░░  ███░░░ ★★★★★
Marker (local)      ████░░░░░  ████░░░ ███░░░░ ███░░░ ███░░░░░░  ████░░░  █████░ ★★★★★
Mathpix             ████░░░░░  ████░░░ ████░░░ █████░ ████░░░░░  ██░░░░░░ ███░░░ ★★★☆☆
Claude              █████░░░░  █████░░ ████░░░ ████░░ ████░░░░░  █████░░░ ██░░░░ ★★☆☆☆
Gemini              █████░░░░  █████░░ ████░░░ ████░░ ████░░░░░  █████░░░ ███░░░ ★★☆☆☆
GPT-4o              █████░░░░  █████░░ ████░░░ ████░░ ████░░░░░  █████░░░ ███░░░ ★☆☆☆☆
AWS Textract        ██░░░░░░░  ███░░░░ ████░░░ ░░░░░░ ░░░░░░░░░  ████░░░  █████░ ★★★☆☆
Unstructured        ████░░░░░  ████░░░ ████░░░ ██░░░  ███░░░░░░  ████░░░  ███░░░ ★★★★☆
Google Doc AI       ███░░░░░░  ███░░░░ ███░░░░ ██░░░  ██░░░░░░░  ████░░░  ███░░░ ★☆☆☆☆

Legend: ████ = Excellent, ███ = Good, ██ = Fair, █ = Poor, ░ = Not supported
Cost:   ★★★★★ = <$1, ★★★★ = $1-2, ★★★ = $2-5, ★★ = $5-10, ★ = >$10
```

---

## FEATURE PRESENCE MATRIX

```
Feature              Mathpix  Azure   Google  AWS     Claude  Gemini  Unstructured
─────────────────    ───────  ────    ──────  ────    ──────  ──────  ────────────
Headings (levels)    ✓✓       ✓✓      ✓       ✗       ✓✓      ✓✓      ✓✓
Tables               ✓✓       ✓✓      ✓✓      ✓       ✓✓      ✓✓      ✓✓
Footnotes            ✓        ✓       ✗       ✗       ✓✓      ✓✓      ✓
LaTeX math           ✓✓✓      ✓       ✓       ✗       ✓✓      ✓✓      ✓
Reading order        ✓✓       ✓✓      ✓       ✓       ✓✓      ✓✓      ✓✓
Scanned OCR          ✓        ✓✓✓     ✓       ✓✓      ✓✓      ✓✓      ✓
Bibliography         ✗        ✗       ✗       ✗       ✓       ✓       ✗
Spanish support      ?        ✓✓      ✓✓      ✓✓      ✓✓      ✓✓      ✓
Python SDK           ✓        ✓✓      ✓✓      ✓✓      ✓✓      ✓✓      ✓✓
Batch processing     ✓        ✓✓      ✓       ✓✓      ✓       ✓       ✓
```

---

## DECISION TREE

```
START: "What's my primary constraint?"
│
├─ COST ("Every $0.10 matters for 1000s of books")
│  └─→ LlamaParse ($0.30-0.60/book)
│      Or: Marker local + Azure fallback ($0.40-0.80)
│
├─ QUALITY ("Must be perfect, cost secondary")
│  └─→ Claude full extraction ($2.40-3.90/book)
│      Or: Hybrid (Marker + Claude selective) ($0.40-0.80)
│
├─ SPEED ("Need results NOW, cost/quality less critical")
│  └─→ AWS Textract ($4.50-30/book, fast)
│      Or: Claude ($2-3s per page)
│
├─ SCANNED DOCUMENTS ("Many degraded PDFs")
│  └─→ Azure AI Read Model ($0.30-0.60/book)
│      Or: AWS Textract ($4.50-30/book)
│
├─ MATH HEAVY ("Lots of equations")
│  └─→ Mathpix ($1.50-3.00/book)
│      Or: Claude selective ($0.01-0.05/page)
│
├─ SPANISH ("Critical language support")
│  └─→ Azure AI or Claude or Gemini (all ✓✓)
│      Test with 20 sample pages first
│
├─ PRIVACY ("Can't send to cloud")
│  └─→ Unstructured.io (self-hosted, $0)
│      Or: Marker local ($0)
│
└─ FLEXIBILITY ("Need custom extraction logic")
   └─→ Claude with custom prompts ($2.40-3.90/book)
       Or: Mistral ($3-9/book)
```

---

## PIPELINE TEMPLATES

### Template 1: BUDGET BASELINE
```
┌─────────────────┐
│  Marker (local) │  ($0)
└────────┬────────┘
         │ Problem pages
         ▼
    ┌──────────┐
    │ LlamaParse│  ($0.30-0.60)
    └─────┬────┘
          │
          ▼
    ┌──────────────┐
    │ Post-process │
    │ (regex/link) │
    └─────┬────────┘
          │
          ▼
    ┌───────────────┐
    │ Pandoc → EPUB │
    └───────────────┘

Total cost: $0.30-0.60/book | Quality: Good
```

### Template 2: RECOMMENDED (Best Balance)
```
┌──────────────────┐
│ Marker (local)   │  ($0)
└────────┬─────────┘
         │ 10% problem pages
         ▼
    ┌────────────────┐
    │ Azure AI Read  │  ($0.15-0.30)
    │ (OCR issues)   │
    └────────┬───────┘
             │ 5% complex pages
             ▼
        ┌───────────┐
        │ Claude    │  ($0.01-0.05)
        │ (refine)  │
        └─────┬─────┘
              │
              ▼
        ┌──────────────┐
        │ Post-process │
        │ (regex/link) │
        └──────┬───────┘
               │
               ▼
        ┌───────────────┐
        │ Pandoc → EPUB │
        └───────────────┘

Total cost: $0.40-0.80/book | Quality: Very High
```

### Template 3: MAXIMUM QUALITY
```
┌──────────────────────┐
│ Claude Full Extract  │  ($2.40-3.90)
│ (page image → MD)    │
└──────────┬───────────┘
           │
           ▼
    ┌──────────────┐
    │ Post-process │
    │ (regex/link) │
    └──────┬───────┘
           │
           ▼
    ┌───────────────┐
    │ Pandoc → EPUB │
    └───────────────┘

Total cost: $2.40-3.90/book | Quality: Excellent
```

### Template 4: SCANNED HERITAGE
```
┌─────────────────────┐
│ Azure AI Read Model │  ($0.15-0.30)
│ (OCR specialist)    │
└──────────┬──────────┘
           │
           ▼
    ┌────────────────────┐
    │ Claude Selective   │  ($0.01-0.03)
    │ (footnotes, refs)  │
    └────────┬───────────┘
             │
             ▼
        ┌──────────────┐
        │ Post-process │
        │ (regex/link) │
        └──────┬───────┘
               │
               ▼
        ┌───────────────┐
        │ Pandoc → EPUB │
        └───────────────┘

Total cost: $0.30-0.60/book | Quality: Excellent (OCR focus)
```

---

## SERVICE SPOTLIGHT

### ⭐ Azure AI Document Intelligence
```
Perfect for:     Scanned books, Spanish support critical
Price:           $0.30-0.60/book (excellent value)
Spanish:         ✓✓ Excellent
Scanned quality: ✓✓✓ Best-in-class
Headings:        ✓✓ Via role detection
Footnotes:       ✓ Via footnote role
Math:            ✓ Basic
Python SDK:      ✓✓ Excellent
Data retention:  No retention (opt), ✓ Privacy-friendly
```

### ⭐ LlamaParse (Cost Leader)
```
Perfect for:     Budget-conscious, born-digital books
Price:           $0.30-0.60/book (cheapest mainstream)
Spanish:         ✓ Multilingual claim (test first)
Structure:       ✓✓ Good partitioning
Headings:        ✓✓ Heading hierarchy preserved
Python SDK:      ✓ Via llama-index
Maturity:        Medium (good but newer than competitors)
```

### ⭐ Claude (LLM Champion)
```
Perfect for:     Complex layouts, refinement, maximum quality
Price:           $2.40-3.90/book (expensive but flexible)
Spanish:         ✓✓✓ Native multilingual
Quality:         ✓✓✓ Best overall output
Footnotes:       ✓✓ Can structure with prompts
Math:            ✓✓ Excellent vision-based
Hallucination:   Risk; best for refinement not full extraction
```

### ⭐ Mathpix (Math Specialist)
```
Perfect for:     Math-heavy papers, equations
Price:           $1.50-3.00/book
Spanish:         ? Limited documentation
LaTeX:           ✓✓✓ Best-in-class
MathML:          ✓ Supported
Equations:       ✓✓✓ Specialized recognition
Best use:        Specific papers not bulk books
```

---

## CRITICAL PATHS: What Can Go Wrong?

```
Scenario: "I chose service X but it fails"

┌─ Service Unavailable
│  └─ Fallback ready? (need backup in pipeline)
│
├─ Spanish Language Issues
│  └─ Didn't test on Spanish corpus first
│     Solution: Always test 20+ Spanish pages
│
├─ Cost Higher Than Expected
│  └─ Didn't account for variable pricing
│     Solution: Monitor usage logs, set alerts
│
├─ Hallucinations in Tables
│  └─ Used LLM for full extraction
│     Solution: Use LLM selective, Mathpix/Azure for tables
│
├─ Footnotes Lost
│  └─ Service doesn't preserve structure
│     Solution: Post-process via regex + Claude
│
├─ Scanned Docs Fail
│  └─ Used general service instead of OCR specialist
│     Solution: Fallback to Azure or AWS
│
└─ Math Looks Wrong
   └─ Used non-specialist service
      Solution: Use Mathpix or Claude for math pages
```

---

## MONTHLY COST CALCULATOR

```
For 100 books (~30,000 pages):

Strategy 1: LlamaParse Only
  100 × $0.30-0.60 = $30-60/month

Strategy 2: Local Marker Only
  100 × $0 = $0/month (compute costs only)

Strategy 3: RECOMMENDED (Marker + Azure + Claude)
  30,000 × $0.0015 (Azure 10%) = $45
  30,000 × $0.008 (Claude 5%) = $12
  Total: $57/month ← Break-even point

Strategy 4: Full Azure
  30,000 × $0.0015 = $45/month

Strategy 5: Full Claude
  30,000 × $0.008 = $240/month

Strategy 6: Full Mathpix
  30,000 × $0.005 = $150/month
```

---

## SPANISH LANGUAGE CONFIDENCE

```
Service          Documented?  Tested?  Confidence  Note
─────────────    ───────────  ───────  ──────────  ────
Azure AI         YES          HIGH     ✓✓          Safe choice
Google Doc AI    YES          GOOD     ✓✓          Safe choice
AWS Textract     YES          HIGH     ✓✓          Safe choice
Claude           Native       HIGH     ✓✓✓         Best LLM option
Gemini           Native       HIGH     ✓✓✓         Best LLM option
Mathpix          LIMITED      UNKNOWN  ⚠           Test first
LlamaParse       IMPLIED      UNKNOWN  ⚠           Test first
Unstructured     YES          GOOD     ✓           Likely works
Mistral          Native       HIGH     ✓✓✓         Native support

ACTION: Always validate with 20+ Spanish pages before production
```

---

## ONE-PAGE DECISION SUMMARY

| If You Want... | Choose | Cost | Why |
|---|---|---|---|
| Lowest cost | LlamaParse | $0.30-0.60 | Commodity pricing |
| Best OCR | Azure AI | $0.30-0.60 | Heritage book specialist |
| Best math | Mathpix | $1.50-3.00 | Equation specialist |
| Best quality | Claude | $2.40-3.90 | LLM superior output |
| Best balance | Marker+Azure+Claude | $0.40-0.80 | Hybrid wins |
| No cloud | Unstructured OSS | $0 | Privacy first |
| Spanish focus | Claude/Gemini | $2.25-6.75 | Native multilingual |
| Scanned books | Azure | $0.30-0.60 | OCR quality leader |

---

**Last updated:** October 2026  
**Next: Read CLOUD_SERVICES_SUMMARY.md for full details**
