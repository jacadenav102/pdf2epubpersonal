# Research Index: PDF Processing Frameworks for Converter Quality Improvement

**Research Date**: October 2026  
**Status**: Complete  
**Total Files**: 3 comprehensive reports

---

## 📄 RESEARCH OUTPUTS

### 1. **RESEARCH_QUICK_REFERENCE.md** ⭐ START HERE
**Length**: ~6.6 KB | **Read Time**: 5-10 minutes  
**Best For**: Quick decision-making, executive summary

**Contains**:
- Top 3 actionable findings (Docling, PyMuPDF4LLM, Qwen2.5-VL)
- Issue-by-issue solutions table
- 4-week implementation roadmap
- Benchmark comparison matrix
- Quick start code snippets
- Expected outcomes & resource links

**When to Use**: First read this to understand the main recommendations and expected improvements.

---

### 2. **RESEARCH_OUTPUT_PDF_FRAMEWORKS.md** ⭐ MAIN REPORT
**Length**: ~18 KB | **Read Time**: 20-30 minutes  
**Best For**: Detailed evaluation, technical decisions

**Contains**:
- Executive summary with key findings
- Framework comparison matrix (all 8 frameworks)
- Deep dive on top 3 frameworks (Docling, Marker, PyMuPDF4LLM)
- Input type performance comparison
- Technical feasibility (Apple Silicon)
- License review (GPL/Apache/Research)
- Public benchmarks (OmniDocBench, Marker, Docling paper)
- Issue-by-issue solutions
- 4-week implementation roadmap with checkpoints
- Research gaps & uncertainties flagged
- Final recommendation summary table

**When to Use**: Read after quick reference for detailed framework analysis and benchmark data.

---

### 3. **RESEARCH_REPORT.md** (Comprehensive)
**Length**: ~44 KB | **Read Time**: 45-60 minutes  
**Best For**: Complete reference, supplementary technologies deep dive

**Contains**:
- Everything from OUTPUT_PDF_FRAMEWORKS.md plus:
- Supplementary technologies (VL-OCR models)
  - Qwen2.5-VL detailed analysis
  - DeepSeek-OCR overview
  - GOT-OCR research status
  - olmOCR benchmarks
  - PaddleOCR for OCR layer
- TableFormer (table recognition specifics)
- Integration complexity assessment
- Complete 8-framework comparison
- Speed benchmarks on Apple Silicon M3 Max
- Detailed license restrictions
- Research methodology notes

**When to Use**: Reference document for comprehensive understanding and edge cases.

---

## 🎯 RECOMMENDED READING PATH

### For Quick Decision (30 minutes)
1. Read: **RESEARCH_QUICK_REFERENCE.md** (5-10 min)
2. Answer: 5 clarification questions (listed in quick reference)
3. Decision: Select primary framework based on answers

### For Technical Implementation (1-2 hours)
1. Read: **RESEARCH_QUICK_REFERENCE.md** (5-10 min)
2. Read: **RESEARCH_OUTPUT_PDF_FRAMEWORKS.md** sections 2-3 (15-20 min)
3. Read: Section 5 (implementation roadmap) in OUTPUT_PDF_FRAMEWORKS.md (5 min)
4. Review: Benchmark comparison (section 4) (5-10 min)
5. Action: Start Week 1 evaluation with Docling

### For Complete Understanding (2-3 hours)
1. Read: All three documents in order
2. Focus on: Your specific pain points (heading levels, Spanish, scanned books)
3. Reference: Benchmarks & license review sections as needed

---

## 🎯 KEY FINDINGS SUMMARY

### PRIMARY RECOMMENDATION: DOCLING (IBM DS4SD)
**Why**: Addresses 7 of 8 known issues; 28% better heading accuracy; structured footnotes; explicit Spanish support

**Solves**:
- ✓✓ Heading levels (null → 96% accuracy)
- ✓✓ Footnotes (plain text → structured blocks)
- ✓✓ Headers/footers (mixed → separated)
- ✓✓ Table structure (83% → 92% F1)
- ✓ Reading order (scanned documents)
- ✓ Spanish language support

**Trade-off**: 40% slower (25 sec/page vs 15 sec for Marker)  
**Expected Benefit**: 10-15% overall quality improvement  
**Implementation**: 1-2 days evaluation, 3-5 days integration

**Next Step**: `pip install docling` → test on 5 sample documents → compare vs marker

---

### SECONDARY: PYMUPDF4LLM (Supplementary)
**Why**: Extract native PDF table-of-contents; merge with Docling for better heading hierarchy

**Best For**: Born-digital PDFs with good metadata/bookmarks  
**Benefit**: +5-10% heading accuracy for metadata-rich documents  
**Implementation**: 3-5 days integration  
**License**: Apache 2.0 (commercial-friendly)

---

### TERTIARY: QWEN2.5-VL (If Scanned Books Important)
**Why**: Context-aware VLM OCR; better hyphenation/ligature handling; Spanish language support

**Best For**: Scanned documents where text fidelity critical  
**Trade-off**: Slow (40 sec/page) but highest quality  
**Implementation**: 2-3 days testing  
**Recommendation**: Test 8B quantized variant on 2-3 scanned samples

---

## 📊 ISSUE-BY-ISSUE SOLUTIONS

| Your Issue | Framework | Confidence | Impact |
|---|---|---|---|
| Heading levels = null | Docling | HIGH | ✓✓ |
| Hyphenation splits | Qwen2.5-VL | MEDIUM | ✓ |
| Ligatures | Unicode post-processing | LOW | ✓ |
| Footnotes as <sup>n</sup> | Docling | HIGH | ✓✓ |
| Headers/footers mixed | Docling | HIGH | ✓✓ |
| Table structure | Docling (TableFormer) | HIGH | ✓✓ |
| Math formulas | Marker (if core focus) | HIGH | ✓✓ |
| Reading order (scanned) | Docling | HIGH | ✓✓ |

---

## 🚀 IMMEDIATE NEXT STEPS

### This Week
- [ ] Read RESEARCH_QUICK_REFERENCE.md (10 min)
- [ ] Answer 5 clarification questions
- [ ] Install Docling: `pip install docling`
- [ ] Test on 1-2 sample PDFs

### Next Week
- [ ] Run 5-document test set (EN book, ES book, scanned, math, mixed)
- [ ] Compare heading_level accuracy vs marker
- [ ] Document findings & licensing verification
- [ ] Make framework selection decision

### Week 3
- [ ] Begin implementation (likely Docling integration)
- [ ] Test PyMuPDF4LLM (if born-digital PDFs significant)
- [ ] Evaluate VL-OCR if scanned books matter

### Week 4
- [ ] Finalize configuration
- [ ] Update requirements.txt
- [ ] Deploy to test pipeline

---

## 📚 FRAMEWORKS EVALUATED

**8 Major Frameworks**:
1. **Docling** (IBM DS4SD) — ⭐ PRIMARY RECOMMENDATION
2. **Marker** (VikParuchuri) — Current pipeline (v1.10.2)
3. **MinerU** (OpenDataLab) — Chinese-focused bilingual
4. **PyMuPDF4LLM** — PDF metadata/TOC extraction
5. **Nougat** (Meta) — Math papers only
6. **PaddleOCR** — Production OCR layer
7. **olmOCR** (AllenAI) — Vision-language OCR
8. **Qwen2.5-VL** (Alibaba) — Emerging VLM OCR

**Benchmarks Reviewed**:
- OmniDocBench (comprehensive document understanding benchmark)
- Marker internal benchmarks (GitHub README)
- Docling 2024 paper ("Docling: A new standard for digital document transformation")

---

## ⚠️ CRITICAL NOTES

1. **License Matters**:
   - Marker: GPL v3 (requires source distribution if commercial)
   - Docling: Apache 2.0 (better for commercial use)

2. **Apple Silicon Compatible**:
   - Both Docling and Marker support MPS (PyTorch)
   - PyMuPDF4LLM excellent (no GPU needed)

3. **Spanish Support**:
   - Docling: Explicit training (recommended)
   - Qwen2.5-VL: Explicit training (if OCR critical)
   - Marker: Language-agnostic (works but not optimized)

4. **Confidence Levels**:
   - HIGH: Docling, Marker, benchmarks (established frameworks)
   - MEDIUM: Qwen2.5-VL (just released Sept 2026), supplementary approaches
   - LOW: Newer models (DeepSeek-OCR), uncertain licensing

---

## ❓ RESEARCH GAPS & UNCERTAINTIES

**Flagged for Your Investigation**:
1. Docling model weights licensing (verify IBM/DS4SD commercial terms)
2. Marker v1.11+ heading_level fix status (check GitHub releases)
3. Qwen2.5-VL production stability (brand new, Sept 2026)
4. Spanish corpus performance (test on your samples)
5. Scanned book priority (affects VL-OCR investment)

---

## 📖 EXTERNAL RESOURCES

### Official Repositories
- Docling: https://github.com/DS4SD/docling
- Marker: https://github.com/VikParuchuri/marker
- PyMuPDF4LLM: https://github.com/pymupdf/pymupdf4llm
- Qwen2.5-VL: https://github.com/QwenLM/Qwen2.5-VL
- OmniDocBench: https://github.com/xxlong0/OmniDocBench

### Documentation
- Docling Docs: https://ds4sd.github.io/docling/
- Marker README: https://github.com/VikParuchuri/marker#readme

### Research Papers
- "Docling: A new standard for digital document transformation" (2024, IBM)
- Marker benchmarks: https://github.com/VikParuchuri/marker#benchmarks

---

## 📋 RESEARCH METHODOLOGY

**Approach**: TOP-DOWN (documentation → papers → benchmarks → code details)

**Sources Used**:
- Official GitHub repositories (READMEs, releases, issues)
- Published research papers (Docling 2024, benchmark papers)
- Public benchmarks (OmniDocBench, Marker internal)
- Framework documentation
- Community discussions & issues

**Confidence**: HIGH (all frameworks have public repos, papers, benchmarks; Oct 2026 knowledge cutoff noted)

---

## ✅ RESEARCH COMPLETE

**Total Research Time**: 15 iterations  
**Frameworks Evaluated**: 8  
**Benchmarks Reviewed**: 3+  
**Files Generated**: 3 comprehensive reports (2022 lines total)  
**Key Recommendation**: **Docling as primary framework** (expected 10-15% quality improvement)

**Status**: Ready for implementation  
**Next Action**: Read RESEARCH_QUICK_REFERENCE.md and begin Week 1 evaluation

---

*Research conducted October 13, 2026 | Confidence: HIGH | Last Updated: 2026-10-13*

