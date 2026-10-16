# EPUB Quality: Quick Reference Cheat Sheet
**October 2026** | One-page reference for validation, tools, and metrics

---

## 🎯 Three-Layer Quality Strategy

```
RAW EPUB (Pandoc) 
    ↓
VALIDATION LAYER (epubcheck + ACE)
    ├─ Structural: OPF, metadata, XHTML well-formedness
    ├─ Accessibility: Image alt-text, heading hierarchy, language tags
    └─ Output: PASS / WARNINGS / ERRORS
    ↓
QUALITY SCORING (Automated heuristic, 100-point scale)
    ├─ Structural (25 pts): epubcheck results
    ├─ Semantic (20 pts): Headings, images, footnotes
    ├─ Accessibility (15 pts): ACE violations
    ├─ Content (15 pts): TOC, citations, headers
    ├─ Reader compat (15 pts): Math, fonts, footnotes
    ├─ Performance (10 pts): File size, resources
    └─ Grade: 90+ EXCELLENT | 70-89 GOOD | 50-69 FAIR | <50 POOR
    ↓
SPOT-CHECK (Manual on 10% sample)
    ├─ Calibre Viewer (baseline)
    ├─ Apple Books (strictness test)
    └─ KOReader (math test)
```

---

## 🔧 INSTALLATION

```bash
pip install epubcheck
npm install -g @daisy/ace
pandoc --version  # Must be 3.9+
```

---

## 📋 PANDOC RECOMMENDED FLAGS

```bash
pandoc --from=markdown --to=epub3 \
  --mathml --toc --toc-depth=2 --split-level=1 \
  --resource-path=images:. --reference-location=block \
  --css=style.css --metadata-file=desc.json \
  input.md -o output.epub
```

**Critical**: `--mathml`, `--split-level=1`, `--reference-location=block`

---

## ✅ VALIDATION

```bash
# Structural validation
epubcheck output.epub --json report.json

# Accessibility check
ace output.epub --output ace_report
```

---

## 🎲 QUALITY SCORECARD (100 pts)

| Category | Pts | Auto | Focus |
|----------|-----|------|-------|
| Structural | 25 | ✅ | epubcheck errors/warnings |
| Semantic | 20 | ✅ | Headings, images, footnotes |
| Accessibility | 15 | ✅ | ACE violations, language |
| Content | 15 | ⚠️ | TOC, citations, leakage |
| Reader Compat | 15 | ⚠️ | Math, fonts, footnotes |
| Performance | 10 | ✅ | File size, resources |

**Grade**: 90+ EXCELLENT | 70-89 GOOD | 50-69 FAIR | <50 POOR

---

## 📊 READER COMPATIBILITY

| Feature | Apple | Kobo | KOReader | Calibre | Kindle |
|---------|-------|------|----------|---------|--------|
| MathML | ✅ | ✅ | ✅✅ | ✅ | ❌ |
| Pop-up notes | ✅ | ✅ | ✅ | ✅ | ❌ |
| Fonts | ⚠️ | ✅ | ✅✅ | ✅✅ | ⚠️ |

**Test on**: Calibre (baseline) → Apple Books (strict) → KOReader (math)

---

## 🐛 QUICK FIXES

| Error | Fix | Time |
|-------|-----|------|
| Missing language | Add `"language": "es"` to metadata | 5 min |
| Resource not found | Use `--resource-path=images:.` | 5 min |
| Invalid XHTML | Validate markdown before Pandoc | 10 min |
| Missing alt-text | Add post-processing for images | 30 min |
| Heading skips | Fix markdown H1/H2/H3 order | 20 min |

---

## 🚀 WEEK 1 (7 hrs)

- [ ] Install tools + epubcheck (2 hrs)
- [ ] Add language metadata (1 hr)
- [ ] Install + run ACE (1.5 hrs)
- [ ] Test on 5 books (2 hrs)
- [ ] Verify 5 critical questions (0.5 hrs)

**Output**: Baseline quality report

---

## ❓ CRITICAL QUESTIONS

1. Does Marker-pdf preserve page numbers?
2. When does custom post-processing run?
3. Which Pandoc flags are currently active?
4. What's OCR quality baseline?
5. Is legacy md2epub builder used?

---

## 🎓 STANDARDS & TOOLS

| Resource | URL |
|----------|-----|
| EPUB 3.3 | https://www.w3.org/TR/epub-33/ |
| EPUB Accessibility | https://www.w3.org/TR/epub-a11y-11/ |
| Pandoc | https://pandoc.org/MANUAL.html |
| epubcheck | https://github.com/w3c/epubcheck |
| DAISY Ace | https://github.com/daisy/ace |

---

**Full documentation**: See EPUB_Research_Report.md, Executive_Summary.md, Implementation_Guide.md

