# EPUB Quality: Implementation Guide & Code Templates
**October 13, 2026** | Quick-start templates for validation, quality scoring, and optimization

---

## PART A: VALIDATION INTEGRATION (Week 1)

### A1. epubcheck Integration

#### Python Wrapper (Recommended)
```python
import json
import subprocess
import sys
from pathlib import Path

def validate_epub(epub_path: str, json_output: str = None) -> dict:
    """
    Run epubcheck on EPUB file; return structured results.
    
    Returns:
        {
            'valid': bool,
            'errors': int,
            'warnings': int,
            'messages': [{
                'severity': 'ERROR'|'WARNING'|'USAGE',
                'message': str,
                'line': int,
                'column': int
            }],
            'error_categories': {'ENCODING': 2, 'METADATA': 1, ...}
        }
    """
    cmd = [
        'epubcheck',
        epub_path,
        '--json',
        *([json_output] if json_output else [])
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        report = json.loads(result.stdout)
    except FileNotFoundError:
        print("ERROR: epubcheck not installed. Run: pip install epubcheck")
        sys.exit(1)
    except json.JSONDecodeError:
        return {
            'valid': False,
            'error': 'Failed to parse epubcheck output',
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    
    # Parse messages
    errors = sum(1 for m in report.get('messages', []) if m['severity'] == 'ERROR')
    warnings = sum(1 for m in report.get('messages', []) if m['severity'] == 'WARNING')
    
    # Categorize errors
    error_categories = {}
    for msg in report.get('messages', []):
        if msg['severity'] == 'ERROR':
            msg_text = msg.get('message', '')
            category = msg_text.split(':')[0] if ':' in msg_text else 'OTHER'
            error_categories[category] = error_categories.get(category, 0) + 1
    
    return {
        'valid': errors == 0,
        'errors': errors,
        'warnings': warnings,
        'messages': report.get('messages', []),
        'error_categories': error_categories,
        'path': epub_path
    }

def build_with_validation(markdown_path: str, output_epub: str):
    """Example: Generate EPUB, validate, report."""
    import subprocess
    
    # Step 1: Generate with Pandoc
    subprocess.run([
        'pandoc',
        '--from=markdown',
        '--to=epub3',
        '--mathml',
        '--toc',
        '--toc-depth=2',
        '--split-level=1',
        f'--output={output_epub}',
        markdown_path
    ], check=True)
    
    # Step 2: Validate
    report = validate_epub(output_epub)
    
    # Step 3: Decide
    if report['errors'] > 0:
        print(f"❌ EPUB validation failed ({report['errors']} errors):")
        for msg in report['messages']:
            if msg['severity'] == 'ERROR':
                print(f"  - {msg['message']}")
        return False
    elif report['warnings'] > 0:
        print(f"⚠️  EPUB has {report['warnings']} warnings (non-fatal)")
        for msg in report['messages'][:5]:  # Show first 5
            if msg['severity'] == 'WARNING':
                print(f"  - {msg['message']}")
    else:
        print(f"✅ EPUB validation passed")
    
    return True

# Usage
if __name__ == '__main__':
    success = build_with_validation('input.md', 'output.epub')
    sys.exit(0 if success else 1)
```

---

### A2. ACE Accessibility Integration

#### Python Wrapper
```python
import json
import subprocess
import sys

def check_accessibility(epub_path: str) -> dict:
    """
    Run DAISY Ace on EPUB; return accessibility violations.
    
    Returns:
        {
            'violations': [
                {
                    'criterion': 'WCAG criterion',
                    'type': 'missing-alt-text'|'heading-hierarchy'|...,
                    'count': int,
                    'examples': [str]
                }
            ],
            'passes': [...]
        }
    """
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = f"{tmpdir}/ace_report"
        
        cmd = ['ace', epub_path, '--output', output_dir]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            print("ERROR: ACE not installed. Run: npm install -g @daisy/ace")
            sys.exit(1)
        
        # Read report
        report_file = f"{output_dir}/report.json"
        try:
            with open(report_file) as f:
                report = json.load(f)
        except FileNotFoundError:
            return {
                'error': 'ACE did not generate report',
                'stdout': result.stdout,
                'stderr': result.stderr
            }
    
    # Parse violations
    violations = []
    for violation_set in report.get('violations', []):
        violations.append({
            'criterion': violation_set.get('rulesetTag'),
            'type': violation_set.get('id'),
            'count': len(violation_set.get('results', [])),
            'examples': [r.get('pointer') for r in violation_set.get('results', [])[:3]]
        })
    
    return {
        'total_violations': len(report.get('violations', [])),
        'violations': violations,
        'passes': report.get('passes', []),
        'path': epub_path
    }

def report_accessibility(epub_path: str):
    """Print accessibility report."""
    report = check_accessibility(epub_path)
    
    if 'error' in report:
        print(f"ERROR: {report['error']}")
        return False
    
    print(f"\n📋 Accessibility Report: {epub_path}")
    print(f"   Violations: {report['total_violations']}")
    
    if report['violations']:
        print(f"\n   ❌ Issues found:")
        for v in report['violations']:
            print(f"      - {v['criterion']}: {v['type']} ({v['count']} instances)")
            for ex in v['examples'][:2]:
                print(f"        • {ex}")
    else:
        print(f"\n   ✅ No accessibility violations!")
    
    return report['total_violations'] == 0
```

---

## PART B: QUALITY SCORECARD (Week 2)

### B1. Lightweight Heuristic Scorer

```python
import json
import zipfile
import subprocess
from xml.etree import ElementTree as ET
from collections import defaultdict

class EPUBQualityScorer:
    """
    Score EPUB on multiple quality dimensions.
    No ground truth needed; purely automated heuristics.
    """
    
    def __init__(self, epub_path: str):
        self.epub_path = epub_path
        self.scores = {}
        self.details = defaultdict(list)
    
    def score_structural_compliance(self) -> int:
        """Score: STRUCTURAL COMPLIANCE (25 pts)"""
        score = 0
        
        # epubcheck: errors
        result = subprocess.run(
            ['epubcheck', self.epub_path, '--json'],
            capture_output=True, text=True
        )
        report = json.loads(result.stdout)
        
        errors = len([m for m in report.get('messages', []) 
                     if m['severity'] == 'ERROR'])
        warnings = len([m for m in report.get('messages', []) 
                       if m['severity'] == 'WARNING'])
        
        if errors == 0:
            score += 10
            self.details['structural'].append("✅ No epubcheck errors")
        else:
            self.details['structural'].append(f"❌ {errors} epubcheck errors")
        
        if warnings < 5:
            score += 5
            self.details['structural'].append(f"✅ {warnings} warnings (< 5)")
        else:
            self.details['structural'].append(f"⚠️  {warnings} warnings")
        
        # Check OPF metadata
        with zipfile.ZipFile(self.epub_path) as z:
            container_xml = z.read('META-INF/container.xml')
            container_root = ET.fromstring(container_xml)
            
            # Find OPF file
            namespace = {'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            opf_path = container_root.find('.//container:rootfile', namespace).get('full-path')
            
            opf_content = z.read(opf_path)
            opf_root = ET.fromstring(opf_content)
            
            # Check metadata
            ns = {'opf': 'http://www.idpf.org/2007/opf', 
                  'dc': 'http://purl.org/dc/elements/1.1/'}
            
            title = opf_root.find('.//dc:title', ns)
            language = opf_root.find('.//dc:language', ns)
            identifier = opf_root.find('.//dc:identifier', ns)
            
            metadata_ok = all([title, language, identifier])
            score += 5 if metadata_ok else 0
            
            if metadata_ok:
                self.details['structural'].append("✅ OPF metadata complete")
            else:
                missing = []
                if not title: missing.append('title')
                if not language: missing.append('language')
                if not identifier: missing.append('identifier')
                self.details['structural'].append(f"❌ Missing OPF: {', '.join(missing)}")
        
        self.scores['structural'] = score
        return score
    
    def score_accessibility(self) -> int:
        """Score: ACCESSIBILITY (15 pts)"""
        score = 0
        
        # Run ACE
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ['ace', self.epub_path, '--output', tmpdir],
                capture_output=True, text=True
            )
            
            try:
                with open(f"{tmpdir}/report.json") as f:
                    ace_report = json.load(f)
                
                violations = len(ace_report.get('violations', []))
                
                if violations == 0:
                    score += 8
                    self.details['accessibility'].append("✅ No ACE violations")
                else:
                    score += max(0, 8 - violations)
                    self.details['accessibility'].append(f"⚠️  {violations} ACE violations")
            except:
                self.details['accessibility'].append("⚠️  Could not run ACE")
        
        # Check language tag
        with zipfile.ZipFile(self.epub_path) as z:
            for f in z.namelist():
                if 'nav' in f or f.endswith('nav.xhtml'):
                    content = z.read(f).decode('utf-8')
                    if 'lang=' in content or 'xml:lang=' in content:
                        score += 4
                        self.details['accessibility'].append("✅ Language tag present")
                        break
            else:
                self.details['accessibility'].append("❌ No language tag found")
        
        self.scores['accessibility'] = score
        return score
    
    def score_performance(self) -> int:
        """Score: PERFORMANCE (10 pts)"""
        score = 0
        
        import os
        file_size = os.path.getsize(self.epub_path)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb < 10:
            score += 5
            self.details['performance'].append(f"✅ File size: {file_size_mb:.1f} MB")
        else:
            self.details['performance'].append(f"⚠️  File size: {file_size_mb:.1f} MB (> 10 MB)")
        
        score += 5  # Placeholder for other performance checks
        
        self.scores['performance'] = score
        return score
    
    def final_score(self) -> dict:
        """Calculate overall score and grade."""
        self.score_structural_compliance()
        self.score_accessibility()
        self.score_performance()
        
        total = sum(self.scores.values())
        
        if total >= 90:
            grade = "✅ EXCELLENT"
        elif total >= 70:
            grade = "✅ GOOD"
        elif total >= 50:
            grade = "⚠️ FAIR"
        else:
            grade = "❌ POOR"
        
        return {
            'total': total,
            'grade': grade,
            'breakdown': self.scores,
            'details': dict(self.details),
            'path': self.epub_path
        }
    
    def report(self):
        """Print readable report."""
        result = self.final_score()
        
        print(f"\n{'='*60}")
        print(f"EPUB Quality Report: {result['path']}")
        print(f"{'='*60}")
        print(f"\nOVERALL SCORE: {result['total']}/100 {result['grade']}")
        print(f"\nBREAKDOWN:")
        for category, score in result['breakdown'].items():
            print(f"  {category.upper():20s} {score:2d} pts")
        
        return result
```

---

## PART C: LUA FILTERS (Week 2)

### C1. Page-Break Injection Filter

```lua
-- pagebreak-filter.lua
-- Convert Markdown comments "<!-- page: N -->" to EPUB page-break spans

function RawBlock(elem)
  if elem.format == 'html' then
    local pagenum = elem.text:match('<!--%s*page:%s*(%d+)%s*-->')
    if pagenum then
      return pandoc.RawBlock('html', 
        '<span id="page' .. pagenum .. '" epub:type="pagebreak" title="' .. pagenum .. '"/>'
      )
    end
  end
  return elem
end
```

**Usage**:
```bash
pandoc --from=markdown \
       --to=epub3 \
       --lua-filter=pagebreak-filter.lua \
       input.md -o output.epub
```

---

## PART D: METADATA TEMPLATE (Week 1)

### D1. description.json Template

```json
{
  "title": "Book Title",
  "author": "Author Name",
  "language": "es",
  "identifier": "urn:uuid:12345678-1234-5678-1234-567812345678",
  "date": "2025-10-13",
  "rights": "Copyright 2025",
  "publisher": "Publisher Name",
  "cover_image": "cover.jpg",
  "default_css": ["style.css"]
}
```

---

## PART E: BATCH PROCESSING (Week 1-2)

### E1. End-to-End Pipeline Script

```python
#!/usr/bin/env python3
"""
Complete PDF→Markdown→EPUB pipeline with validation.
"""

import subprocess
import json
import sys
from pathlib import Path

class PDFToEPUBPipeline:
    def __init__(self, work_dir: str):
        self.work_dir = Path(work_dir)
        self.results = []
    
    def process_pdf(self, pdf_path: str, book_name: str) -> dict:
        """
        Process single PDF: marker-pdf → markdown → EPUB → validate
        """
        print(f"\n{'='*60}")
        print(f"Processing: {book_name}")
        print(f"{'='*60}")
        
        # Step 1: PDF → Markdown (marker-pdf)
        print("\n[1/5] Converting PDF to Markdown...")
        markdown_dir = self.work_dir / f"{book_name}_markdown"
        markdown_dir.mkdir(exist_ok=True)
        
        try:
            subprocess.run([
                'marker_pdf',
                str(pdf_path),
                '--output-dir', str(markdown_dir)
            ], check=True, capture_output=True)
            print("✅ Marker-pdf completed")
        except Exception as e:
            print(f"❌ Marker-pdf failed: {e}")
            return {'status': 'FAILED', 'step': 'marker-pdf'}
        
        # Step 2: Markdown → EPUB (Pandoc)
        print(f"\n[2/5] Converting Markdown to EPUB...")
        markdown_file = markdown_dir / f"{book_name}.md"
        epub_path = self.work_dir / f"{book_name}.epub"
        
        try:
            subprocess.run([
                'pandoc',
                '--from=markdown',
                '--to=epub3',
                '--mathml',
                '--toc',
                '--toc-depth=2',
                '--split-level=1',
                f'--output={epub_path}',
                str(markdown_file)
            ], check=True, capture_output=True)
            print(f"✅ EPUB generated: {epub_path}")
        except Exception as e:
            print(f"❌ Pandoc failed: {e}")
            return {'status': 'FAILED', 'step': 'pandoc'}
        
        # Step 3: Validate EPUB
        print(f"\n[3/5] Validating EPUB...")
        result = subprocess.run(
            ['epubcheck', str(epub_path), '--json'],
            capture_output=True, text=True
        )
        
        try:
            validation = json.loads(result.stdout)
            errors = len([m for m in validation.get('messages', []) if m['severity'] == 'ERROR'])
            warnings = len([m for m in validation.get('messages', []) if m['severity'] == 'WARNING'])
            
            if errors > 0:
                print(f"❌ Validation failed ({errors} errors)")
                status = 'ERRORS'
            elif warnings > 0:
                print(f"⚠️  {warnings} warnings")
                status = 'WARNINGS'
            else:
                print("✅ Validation passed")
                status = 'VALID'
        except:
            errors, warnings = 0, 0
            status = 'UNKNOWN'
        
        report = {
            'book': book_name,
            'status': status,
            'epub': str(epub_path),
            'validation_errors': errors,
            'validation_warnings': warnings
        }
        
        self.results.append(report)
        return report
    
    def process_batch(self, pdf_files):
        """Process multiple PDFs."""
        for pdf_file in pdf_files:
            path = Path(pdf_file)
            book_name = path.stem
            self.process_pdf(pdf_file, book_name)
        
        # Print summary
        print(f"\n{'='*60}")
        print("BATCH PROCESSING SUMMARY")
        print(f"{'='*60}")
        for result in self.results:
            status_emoji = "✅" if result['status'] == 'VALID' else "⚠️" if result['status'] == 'WARNINGS' else "❌"
            print(f"{status_emoji} {result['book']}: {result['status']} (E:{result['validation_errors']} W:{result['validation_warnings']})")

# Usage
if __name__ == '__main__':
    pipeline = PDFToEPUBPipeline('./output')
    pdf_files = ['book1.pdf', 'book2.pdf']
    pipeline.process_batch(pdf_files)
```

---

## PART F: QUICK REFERENCE

### Installation
```bash
# Core tools
pip install epubcheck marker-pdf pandoc
npm install -g @daisy/ace

# Optional
brew install calibre  # macOS
apt install calibre   # Linux
```

### Key Commands
```bash
# Validate EPUB
epubcheck output.epub --json report.json

# Check accessibility
ace output.epub --output ace_report

# Generate with Pandoc
pandoc --from=markdown --to=epub3 --mathml --toc --split-level=1 input.md -o output.epub

# Optimize with Calibre
ebook-polish --remove-unused-resources --subset-fonts input.epub output.epub
```

### Common Issues & Fixes

| Error | Fix |
|-------|-----|
| `Missing dc:language` | Add `"language": "es"` to description.json |
| `Resource not found: images/fig.png` | Ensure `--resource-path=images:.` in Pandoc |
| `Invalid XHTML` | Validate markdown before Pandoc conversion |
| `Missing alt-text` | Add OCR-based alt-text post-processing |

---

**Implementation Guide Complete**

Ready for production integration into your PDF→EPUB pipeline.

