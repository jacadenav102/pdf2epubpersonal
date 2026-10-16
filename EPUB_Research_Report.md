# EPUB Output Quality, Validation & Evaluation Research Report
**October 2026** | Research Domain: EPUB output quality, validation/accessibility, and evaluation methodologies

---

## EXECUTIVE SUMMARY

This research provides a top-down analysis of how to improve EPUB output quality from a PDF→Markdown→EPUB pipeline. The findings span W3C standards compliance, Pandoc best practices, validation tooling, reader compatibility, and practical evaluation methodologies suitable for mixed input types (born-digital books, scanned documents, academic papers).

**Key Insight**: Quality improvement requires a three-pronged approach:
1. **Standards-compliant generation** (Pandoc + metadata + semantic markup)
2. **Validation & accessibility checking** (epubcheck + ACE + reader testing)
3. **Lightweight measurement** (heuristic scorecard + sample validation)

---

## PART 1: W3C EPUB 3.3 STANDARDS & ACCESSIBILITY

### A. EPUB 3.3 Core Requirements

**Source**: W3C EPUB 3.3 Specification (https://www.w3.org/TR/epub-33/)
**Confidence**: HIGH | Current standard as of October 2026

#### Essential Structural Elements:
- **Package Document (OPF)**: Metadata (title, author, language, identifier, date, rights) + manifest (content documents, images, fonts) + spine (reading order) + guide
- **Container (XML)**: Points to OPF location in `.epub` (ZIP archive)
- **XHTML Content**: Semantic markup using ARIA roles and epub:type attributes
- **Navigation Document**: TOC equivalent; replaces legacy NCX
- **Mimetype File**: Must be first file in ZIP, uncompressed, contains "application/epub+zip"

#### Critical Metadata for Mixed Content:
```xml
<!-- OPF metadata requirements -->
<dc:language>es</dc:language>  <!-- Spanish books -->
<dc:language>en</dc:language>  <!-- English books -->
<dc:creator>Author Name</dc:creator>
<dc:date>2025-10-13</dc:date>
<dc:identifier id="uuid">urn:uuid:...</dc:identifier>
<dc:rights>License/Copyright info</dc:rights>
<!-- Optional but recommended -->
<meta property="dcterms:issued">2025-10-13</meta>
<meta property="schema:accessMode">textual</meta>
<meta property="schema:accessMode">visual</meta>  <!-- for scanned books with images -->
```

#### Reading System Compatibility Considerations:
- **Apple Books**: Requires valid Package Document; strict XHTML validation
- **Kobo**: Accepts some HTML5; slower on very large EPUBs (split-level=1 helps)
- **KOReader** (open-source): Excellent MathML support, requires valid fonts
- **Calibre**: Lenient parsing; good for validation feedback
- **Kindle**: Limited EPUB support via "Send to Kindle EPUB support"; prefers PDF or MOBI

**Relevance**: Your custom post-processing (footnotes, citations) must produce valid XHTML compliant with EPUB 3.3 semantics. Pandoc's defaults are generally compliant, but Lua filters can break this.

---

### B. EPUB Accessibility 1.1 Standard

**Source**: W3C EPUB Accessibility 1.1 (https://www.w3.org/TR/epub-a11y-11/)
**Confidence**: HIGH | Current accessibility standard

#### Key Accessibility Markers for PDF→EPUB:
1. **Semantic Markup**: Use proper heading hierarchy (H1→H2→H3), not styled text
2. **Alternative Text**: All images require `<img alt="..."/>`; critical for scanned books
3. **Footnote Semantics**: Use `epub:type="noteref"` + `epub:type="footnote"` with aside element
4. **Reading Order**: Linear spine order; list items in `<nav epub:type="toc">`
5. **Language Tagging**: `<html lang="es">` for Spanish, `<html lang="en">` for English
6. **Math Accessibility**: MathML preferred over SVG/PNG (screen reader friendly)
7. **Color Accessibility**: Don't rely on color alone for citations or emphasis

#### Specific Challenges in Your Pipeline:
- **Marker-pdf OCR output**: May produce images without alt-text; needs post-processing
- **Scanned books**: Every equation image needs `<math>` alternative OR detailed alt-text
- **Citation links**: Color-coded links need aria-labels: `<a href="#bib-2025" aria-label="Citation: Author 2025">`

**Relevance**: DAISY Ace checker (see validation section) will flag accessibility gaps. Fixing these improves usability on all readers.

---

## PART 2: PANDOC EPUB GENERATION BEST PRACTICES

### A. Pandoc EPUB3 Output Options & Their Effects

**Source**: Pandoc 3.9 Documentation (https://pandoc.org/MANUAL.html), October 2026
**Confidence**: HIGH | Latest stable version

#### Recommended CLI Flags for Your Pipeline:

```bash
pandoc \
  --from=markdown \
  --to=epub3 \
  --output=output.epub \
  --metadata-file=description.json \
  --mathml \                        # MathML over SVG (accessibility)
  --toc \                            # Generate TOC from headers
  --toc-depth=2 \                    # Depth 2-3 for mixed books/papers
  --split-level=1 \                  # Chapter per H1 (critical for large books)
  --resource-path=images:. \         # Find images in ./images/ directory
  --epub-cover-image=cover.jpg \     # Cover image path
  --css=style.css \                  # Custom CSS for fonts, notes styling
  --reference-location=block \       # Footnotes at block level (better layout)
  --citeproc \                       # Process citations (if using BibTeX/CSL)
  input.md
```

#### Detailed Flag Analysis:

| Flag | Effect | Best for Your Case | Notes |
|------|--------|-------------------|-------|
| `--mathml` | Uses MathML for equations | **YES** - academic papers | Better accessibility; KOReader native support |
| `--toc` | Auto-generates TOC from headers | **YES - conditional** | Ensure Marker-pdf outputs proper H1/H2 hierarchy |
| `--toc-depth=2` | Limits TOC nesting to H1→H2 | **YES** | Prevents overwhelming TOC for papers with deep nesting |
| `--split-level=1` | One XHTML file per H1 section | **YES** - large books | Faster reader loading; enables chapter-per-file landmarks |
| `--reference-location=block` | Footnotes after paragraph/block | **YES** | Better than `document` (all at end) for reading flow |
| `--reference-location=section` | Footnotes per section | Maybe | Good for academic papers; requires H2+ structure |
| `--epub-footnotes` | Modern `<aside epub:type="footnote">` | **YES** - if available | Replaces legacy `<a>` footnote links; improves reader support |
| `--css=style.css` | Custom stylesheet | **YES** | Control footnote styling, font sizes, margins for scanned text |
| `--citeproc` | BibTeX/CSL citation processing | Maybe | Only if citations in markdown use `@key` syntax |

**Confidence**: HIGH | These are documented, stable options.

---

### B. Footnote Rendering in EPUB3

**Key Challenge**: Your post-processing links footnotes as Pandoc `[^id]` format. How does this survive Pandoc's EPUB generation?

#### Current Markdown Approach vs. EPUB Semantics:

```markdown
<!-- Your current format (post-processed) -->
This is text[^1]
[^1]: Footnote content
```

Pandoc converts this to:
```html
<p>This is text<a epub:type="noteref" href="#fn1">1</a></p>
<aside epub:type="footnote" id="fn1">
  <p>Footnote content</p>
</aside>
```

#### Three Rendering Options in Readers:

1. **Pop-up (Apple Books, Kobo recent)**
   - Tap/click `<a epub:type="noteref">` → footnote appears in overlay
   - Requires valid `epub:type` and `href=#fn` linkage
   - **Best UX** for academic papers with many citations

2. **Inline/Expanded**
   - Footnote shown below paragraph
   - Controlled by reader CSS or reader settings
   - Default in many EPUB readers

3. **End-of-section/document**
   - All footnotes gathered at section end
   - Use `--reference-location=section` or `--reference-location=document`
   - **Fallback** for older readers

#### Recommendation for Your Mixed Content:
- **Academic papers**: Use `--reference-location=section` + ensure valid `epub:type="footnote"` semantics
- **Books**: Use `--reference-location=block` for natural reading flow
- **Scanned books**: Footnotes often in margins; OCR may place them incorrectly — requires manual review

**Implementation Gap**: Your custom post-processing currently handles footnote linking via Pandoc `[^id]` syntax. Pandoc's native handling is sufficient. **However**: If your custom processing adds links to bibliography anchors (e.g., `<span id="bib-2025">`), ensure these use EPUB-valid `id` format (no colons, ASCII-safe).

**Confidence**: HIGH for standard footnote rendering; MEDIUM for custom bibliography link survival through Pandoc.

---

### C. Page-Lists, Page Breaks & Citation Support

**Critical Gap**: EPUB 3.3 supports page-lists via `<nav epub:type="page-list">` to map printed page numbers → EPUB locations. This enables citations like "Smith (2025, p. 42)" to link to exact page.

#### How Page-Lists Work:
```xml
<!-- In Navigation Document (nav.xhtml) -->
<nav epub:type="page-list">
  <ol>
    <li><a href="ch1.xhtml#page42">42</a></li>
    <li><a href="ch1.xhtml#page43">43</a></li>
  </ol>
</nav>

<!-- In content (ch1.xhtml) -->
<span id="page42" epub:type="pagebreak" title="42"/>
<span id="page43" epub:type="pagebreak" title="43"/>
```

#### Relevance to Your Pipeline:
- **Born-digital books**: Original PDFs may lack page number markers → page-list not applicable
- **Scanned books**: Original PDFs have pages → Marker-pdf should preserve page breaks via OCR metadata
- **Academic papers**: Almost always page-numbered; page-list highly valuable for citations

#### Current Status of Pandoc Support:
- **Pandoc 3.9 (current)**: Does NOT auto-generate page-lists
- **Workaround**: Use Lua filter to inject `<span epub:type="pagebreak">` before each H2/H3 (approximation) OR manually post-process Markdown with `\pagebreak` markers

#### Recommendation:
1. Extract page-break markers from Marker-pdf output (if available in metadata)
2. Inject into Markdown as `<!-- page: 42 -->` comments
3. Create Lua filter to convert to `<span epub:type="pagebreak" title="42"/>`
4. Post-process OPF manifest to include `<nav epub:type="page-list">`

**Confidence**: HIGH for EPUB standard; MEDIUM for practical implementation in Marker-pdf output (requires checking if Marker-pdf preserves page metadata).

---

### D. Landmarks & Navigation

#### EPUB3 Landmarks (Replaces Legacy Guide):
```xml
<nav epub:type="landmarks">
  <ol>
    <li><a epub:type="cover" href="cover.xhtml">Cover</a></li>
    <li><a epub:type="toc" href="nav.xhtml">Table of Contents</a></li>
    <li><a epub:type="bodymatter" href="chapter01.xhtml">Start of Book</a></li>
    <li><a epub:type="appendix" href="appendix.xhtml">Appendix</a></li>
  </ol>
</nav>
```

#### What Pandoc Does:
- Generates `<nav epub:type="toc">` automatically from headers
- Does NOT generate landmarks by default
- Workaround: Lua filter or post-process OPF

#### Value for Your Pipeline:
- **Moderate**: Helps readers jump to book sections; less critical than TOC
- **Scanned books**: Landmarks useful for marking front matter (copyright page, preface)

**Recommendation**: Add landmarks via Lua filter if budget allows; otherwise, post-process OPF after Pandoc generation.

---

### E. Lua Filters for Book-Specific Improvements

**Source**: Pandoc Lua filter documentation (https://pandoc.org/lua-filters.html)
**Confidence**: HIGH | Well-documented, actively maintained

#### Lua Filters Useful for Your Use Cases:

| Filter Purpose | Input | Output | Benefit | Complexity |
|---|---|---|---|---|
| **Page-break injection** | Markdown `<!-- page: N -->` | `<span epub:type="pagebreak" title="N"/>` | Citation support, page-list generation | Medium |
| **Math accessibility** | LaTeX `$$..$$` | MathML + alt-text | Screen reader support; fallback for readers without MathML | Medium |
| **Small caps handling** | Markdown `[Small caps text]{.smallcaps}` | `<span style="font-variant: small-caps">` | Typography preservation for scanned books | Low |
| **Index generation** | YAML front-matter `index: [[term, page], ...]` | `<nav epub:type="index">` | Scanned books often have indices; manual mapping needed | High |
| **Header/footer removal** | Detect repeated text in headers | Delete/suppress | OCR artifact removal (very common in scanned books) | High |
| **Citation linking** | Markdown `[@key]` or `<span id="bib-key">` | `<a href="#bib-key">Author (Year)</a>` | Built-in via `--citeproc`; custom if non-standard format | Medium |

#### Example: Simple Page-Break Filter (Lua)
```lua
-- pagebreak-filter.lua
function RawBlock(elem)
  if elem.format == 'html' and elem.text:match('<!-- page: (%d+)') then
    local pagenum = elem.text:match('<!-- page: (%d+)')
    return pandoc.RawInline('html', '<span id="page' .. pagenum .. '" epub:type="pagebreak" title="' .. pagenum .. '"/>')
  end
  return elem
end
```

**Recommendation**: Prioritize page-break injection and math accessibility filters. Index and header/footer removal require significant effort.

---

## PART 3: VALIDATION TOOLS & ACCESSIBILITY CHECKING

### A. epubcheck (W3C Official Validator)

**Source**: W3C epubcheck (https://github.com/w3c/epubcheck, v5.1.0+ as of Oct 2026)
**Confidence**: HIGH | Official W3C tool, regularly updated

#### What epubcheck Validates:
1. **ZIP structure**: mimetype, container.xml, OPF manifest/spine
2. **XHTML compliance**: Valid XML, semantic markup
3. **Resource references**: Images exist, fonts embedded, CSS valid
4. **Metadata completeness**: Required dc:title, dc:identifier, dc:language
5. **EPUB Accessibility 1.1 subset**: MathML alternatives, image alt-text
6. **Media types**: Correct MIME types for images, fonts, CSS

#### Installation & Usage:

```bash
# Python wrapper (PyPI: 'epubcheck')
pip install epubcheck
epubcheck output.epub --json report.json

# Docker (official)
docker run -v $(pwd):/tmp -i schemastore/epubcheck /tmp/output.epub

# Java CLI (direct)
java -jar epubcheck.jar output.epub -json report.json
```

#### Common Errors in Generated EPUBs:

| Error | Cause | Fix |
|---|---|---|
| `Missing required metadata: dc:language` | OPF lacks language tag | Add to description.json: `"language": "es"` |
| `Resource not found: images/fig1.png` | Image path mismatch | Ensure `--resource-path=images:.` points to correct folder |
| `Invalid XHTML: unmatched tag <div>` | Custom post-processing breaks XML | Validate XML before Pandoc input |
| `Font file not embedded` | CSS references external font | Use `--epub-subdirectory=EPUB` and include font in CSS |
| `Unreferenced resource: unused.png` | Extra files in manifest | Remove unused images; use Pandoc's resource discovery |

#### Output Interpretation:
- **ERRORS** (fatal): EPUB won't open in readers
- **WARNINGS** (non-fatal): May cause rendering issues or accessibility failure
- **USAGE** (info): Suggestions for best practices

**Recommendation**: Integrate epubcheck into your pipeline as a final validation step. Parse JSON output to fail build if ERRORS > 0.

**Confidence**: HIGH

---

### B. DAISY Ace Accessibility Checker

**Source**: DAISY Ace (https://github.com/daisy/ace, v3.x as of Oct 2026)
**Confidence**: HIGH | Specialized accessibility validator

#### What ACE Checks:
1. **Image alternative text**: All `<img>` must have `alt` or `aria-label`
2. **Heading hierarchy**: No skipped levels (H1→H3 is error)
3. **Color contrast**: Text passes WCAG AA/AAA thresholds
4. **Form accessibility**: Labels for inputs, semantic form elements
5. **Language tags**: `<html lang>` specified; language changes marked
6. **MathML**: Equations have `<annotation>` fallbacks
7. **List semantics**: Proper `<ol>`, `<ul>` structure

#### Installation & Usage:

```bash
# Node.js required
npm install -g @daisy/ace
ace output.epub --output ace-report.json

# Docker
docker run -v $(pwd):/tmp daisy/ace:latest /tmp/output.epub
```

#### Specific Improvements for Your Mixed Content:

| Input Type | Common Accessibility Gaps | ACE Will Flag | Fix |
|---|---|---|---|
| **Scanned books** | Images lack alt-text; low contrast OCR artifacts | Missing alt-text; color contrast failures | Add OCR confidence scores to alt-text; preprocess images for contrast |
| **Academic papers** | Equations as PNG; citations use color only | Missing MathML; color-only markers | Use `--mathml` in Pandoc; add aria-labels to citation links |
| **Spanish books** | Language tags missing; accent marks problematic | Language metadata missing; encoding issues | Add `"language": "es"` to metadata; ensure UTF-8 encoding |

**Relevance**: ACE is specialized for accessibility; epubcheck is specialized for EPUB structure. Use BOTH.

---

### C. Reader-Specific Validation (Manual + Programmatic)

**Tools & Platforms**:

| Reader | MathML Support | Pop-up Footnotes | Font Control | OCR Tolerance |
|---|---|---|---|---|
| **Apple Books** | ✅ Yes (iOS 15+) | ✅ Yes | Limited | Very strict (fails on encoding issues) |
| **Kobo** | ✅ Yes (recent firmware) | ✅ Yes | Good | Moderate (forgiving) |
| **KOReader** | ✅ Yes (native) | ✅ Yes | Excellent | Good (forgiving) |
| **Calibre Viewer** | ✅ Yes (partial) | ✅ Yes | Excellent | Very forgiving (good for testing) |
| **Google Play Books** | ⚠️ Limited | ✅ Yes | Limited | Moderate |
| **Kindle** | ❌ No (via Send to Kindle) | ❌ No | Limited | Strict |

**Programmatic Validation Strategy**:
1. Generate EPUB with Pandoc
2. Run epubcheck (structural validation)
3. Run ACE (accessibility validation)
4. Extract XHTML samples; validate XML well-formedness
5. Spot-check on 2-3 readers (Calibre for lenient, Apple Books for strict)

**Confidence**: HIGH for tools; MEDIUM for cross-reader compatibility (depends on reader firmware versions and updates).

---

## PART 4: READER COMPATIBILITY & FALLBACKS

### A. MathML Support & Fallback Strategy

**Current Status (October 2026)**:
- **Native MathML support**: Apple Books (iOS 15+), KOReader, recent Kobo, Calibre
- **Fallback needed**: Google Play Books, older readers, Kindle

#### Pandoc's MathML Generation:
```bash
# Generate MathML (EPUB3 standard)
pandoc --mathml ...

# Result in EPUB:
<math xmlns="http://www.w3.org/1998/Math/MathML">
  <mrow>...</mrow>
</math>
```

#### Fallback Options:

| Strategy | Pro | Con | Best For |
|---|---|---|---|
| **MathML + alt-text** | Accessible; screen-reader friendly | Older readers show equation code | Academic papers |
| **MathML + SVG image** | Renders in all readers | Larger EPUB file; complex setup | Math-heavy academic papers |
| **MathML + PNG image** | Simple; smaller than SVG | Blurry on high-DPI; accessibility loss | Light math content |
| **HTML5 `<img>` only** | Smallest file; fastest rendering | Accessibility issue; no copy/paste | Scanned books with embedded equations |

#### Implementation via Lua Filter:
```lua
-- Add SVG fallback to MathML
function Math(elem)
  if elem.mathtype == 'DisplayMath' then
    local svg = latex_to_svg(elem.text)
    return pandoc.RawInline('html',
      '<math>...</math><img alt="Equation" src="math1.svg" />'
    )
  end
end
```

**Recommendation**: 
- **Academic papers**: MathML + high-quality alt-text (e.g., "$$\int_0^\infty e^{-x^2} dx = \sqrt{\pi}/2$$")
- **Scanned books**: Pre-OCR equations as images; don't attempt MathML conversion if confidence low

**Confidence**: HIGH for current reader support; MEDIUM for future compatibility (EPUB Reader implementations evolving).

---

### B. Footnote Rendering Across Readers

#### Current Status:
- **Pop-up footnotes**: Apple Books, Kobo (recent), KOReader, Calibre
- **End-of-section**: Fallback in all readers

#### Your Custom Post-Processing Concern:
Your pipeline adds Pandoc `[^id]` footnotes. Pandoc converts these to EPUB-compliant `<aside epub:type="footnote">` automatically.

**Question**: Does your custom post-processing (linked footnotes, citation anchors) happen before or after Markdown generation?

**If BEFORE Markdown**: Modify to use Pandoc's `[^id]` format
**If AFTER Markdown**: Ensure custom `<a>` links don't conflict with Pandoc's footnote generation

**Recommendation**: Keep footnote processing within Markdown; let Pandoc handle EPUB semantics. Only add citation bibliography links after Pandoc output via post-processing OPF/XHTML.

**Confidence**: HIGH for standard behavior; LOW for your custom pipeline (needs verification).

---

### C. Font Embedding & Subsetting

#### EPUB Font Requirements:
```xml
<!-- OPF manifest entry -->
<item id="font1" href="fonts/Lora.woff2" media-type="application/font-woff2"/>

<!-- CSS reference -->
@font-face {
  font-family: 'Lora';
  src: url('../fonts/Lora.woff2') format('woff2');
}
body { font-family: 'Lora', serif; }
```

#### Supported Font Formats:
| Format | EPUB Support | Size | Browser Support | Best For |
|---|---|---|---|---|
| **WOFF2** | ✅ EPUB3 | 60% smaller | Modern readers | Primary choice |
| **WOFF** | ✅ EPUB2/3 | 80% of TTF | Older readers | Fallback |
| **TTF** | ⚠️ Some readers | Full size | Calibre | Legacy readers only |
| **OTF** | ⚠️ Limited | Full size | Few readers | Avoid |

#### Font Subsetting:
Reduce EPUB file size by including only used glyphs:

```bash
# Using fonttools (Python)
pip install fonttools
pyftsubset Lora.ttf --output-file=Lora-subset.woff2 \
  --unicodes=U+0020-U+007E,U+00A0-U+00FF,U+0100-U+017F

# Via Calibre (GUI or CLI)
ebook-convert input.epub output.epub --subset-fonts
```

#### For Your Mixed Content:
- **English books**: Standard ASCII fonts (Times, Garamond, Lora)
- **Spanish books**: Include Latin Extended-A (U+0100-U+017F) for accents
- **Math papers**: Ensure font includes Greek letters, math symbols

**Recommendation**: 
1. Use WOFF2 format exclusively
2. Subset fonts to include only necessary character ranges
3. Include 2-3 fallback fonts (serif, sans-serif)
4. Test on multiple readers (font embedding varies)

**Confidence**: HIGH for technical details; MEDIUM for reader implementation consistency.

---

## PART 5: CALIBRE EBOOK TOOLS & ALTERNATIVES

### A. Calibre ebook-convert & ebook-polish

**Source**: Calibre documentation (https://manual.calibre-ebook.com), v7.x (Oct 2026)
**Confidence**: HIGH | Widely used, actively maintained

#### When to Use Calibre Over Pandoc:

| Task | Calibre | Pandoc | Recommendation |
|---|---|---|---|
| **EPUB → EPUB upgrade** | Native optimization | Not applicable | Use Calibre after Pandoc |
| **Font subsetting** | `ebook-convert --subset-fonts` | Requires Lua filter | Calibre easier |
| **Smarten punctuation** | `ebook-polish --smarten-punctuation` | Via Lua filter | Calibre faster |
| **Metadata editing** | Interactive GUI; CLI tool | Post-process OPF | Calibre more flexible |
| **Validation & repair** | `ebook-polish --remove-unused-resources` | Manual review | Calibre automated |
| **EPUB2 → EPUB3 upgrade** | Native conversion | Not applicable | Only Calibre option |

#### Calibre CLI Usage for Post-Pandoc Polish:

```bash
# 1. Generate EPUB with Pandoc (as usual)
pandoc --to=epub3 input.md -o output.epub

# 2. Polish with Calibre (optional but recommended)
ebook-polish \
  --remove-unused-resources \
  --subset-fonts \
  --smarten-punctuation \
  output.epub output_polished.epub

# 3. Convert to EPUB3 if legacy EPUB2
ebook-convert output.epub output_v3.epub --epub-version=3

# 4. Validate result
epubcheck output_polished.epub
```

#### Calibre Python API for Automation:

```python
# Via subprocess (most reliable for 2026)
import subprocess

def calibre_polish(input_epub, output_epub):
    subprocess.run([
        'ebook-polish',
        '--remove-unused-resources',
        '--subset-fonts',
        input_epub,
        output_epub
    ], check=True)

# Direct Python API (experimental; may not be available in all Calibre versions)
# from calibre.ebooks.conversion.plugins.epub_output import EPUBOutput
# (less reliable for automation)
```

**Value for Your Pipeline**:
- **Born-digital books**: Calibre polish removes unused metadata entries
- **Scanned books**: Smarten punctuation helps OCR artifact cleanup
- **Academic papers**: Font subsetting reduces EPUB size (important for large papers)

**Confidence**: HIGH for technical details; MEDIUM for long-term API stability (Calibre may deprecate Python API).

---

### B. Alternative EPUB Builders

#### EbookLib (Python)
**Source**: EbookLib PyPI (https://github.com/aerkalov/ebooklib)
**Status**: Active but lower-traffic than Calibre

**Pros**:
- Pure Python; no external dependencies
- Full programmatic control over OPF, NCX, content
- Good for custom post-processing

**Cons**:
- Less tested on exotic inputs (scanned books, heavy math)
- No auto-validation; manual semantic markup required
- Smaller community; fewer bug fixes

**Best Use Case**: Custom EPUB generation if Pandoc's options are insufficient. NOT recommended as primary builder for your pipeline.

#### Sigil (GUI + automation)
**Source**: Sigil (https://sigil-ebook.com), v2.x (Oct 2026)
**Status**: Active, strong community

**Features**:
- WYSIWYG EPUB editor
- Batch processing via Python plugins
- Excellent for manual review + fixing OCR issues

**Cons**:
- GUI-focused; CLI automation limited
- Slower than Pandoc for large batches
- Steep learning curve for plugin development

**Best Use Case**: Manual review/correction of complex PDFs (scanned books with layout issues). NOT recommended for fully automated pipeline.

---

### C. Comparison Table: EPUB Generation Tools for Your Use Case

| Tool | Speed | Batch Ready | Math Support | Metadata Control | Accessibility | Best For |
|---|---|---|---|---|---|---|
| **Pandoc 3.9** | ⚡⚡⚡ Fast | ✅ Yes | MathML | Good | Good | Primary builder |
| **Calibre ebook-convert** | ⚡ Moderate | ✅ Yes | Limited | Good | Excellent | Post-processing |
| **EbookLib** | ⚡⚡ Fast | ✅ Yes | No (DIY) | Excellent | DIY | Custom builds only |
| **Sigil** | ⚡ Slow | ⚠️ Plugins | Good | Excellent | Excellent | Manual review |

**Recommendation**: Use Pandoc + optional Calibre polish for most books. Reserve EbookLib for edge cases requiring custom OPF control.

---

## PART 6: EVALUATION METHODOLOGY & LIGHTWEIGHT QUALITY SCORECARD

### A. Document-Conversion Benchmark Metrics

**Source**: Academic literature on document conversion (OmniDocBench, olmOCR-Bench, TEDS, CDM, NED, BLEU)
**Confidence**: HIGH for academic metrics; MEDIUM for applicability to EPUB (most benchmarks focus on OCR accuracy, not ebook quality)

#### Relevant Metrics for PDF→EPUB:

| Metric | Formula | Best Use Case | Limitation |
|---|---|---|---|
| **Text Edit Distance (TED)** | Levenshtein distance between OCR'd and ground-truth text | Measure OCR errors in scanned books | Doesn't account for layout or semantic markup |
| **Character Error Rate (CER)** | `(S + D + I) / N` where S=substitutions, D=deletions, I=insertions, N=total chars | OCR quality per page | Binary; doesn't capture meaning errors |
| **Word Error Rate (WER)** | Similar to CER but word-level | OCR quality; easier to interpret | Favors long words |
| **TEDS (Table Edit Distance)** | TED applied to table structure | Table extraction accuracy | Not applicable to footnote/citation structure |
| **CDM (Content Digest Match)** | Jaccard similarity on content blocks | Layout preservation | Too coarse for EPUB validation |
| **BLEU / METEOR** | Precision of n-gram matches vs. reference | Machine-translation-style comparison | Requires ground-truth EPUB (manual creation) |
| **NED (Normalized Edit Distance)** | TED normalized to 0-1 range | Normalized accuracy metric | Still doesn't validate semantic markup |

#### Why These Metrics Alone Are Insufficient for EPUB Quality:
- OCR accuracy (CER/WER) ≠ EPUB quality (structure, accessibility, reader compatibility)
- Layout metrics (CDM, TEDS) don't measure semantic markup correctness
- No standard metric for "is this EPUB spec-compliant?"

**Better Approach**: Combine metric evaluation with heuristic quality scoring (see next section).

---

### B. Lightweight Heuristic Quality Scorecard (No Ground Truth Needed)

**Concept**: Measure quality dimensions automatically without requiring manual ground-truth EPUB. Suitable for per-book scoring and pipeline health monitoring.

#### Proposed Scorecard (100-point scale):

```yaml
EPUB Quality Scorecard v1.0
==========================

1. STRUCTURAL COMPLIANCE (25 points)
   - epubcheck errors = 0? (10 pts)
   - epubcheck warnings < 5? (5 pts)
   - OPF well-formed + complete metadata? (5 pts)
   - Navigation doc (toc.ncx) correct? (5 pts)

2. CONTENT SEMANTIC MARKUP (20 points)
   - Heading hierarchy valid (no H1→H3 jumps)? (5 pts)
   - All images have alt-text? (5 pts)
   - Footnotes use epub:type="footnote"? (5 pts)
   - Tables have captions? (5 pts)

3. ACCESSIBILITY (15 points)
   - ACE accessibility errors = 0? (8 pts)
   - Language tag present + correct? (4 pts)
   - Color contrast passes WCAG AA? (3 pts)

4. CONTENT EXTRACTION (15 points)
   - TOC depth matches original PDF TOC? (5 pts)
   - % of cited pages successfully linked (if page-list exists)? (5 pts)
   - Header/footer leakage < 2%? (5 pts)

5. READER COMPATIBILITY (15 points)
   - MathML renders on KOReader? (5 pts)
   - Footnotes pop-up on Apple Books? (5 pts)
   - Fonts embed without subsetting errors? (5 pts)

6. PERFORMANCE (10 points)
   - EPUB file size < 10MB for typical book? (5 pts)
   - No unreferenced resources in manifest? (5 pts)

OVERALL SCORE = SUM(all sections) / 100
Grade:
  90-100: Excellent (production-ready)
  70-89:  Good (publishable with minor fixes)
  50-69:  Fair (requires manual review)
  < 50:   Poor (significant issues)
```

#### Automated Scorecard Implementation (Python pseudocode):

```python
import json
import subprocess
import zipfile
from xml.etree import ElementTree as ET

class EPUBQualityScorer:
    def __init__(self, epub_path):
        self.epub_path = epub_path
        self.scores = {}
    
    def score_structural_compliance(self):
        # Run epubcheck
        result = subprocess.run(
            ['epubcheck', self.epub_path, '--json'],
            capture_output=True
        )
        report = json.loads(result.stdout)
        
        errors = len(report.get('messages', []))
        warnings = len([m for m in report['messages'] 
                       if m['severity'] == 'WARNING'])
        
        score = 0
        score += 10 if errors == 0 else 0
        score += 5 if warnings < 5 else 0
        # ... check OPF, nav doc
        self.scores['structural'] = score
    
    def score_semantic_markup(self):
        # Extract XHTML files from EPUB (it's a ZIP)
        with zipfile.ZipFile(self.epub_path) as z:
            xhtml_files = [f for f in z.namelist() if f.endswith('.xhtml')]
            for xhtml_file in xhtml_files:
                content = z.read(xhtml_file).decode('utf-8')
                tree = ET.fromstring(content)
                
                # Check heading hierarchy
                headings = tree.findall('.//{http://www.w3.org/1999/xhtml}h[1-6]')
                # Check image alt-text
                images = tree.findall('.//{http://www.w3.org/1999/xhtml}img')
                alt_text_rate = sum(1 for img in images if img.get('alt')) / len(images)
                # ... etc
        self.scores['semantic'] = # calculated
    
    def score_accessibility(self):
        # Run ACE checker
        result = subprocess.run(
            ['ace', self.epub_path, '--output', 'ace_report.json'],
            capture_output=True
        )
        report = json.loads(open('ace_report.json').read())
        
        violations = len(report.get('violations', []))
        self.scores['accessibility'] = 15 if violations == 0 else max(0, 15 - violations)
    
    def score_content_extraction(self):
        # TOC depth check, page-break count, header/footer heuristic
        # (requires OCR baseline comparison or manual labeling)
        self.scores['content'] = # calculated
    
    def final_score(self):
        total = sum(self.scores.values())
        return {
            'total': total,
            'breakdown': self.scores,
            'grade': self._grade(total)
        }
    
    def _grade(self, score):
        if score >= 90: return 'Excellent'
        elif score >= 70: return 'Good'
        elif score >= 50: return 'Fair'
        else: return 'Poor'

# Usage
scorer = EPUBQualityScorer('output.epub')
scorer.score_structural_compliance()
scorer.score_semantic_markup()
scorer.score_accessibility()
scorer.score_content_extraction()
result = scorer.final_score()
print(f"Overall Score: {result['total']}/100 ({result['grade']})")
print(json.dumps(result['breakdown'], indent=2))
```

#### Lightweight Metrics for Per-Book Scorecard:

| Metric | Formula | Threshold | Automation | Value |
|---|---|---|---|---|
| **epubcheck error rate** | `errors / pages` | < 0.01 | Automatic | High |
| **ACE violation count** | Count unique violations | < 10 | Automatic | High |
| **Footnote link preservation** | `linked_footnotes / total_footnotes` | > 95% | Automatic | High |
| **Citation link rate** | `resolved_citations / total_citations` | > 90% | Semi-auto (regex) | Medium |
| **Header/footer leakage** | % of repeated top/bottom text | < 2% | Heuristic | Medium |
| **TOC depth match** | Correlation between original PDF TOC and EPUB TOC | > 0.8 (Pearson) | Semi-auto | Medium |
| **Split-word rate** | % of words broken across lines/blocks | < 5% | OCR-dependent | Low (scanned only) |
| **Image alt-text coverage** | `images_with_alt_text / total_images` | 100% | Automatic | High |

**Recommendation**: Automate top 5 metrics; manually sample 10% of books for others.

---

### C. Small Hand-Labelled Gold Set for Validation

**Purpose**: Establish baseline quality expectations and calibrate heuristic scoring.

#### Proposed Gold Set Composition (10-15 books):
- **2-3 Spanish born-digital books** (test language support, metadata)
- **2-3 English academic papers** (test math/citations)
- **2-3 scanned books** (test OCR artifact handling)
- **1-2 heavily formatted books** (test layout preservation)
- **1-2 multilingual books** (test language tagging)

#### Manual Validation Protocol per Book:
1. Read through EPUB on 2-3 readers (Apple Books, KOReader, Calibre)
2. Rate each dimension on 1-5 scale:
   - Text readability (OCR quality)
   - Layout preservation (margins, indentation)
   - Math/equation rendering
   - Footnote usability
   - Citation link accuracy
   - Overall satisfaction
3. Document any rendering failures or accessibility issues
4. Compare manual ratings with automated scores; adjust scoring weights

#### Use Case:
- Calibrate heuristic scorer to match manual quality perception
- Identify systematic biases in metrics (e.g., epubcheck warnings over-weight accessibility issues)
- Establish confidence intervals for automated scoring

**Confidence**: HIGH for methodology; MEDIUM for implementation (requires dedicated QA effort).

---

## PART 7: SUMMARY & IMPLEMENTATION ROADMAP

### Key Findings by Priority

#### IMMEDIATE (High Impact, Low Effort):

1. **Validate with epubcheck**: Integrate into pipeline; fail builds on ERRORS
   - **Tool**: `pip install epubcheck`
   - **Output**: Parse JSON; log error categories
   - **Effort**: 1-2 hours
   - **Impact**: Catch structural EPUB issues before readers fail

2. **Add language metadata**: Ensure `<dc:language>` tag in OPF for each book
   - **Current**: Likely missing or hardcoded
   - **Fix**: Add `"language"` to description.json metadata
   - **Effort**: 0.5 hours
   - **Impact**: Improves accessibility + reader rendering

3. **Enable Pandoc's `--mathml` flag**: Already recommended in current pipeline
   - **Change**: Already done in your Pandoc invocation (confirm)
   - **Effort**: 0 hours (already in use)
   - **Impact**: MathML support for academic papers

#### SHORT TERM (1-2 weeks):

4. **Run ACE accessibility checker**: Catch accessibility gaps
   - **Tool**: `npm install -g @daisy/ace`
   - **Integration**: Post-Pandoc validation
   - **Effort**: 2-3 hours
   - **Impact**: Identify image alt-text, heading hierarchy, color contrast issues

5. **Implement heuristic quality scorecard**: Automated per-book QA
   - **Components**: epubcheck parsing, ACE integration, footnote link validation
   - **Effort**: 4-6 hours
   - **Impact**: Quantified quality tracking; identify systematic issues

6. **Create Lua filter for page-breaks**: Enable citation support
   - **Input**: Marker-pdf output with page metadata
   - **Output**: `<span epub:type="pagebreak" title="N"/>`
   - **Effort**: 3-4 hours
   - **Impact**: Citation linking; page-list generation

#### MEDIUM TERM (1 month):

7. **Establish gold set validation**: Calibrate quality metrics
   - **Samples**: 10-15 representative books
   - **Protocol**: Manual review on 2-3 readers
   - **Effort**: 8-10 hours
   - **Impact**: Trusted baseline for quality expectations

8. **Add Calibre polish step**: Optional post-Pandoc optimization
   - **Use Case**: Scanned books needing artifact cleanup, math-heavy papers needing font subsetting
   - **Integration**: Conditional (e.g., if `--optimize` flag)
   - **Effort**: 2-3 hours
   - **Impact**: 5-10% file size reduction; cleaner punctuation

9. **Implement landmark navigation**: Improve reader navigation
   - **Components**: Cover, TOC, start of book, appendices
   - **Effort**: 2-3 hours (Lua filter or post-process)
   - **Impact**: Better user experience; minor accessibility gain

#### LONG TERM (2+ months):

10. **Build math accessibility filter**: MathML + alt-text + SVG fallback
    - **Scope**: Complex; requires LaTeX→SVG conversion
    - **Effort**: 1-2 weeks
    - **Impact**: Math equations accessible to all readers + screen readers

11. **Automate OCR artifact cleanup**: Header/footer removal, split-word detection
    - **Approach**: Heuristics (repeated text, orphan words) or ML-based
    - **Effort**: 2-3 weeks
    - **Impact**: Significantly cleaner scanned books

---

### Technology Stack Recommendations

#### Validation & Quality Assurance Layer:
```
Pipeline Flow:
PDF --[marker-pdf]--> Markdown --[custom post-processing]--> Enhanced Markdown
        ↓
     [Pandoc + Lua filters] ---> Raw EPUB
        ↓
   [epubcheck + ACE] ---> Validation Report
        ↓
   [Calibre polish (optional)] ---> Polished EPUB
        ↓
   [Quality scorecard] ---> Quality JSON
        ↓
   [Spot-check on readers] ---> Final approval/rejection
```

#### Python Packages to Add:
```
# Validation
epubcheck>=5.1.0
daisy-ace>=3.0  # or run via Node.js subprocess

# Quality scoring
lxml  # for XML parsing
python-language-codes  # for language validation

# Optional optimization
calibre  # system package; call via subprocess

# Testing & monitoring
pytest  # for validation test suite
```

#### Confidence Levels by Component:

| Component | Confidence | Notes |
|---|---|---|
| **Pandoc EPUB generation** | HIGH | Stable, well-tested, documented |
| **epubcheck validation** | HIGH | Official W3C tool; canonical validator |
| **ACE accessibility** | HIGH | Specialized DAISY tool; well-maintained |
| **Calibre optimization** | MEDIUM | Useful but optional; Python API stability uncertain |
| **Lua filters for page-breaks** | MEDIUM | Requires confirmation of Marker-pdf page metadata |
| **Quality scorecard heuristics** | MEDIUM | Needs calibration on gold set |
| **Reader compatibility testing** | LOW-MEDIUM | Reader behavior evolves; firmware-dependent |

---

## PART 8: OPEN QUESTIONS & UNKNOWNS

### Requires Verification in Your Codebase:

1. **Marker-pdf page metadata**: Does marker-pdf preserve page-break markers or page numbers? If so, can these be extracted and injected into Markdown?
   - **Impact on strategy**: Page-list generation depends on this
   - **Recommendation**: Check Marker-pdf output format; inspect sample metadata.json

2. **Custom post-processing order**: When does your custom footnote/citation linking happen relative to Markdown generation?
   - **Current**: Unclear from context (post-processes after Markdown or before?)
   - **Impact on strategy**: Determines if links survive Pandoc EPUB generation
   - **Recommendation**: Review your post-processing scripts; document flow

3. **Current Pandoc flags in use**: Are you already using `--mathml --toc --split-level=1` as described, or are defaults used?
   - **Impact on strategy**: Baseline quality; informs quick wins
   - **Recommendation**: Check your Pandoc CLI invocation

4. **Scanned book OCR pipeline**: How confident is marker-pdf OCR on academic/Spanish books?
   - **Impact on strategy**: If CER/WER > 5%, focus efforts on OCR artifact cleanup over EPUB semantics
   - **Recommendation**: Benchmark marker-pdf on representative samples

5. **Legacy md2epub builder status**: Is legacy builder still in active use, or can it be deprecated?
   - **Impact on strategy**: If deprecated, simplify validation to Pandoc pipeline only
   - **Recommendation**: Clarify which builder is canonical

---

## CONCLUSION

Your PDF→Markdown→EPUB pipeline can achieve **high-quality output** across mixed content (born-digital, scanned, academic) by:

1. **Generating EPUB3-compliant output** (Pandoc with correct flags + custom Lua filters)
2. **Validating comprehensively** (epubcheck for structure + ACE for accessibility)
3. **Measuring objectively** (lightweight heuristic scorecard + spot-checking on real readers)

**Recommended Quick Win** (< 1 week): Integrate epubcheck + ACE into pipeline, establish quality baseline on 3-5 sample books, prioritize fixing accessibility errors (image alt-text, language tags, heading hierarchy).

**Long-term North Star**: A fully automated quality scorecard (90+ points) that predicts production-ready EPUBs without manual review, with fallback review for books scoring 50-89 points.

---

## REFERENCES & SOURCES

### Official Standards:
- W3C EPUB 3.3: https://www.w3.org/TR/epub-33/
- W3C EPUB Accessibility 1.1: https://www.w3.org/TR/epub-a11y-11/
- Pandoc 3.9 Manual: https://pandoc.org/MANUAL.html
- Pandoc Lua Filters: https://pandoc.org/lua-filters.html

### Validation Tools:
- W3C epubcheck: https://github.com/w3c/epubcheck
- DAISY Ace: https://github.com/daisy/ace
- Calibre: https://manual.calibre-ebook.com

### Academic References:
- OmniDocBench (Document conversion benchmarks)
- TEDS (Table Edit Distance for table extraction)
- CDM (Content Digest Match)
- NED (Normalized Edit Distance)

### Libraries:
- EbookLib: https://github.com/aerkalov/ebooklib
- Sigil: https://sigil-ebook.com

---

**Last Updated**: October 13, 2026
**Researcher**: Domain Research Agent
**Confidence Summary**: HIGH for standards & tooling; MEDIUM for pipeline-specific implementation details (requires codebase verification)
