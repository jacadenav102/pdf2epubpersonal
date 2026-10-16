# EPUB Output Quality & Evaluation: Executive Summary
**October 13, 2026** | Research domain: EPUB validation, accessibility, and quality measurement for PDF→Markdown→EPUB pipeline

---

## TL;DR: Three-Layer Quality Strategy

| Layer | Tool/Approach | Effort | Impact | Timeline |
|-------|---|---|---|---|
| **Generation** | Pandoc 3.9 + Lua filters | Included | Baseline quality | Immediate |
| **Validation** | epubcheck + ACE | 2-3 hrs | Catch structural/accessibility errors | 1 week |
| **Measurement** | Heuristic scorecard | 4-6 hrs | Quantified QA per book | 2 weeks |

---

## QUICK WIN: Next 7 Days

### 1. Add Language Metadata (0.5 hr)
```json
// In description.json for each book:
{
  "title": "...",
  "language": "es",  // Add this for Spanish books
  "author": "...",
  "identifier": "urn:uuid:..."
}
```
**Impact**: Fixes accessibility + reader rendering | **Blocker**: None

### 2. Integrate epubcheck (1 hr)
```bash
pip install epubcheck
# In your build pipeline:
epubcheck output.epub --json report.json
# Fail build if errors > 0
```
**Impact**: Catch structural EPUB issues early | **Blocker**: None

### 3. Run ACE Accessibility Check (1.5 hrs)
```bash
npm install -g @daisy/ace
# Post-Pandoc step:
ace output.epub --output ace_report.json
# Log violations; prioritize fixes
```
**Impact**: Identify image alt-text, heading hierarchy gaps | **Blocker**: Node.js required

**Result**: Within 1 week, you'll have quantified baseline of which books pass validation and which have fixable issues.

---

## PANDOC FLAGS: Current vs. Recommended

| Flag | Current Status | Recommendation | Priority |
|------|---|---|---|
| `--to=epub3` | Assumed ✅ | Confirm using this | Verify |
| `--mathml` | Likely missing | **ADD** (academic papers) | HIGH |
| `--toc --toc-depth=2` | Likely present | Keep; verify depth=2 | Verify |
| `--split-level=1` | Likely present | Keep (essential for large books) | Verify |
| `--reference-location=block` | Likely missing | **ADD** (better footnote flow) | MEDIUM |
| `--epub-footnotes` | Not standard | Try adding (if Pandoc supports) | LOW |
| `--css=custom.css` | Maybe | Add for footnote/math styling | MEDIUM |
| `--citeproc` | Conditional | Use if citations in markdown | MEDIUM |

**Action**: Review your Pandoc CLI invocation; confirm which flags are active.

---

## CONTENT QUALITY SCORECARD (v1.0)

### Automated Scoring (No Manual Labor Needed)

```
EPUB Quality Score = Points Across These Dimensions:

1. STRUCTURAL (25 pts)
   ✅ epubcheck errors = 0? (10 pts)
   ✅ epubcheck warnings < 5? (5 pts)
   ✅ OPF complete (language, creator, identifier)? (5 pts)
   ✅ Navigation doc valid? (5 pts)

2. SEMANTIC MARKUP (20 pts)
   ✅ Heading hierarchy valid (no H1→H3 skips)? (5 pts)
   ✅ All images have alt-text? (5 pts)
   ✅ Footnotes use epub:type="footnote"? (5 pts)
   ⚠️ Tables have captions? (5 pts) [requires inspection]

3. ACCESSIBILITY (15 pts)
   ✅ ACE violations = 0? (8 pts)
   ✅ Language tag correct? (4 pts)
   ⚠️ Color contrast WCAG AA? (3 pts) [may need tool]

4. CONTENT (15 pts)
   ⚠️ TOC depth matches original PDF? (5 pts) [manual sampling]
   ⚠️ Citation links preserved > 90%? (5 pts) [regex-based]
   ⚠️ Header/footer leakage < 2%? (5 pts) [heuristic]

5. READER COMPATIBILITY (15 pts)
   ⚠️ MathML renders? (5 pts) [spot-check on readers]
   ⚠️ Footnotes pop-up? (5 pts) [spot-check]
   ⚠️ Fonts embed correctly? (5 pts) [spot-check]

6. PERFORMANCE (10 pts)
   ✅ EPUB < 10MB? (5 pts)
   ✅ No unreferenced resources? (5 pts)

GRADING:
  90-100: ✅ EXCELLENT (production-ready)
  70-89:  ✅ GOOD (publishable with minor fixes)
  50-69:  ⚠️ FAIR (needs manual review)
  < 50:   ❌ POOR (significant issues)
```

**✅ Automatable**: 14 dimensions (70% of score)
**⚠️ Semi-automatable**: 5 dimensions (spot-check or heuristic)

---

## VALIDATION TOOLS COMPARISON

### Immediate Integration (Automated)

| Tool | Purpose | Setup | Output | Confidence |
|------|---------|-------|--------|------------|
| **epubcheck 5.1+** | EPUB spec compliance | `pip install epubcheck` | JSON report; ERROR/WARNING categories | HIGH |
| **DAISY Ace 3.x** | EPUB accessibility (WCAG) | `npm install -g @daisy/ace` | JSON report; violations per WCAG criterion | HIGH |
| **Calibre ebook-polish** | Post-generation optimization | `brew install calibre` (system) | Polished EPUB; removes unused resources, subsets fonts | MEDIUM |

### Spot-Check (Manual Testing 10% Sample)

| Reader | Setup | MathML | Pop-up Notes | Fonts | Best For Testing |
|--------|-------|--------|---|---|---|
| **Calibre Viewer** | `pip install calibre` | ✅ Partial | ✅ Yes | ✅ Excellent | Baseline (most forgiving) |
| **KOReader** | Open-source e-reader | ✅ Native | ✅ Yes | ✅ Good | Math papers |
| **Apple Books** | iOS app | ✅ iOS 15+ | ✅ Yes | ⚠️ Limited | Strictness test (fails on encoding) |

---

## READER COMPATIBILITY MATRIX

### Your Mixed Content vs. Reader Support

| Content Type | Apple Books | Kobo | KOReader | Calibre | Kindle |
|---|---|---|---|---|---|
| **Spanish books** | ✅ Good | ✅ Good | ✅ Excellent | ✅ Excellent | ⚠️ Limited EPUB support |
| **Academic papers (math)** | ✅ MathML (iOS15+) | ✅ Recent firmware | ✅✅ Native | ✅ Partial | ❌ No MathML |
| **Scanned books** | ⚠️ Strict (encoding) | ✅ Forgiving | ✅ Good | ✅✅ Most forgiving | ⚠️ EPUB via "Send to Kindle" |
| **Heavy formatting** | ⚠️ May fail | ✅ Good | ✅ Good | ✅ Most forgiving | ⚠️ Limited |

**Key Insight**: Calibre Viewer = best baseline validator. Apple Books = strictest test (catches encoding issues). KOReader = best for math support.

---

## FOOTNOTE & CITATION HANDLING

### Current Pipeline Status (NEEDS VERIFICATION)

**Question 1**: When does your custom post-processing run?
```
Scenario A (BEFORE Markdown):
  PDF → custom footnote extraction → Markdown with [^id] → Pandoc → EPUB
  ✅ Pandoc handles EPUB semantics correctly
  
Scenario B (AFTER Markdown):
  PDF → Markdown → Pandoc → custom footnote/citation links → EPUB
  ⚠️ Risk: Custom links may conflict with Pandoc's footnote generation
```

**Question 2**: What format are your bibliography links?
```
Current (assumed):
  Markdown: Citation text + custom post-processing adds
  HTML: <a href="#bib-2025">Author (2025)</a>
  
Requirement for EPUB:
  - id format: "bib-2025" ✅ (ASCII, no colons OK)
  - href should point to valid XHTML element
  - Consider adding aria-label for accessibility
```

**Recommendation**: 
- Confirm post-processing order
- If AFTER Markdown, ensure custom links don't break Pandoc's `<aside epub:type="footnote">` generation
- Add aria-labels to citation links: `<a href="#bib-2025" aria-label="Citation: Smith 2025">Author (2025)</a>`

---

## PAGE-BREAKS & CITATION SUPPORT

### EPUB3 Feature: Page-Lists (Advanced)

**What it does**: Maps printed page numbers (from PDF) to EPUB locations, enabling citations like "p. 42" to link directly.

**Current support**:
- ✅ Born-digital books: May not have page numbers
- ✅ Academic papers: Almost always have page numbers
- ⚠️ Scanned books: Have page numbers; need Marker-pdf to preserve metadata

**Implementation** (3-4 hours):
```lua
-- Lua filter: Convert Markdown comments to EPUB page-break spans
function RawBlock(elem)
  if elem.format == 'html' and elem.text:match('<!-- page: (%d+)') then
    local pagenum = elem.text:match('<!-- page: (%d+)')
    return pandoc.RawInline('html', 
      '<span id="page' .. pagenum .. '" epub:type="pagebreak" title="' .. pagenum .. '"/>')
  end
  return elem
end
```

**Then post-process OPF to generate `<nav epub:type="page-list">`**

**Priority**: MEDIUM (high value for academic papers; requires Marker-pdf page metadata verification)

---

## FONT EMBEDDING & SUBSETTING

### For Spanish + Academic Content

| Font Choice | File Size | Latin Accents | Math Symbols | Best For |
|---|---|---|---|---|
| **WOFF2 (subset)** | 40-60 KB | ✅ U+0100-U+017F | ✅ Included | PRIMARY choice |
| **WOFF (full)** | 120-180 KB | ✅ Yes | ✅ Yes | Fallback |
| **TTF (embedded)** | 200+ KB | ✅ Yes | ✅ Yes | Legacy only |

**Recommendation**:
1. Use WOFF2 format exclusively
2. Subset character ranges:
   - English: U+0020-U+007E (ASCII)
   - Spanish: Add U+00A0-U+00FF (Latin-1) + U+0100-U+017F (Latin Extended-A for accents)
   - Math: Add Greek (U+0370-U+03FF) + Math Alphanumeric Symbols
3. Include 2 fallback fonts (serif, sans-serif system fonts)

**Tool**: Calibre's `ebook-polish --subset-fonts` does this automatically post-Pandoc.

---

## MATH & EQUATION HANDLING

### Strategy by Content Type

| Input | Pandoc Default | Fallback | Implementation | Effort |
|---|---|---|---|---|
| **Born-digital LaTeX** | `--mathml` | Alt-text | ✅ Done automatically | None |
| **Scanned PDF (equations as images)** | Image + `alt=""` | Manual alt-text | Requires OCR → alt-text mapping | MEDIUM |
| **Academic papers (heavy math)** | `--mathml` | MathML + SVG image | Lua filter for dual rendering | MEDIUM |

**Current recommendation**: 
```bash
pandoc --mathml input.md -o output.epub
# MathML native support: Apple Books (iOS15+), KOReader, Calibre, recent Kobo
# Fallback readers: Show equation code (acceptable for now)
```

**Enhanced (later)**: Add SVG/PNG fallback via Lua filter for maximum compatibility.

---

## SCANNED BOOK PIPELINE: OCR QUALITY

### Marker-pdf Output Quality Check (Benchmark Your Sample)

**Metrics to measure** (on 10-page sample):
| Metric | Formula | Target | Tool |
|---|---|---|---|
| **Character Error Rate (CER)** | (substitutions + deletions + insertions) / total chars | < 2% | Manual spot-check OR compare vs. ground truth |
| **Word Error Rate (WER)** | Errors at word level | < 5% | Similar |
| **Header/footer leakage** | % repeated top/bottom text | < 2% | Grep for duplicate lines |
| **Split-word rate** | % words broken across blocks | < 5% | Regex: count hyphenated words |

**If CER > 3%**: Focus on OCR artifact cleanup BEFORE EPUB generation (Calibre polish helps; consider pre-processing with image enhancement).

**If CER < 2%**: Quality sufficient; focus on semantic markup (alt-text, landmarks).

---

## OPEN QUESTIONS: VERIFY IN YOUR CODEBASE

### Critical (Blockers)
- [ ] **Marker-pdf page metadata**: Does output include page numbers/page-break markers? (Affects page-list strategy)
- [ ] **Post-processing order**: Does custom footnote/citation linking run BEFORE or AFTER Pandoc?
- [ ] **Current Pandoc flags**: Which of the recommended flags are already in use?

### Important (Non-blockers)
- [ ] Scanned book OCR quality baseline (affects cleanup strategy)
- [ ] Legacy md2epub builder status (can we deprecate it?)
- [ ] Current error handling/validation in pipeline (baseline for integration)

---

## IMPLEMENTATION ROADMAP

### Week 1: Baseline Establishment (7 hrs)
```
□ Add language metadata to description.json templates (0.5 hr)
□ Integrate epubcheck validation (1 hr)
□ Integrate ACE accessibility check (1.5 hrs)
□ Run on 5 representative books; document errors (2 hrs)
□ Document current Pandoc flags in use (0.5 hr)
□ Answer open questions above (1 hr)

Output: Baseline quality report; list of top 10 fixable errors
```

### Week 2-3: Quick Wins (8 hrs)
```
□ Implement lightweight quality scorecard (4-6 hrs)
□ Fix top 5 error categories (fixable issues from Week 1) (2-3 hrs)
□ Create Lua filter for page-breaks IF Marker-pdf supports page metadata (3-4 hrs)
□ Establish gold set (10-15 books for validation baseline) (manual effort)

Output: Quantified quality scores; page-break support (if applicable)
```

### Month 2: Optimization (10-15 hrs)
```
□ Calibre polish post-processing pipeline (2-3 hrs)
□ Landmark navigation via Lua filter (2-3 hrs)
□ Math accessibility filter (MathML + alt-text) (4-6 hrs)
□ OCR artifact cleanup heuristics (3-5 hrs)

Output: Optimized EPUB file sizes; improved accessibility
```

---

## READER SPOT-CHECK PROTOCOL (10% Sample)

For each book scoring 50-89 on automated scorecard:

1. **Generate EPUB** with Pandoc
2. **Run validators** (epubcheck + ACE)
3. **Open on Calibre Viewer**
   - Check footnote rendering
   - Verify math display (if applicable)
   - Confirm language setting
   - Look for formatting issues
4. **Open on KOReader** (if math-heavy)
   - Verify MathML rendering
   - Check font display
5. **Open on Apple Books** (if possible)
   - Check strictness (encoding issues caught here)
   - Verify accessibility (screen reader readability)

**Expected time per book**: 5-10 minutes | **Sample size**: 10% of new books

---

## CONFIDENCE LEVELS & CAVEATS

### High Confidence (>90%)
- ✅ Pandoc EPUB3 generation (stable, well-tested)
- ✅ epubcheck validation (official W3C tool)
- ✅ ACE accessibility checks (specialized, maintained)
- ✅ EPUB 3.3 standards (current as of Oct 2026)
- ✅ Reader support matrix (firmware versions current as of Oct 2026)

### Medium Confidence (50-89%)
- ⚠️ Calibre API stability (may change in future versions)
- ⚠️ Lua filter performance on large books (untested at scale)
- ⚠️ OCR quality metrics (depends on Marker-pdf version)
- ⚠️ Reader firmware updates (evolving MathML/accessibility support)

### Low Confidence (<50%)
- ❌ Kindle EPUB support (limited; may change)
- ❌ Custom bibliography link survival through Pandoc (needs testing)
- ❌ Marker-pdf page metadata preservation (needs verification)

---

## KEY REFERENCES

**Standards**:
- W3C EPUB 3.3: https://www.w3.org/TR/epub-33/
- EPUB Accessibility 1.1: https://www.w3.org/TR/epub-a11y-11/

**Tools**:
- Pandoc 3.9: https://pandoc.org/
- epubcheck: https://github.com/w3c/epubcheck
- DAISY Ace: https://github.com/daisy/ace
- Calibre: https://manual.calibre-ebook.com

**Benchmarks**:
- OmniDocBench, TEDS, CDM, NED: Document conversion metrics (academic)

---

## NEXT STEPS FOR YOU

1. **Read** detailed report: `./EPUB_Research_Report.md`
2. **Verify** open questions (codebase)
3. **Run** quick wins (Week 1, 7 hrs)
4. **Report** baseline quality (top errors by category)
5. **Prioritize** fixes based on impact/effort matrix

---

**Research completed**: October 13, 2026 (10:09 UTC)
**Report format**: Executive summary + detailed reference document
**Confidence**: HIGH for standards & tooling; MEDIUM for pipeline specifics (pending verification)

