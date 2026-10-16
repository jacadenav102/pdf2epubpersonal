# Technical Integration Guide: Cloud Services into Marker Pipeline

**Purpose:** Detailed technical specification for integrating cloud document conversion services with your existing marker-pdf + Pandoc pipeline.

---

## PART 1: DETAILED COMPARISON TABLE

### Full Feature Matrix

```
SERVICE              | Output Format    | Structure Preservation | Math Support | OCR Quality | Spanish | Cost/300pg | Python SDK | Processing Speed | Data Retention |
---------------------|------------------|----------------------|------|-----------|---------|-----------|----------|-----------|-----------|
Mathpix              | MD/LaTeX/XLSX    | Good (h1-h6)         | ✓✓✓  | Good      | ?       | $1.50-3   | ✓        | Moderate  | Check ToS |
Azure AI Read        | JSON→MD          | Excellent (roles)     | Basic| ✓✓ Excl  | ✓       | $0.30-0.6 | ✓        | Fast      | No retention (opt) |
Azure AI Layout      | JSON→MD          | Good (headings)       | Basic| Good      | ✓       | $15-30    | ✓        | Moderate  | No retention (opt) |
Google Doc AI        | JSON→MD          | Good (heading roles)  | Basic| Good      | ✓       | $45-90    | ✓        | Moderate  | Config req |
AWS Textract         | JSON/CSV         | Limited (blocks)      | No   | ✓✓ Good  | ✓       | $4.50-30  | ✓ boto3  | Fast      | No retention (default) |
Unstructured (API)   | MD/JSON/HTML     | Good (partitioning)   | Basic| Good      | ✓       | $3-15     | ✓        | Moderate  | Check ToS |
Unstructured (OSS)   | MD/JSON/HTML     | Good (partitioning)   | Basic| Good      | ✓       | $0        | ✓        | Slow (CPU)| Local only |
LlamaParse           | MD/JSON          | Good (structure)      | Basic| Good      | ?       | $0.30-0.6 | ✓ llama  | Moderate  | Check ToS |
Claude 3.5 Opus      | JSON/MD (custom) | Excellent (prompt eng)| ✓✓  | ✓✓ Excl  | ✓       | $2.40-3.9 | ✓        | Slow      | Opt-out training |
Gemini 2.0 Flash     | JSON/MD (custom) | Excellent (prompt eng)| ✓✓  | ✓✓ Very  | ✓       | $2.25-6.75| ✓        | Moderate  | Opt-out training |
GPT-4o               | JSON/MD (custom) | Excellent (prompt eng)| ✓✓  | ✓✓ Excl  | ✓       | $5.30-8.3 | ✓        | Moderate  | Opt-out training |
Mistral Large        | JSON/MD (custom) | Good (prompt eng)     | Basic| Good      | ✓       | $3-9      | ✓        | Moderate  | Check ToS |
Marker (hosted)      | MD               | Excellent (same)      | ✓    | Good      | ✓       | $0.50-2   | TBD      | Fast      | Unknown |
Reducto              | JSON/CSV         | Excellent (tables)    | No   | Good      | ?       | $20-50+   | ?        | Moderate  | Enterprise |
```

### Legend
- **Output Format:** Primary output format(s)
- **Structure Preservation:** How well heading levels, sections, reading order maintained
- **Math Support:** LaTeX equation handling capability
- **OCR Quality:** Performance on scanned/degraded documents
- **Spanish:** Language support level (✓ = documented, ? = undocumented)
- **Cost/300pg:** Estimated cost per 300-page book
- **Python SDK:** Official Python package availability
- **Processing Speed:** Relative speed (Fast = <1 sec, Moderate = 1-5 sec, Slow = >5 sec per page)
- **Data Retention:** Cloud data handling policy

---

## PART 2: INTEGRATION PATTERNS

### Pattern 1: Drop-In Replacement (Simplest)

**Use Case:** Full replacement of marker-pdf with cloud service

**Best Services:** LlamaParse, Azure AI, Unstructured.io

**Code Pattern:**
```python
# BEFORE: marker-pdf pipeline
from marker.pdf_provider import PdfProvider
pdf = PdfProvider(pdf_path)
md = pdf.to_markdown()

# AFTER: Cloud service replacement
from cloud_service_client import CloudConverter
converter = CloudConverter(api_key=os.getenv("API_KEY"))
md = converter.pdf_to_markdown(pdf_path)
```

**Advantages:**
- Simplest implementation
- No local compute needed
- Consistent output format

**Disadvantages:**
- Higher ongoing cost
- Cloud dependency (latency, availability)
- Less flexibility for custom handling

**Recommended Services:**
1. **Azure AI:** Best balance of cost, quality, Spanish support
2. **LlamaParse:** Most cost-effective
3. **Unstructured.io:** Best for hybrid (API + local options)

---

### Pattern 2: Hybrid (Recommended for Your Use Case)

**Use Case:** Local marker-pdf + cloud fallback for problem pages

**Implementation:**
```python
import marker_pdf
import azure_doc_intelligence
import anthropic

def process_book_hybrid(pdf_path, output_md_path):
    # Step 1: Local baseline
    print("Step 1: Extracting with local marker-pdf...")
    md_baseline = marker_pdf.convert(pdf_path)
    
    # Step 2: Detect problem pages
    print("Step 2: Detecting quality issues...")
    problem_pages = detect_page_issues(md_baseline, pdf_path)
    # Returns: {"scanned": [1, 5, 10], "complex_table": [23], "math": [45]}
    
    # Step 3: Route to specialized services
    print(f"Step 3: Refinement ({len(problem_pages)} pages)...")
    
    md_refined = md_baseline.copy()
    
    # OCR issues → Azure Read Model
    for page_num in problem_pages.get("scanned", []):
        page_image = extract_page_image(pdf_path, page_num)
        refined_text = azure_read_model(page_image)
        md_refined[page_num] = refined_text
    
    # Complex tables → Claude
    for page_num in problem_pages.get("complex_table", []):
        page_image = extract_page_image(pdf_path, page_num)
        refined_md = claude_extract_table(page_image)
        md_refined[page_num] = refined_md
    
    # Math → Mathpix or Claude
    for page_num in problem_pages.get("math", []):
        page_image = extract_page_image(pdf_path, page_num)
        refined_md = mathpix_convert(page_image)
        md_refined[page_num] = refined_md
    
    # Step 4: Post-process
    print("Step 4: Post-processing...")
    final_md = post_process(md_refined)
    
    # Step 5: Output
    with open(output_md_path, 'w') as f:
        f.write(final_md)
    
    return output_md_path

def detect_page_issues(md, pdf_path):
    """Detect pages with quality issues based on text metrics"""
    issues = {"scanned": [], "complex_table": [], "math": []}
    
    # High OCR confidence → likely scanned
    if confidence_score < 0.7:
        issues["scanned"].append(page_num)
    
    # Table density or formatting issues
    if count_markdown_tables > 2 and formatting_score < 0.8:
        issues["complex_table"].append(page_num)
    
    # Math equations
    if count_latex_equations > 3:
        issues["math"].append(page_num)
    
    return issues
```

**Costs:**
- Marker: ~$0 (local compute)
- Azure Read (10% of pages): ~$0.15-0.30/book
- Claude (5% refinement): ~$0.01-0.05/book
- **Total: ~$0.16-0.35 per book**

**Advantages:**
- Minimal cost overhead
- Local baseline + cloud refinement
- Flexible routing based on content
- Good fallback strategy

**Disadvantages:**
- Multi-stage pipeline complexity
- Debugging across services more complex

**Service Recommendations:**
- **Primary:** marker-pdf (local)
- **OCR fallback:** Azure AI Read Model
- **Table/complex:** Claude
- **Math:** Mathpix or Claude

---

### Pattern 3: Specialized Routing (For Mixed Document Types)

**Use Case:** Different services for different document categories

**Implementation:**
```python
def process_book_with_routing(pdf_path, doc_type="mixed"):
    """Route based on detected document type"""
    
    # Classify document
    doc_class = classify_document(pdf_path)
    # Returns: "academic", "scanned_heritage", "born_digital"
    
    if doc_class == "scanned_heritage":
        # Use Azure for maximum OCR quality
        converter = AzureAIConverter(model="read")
        md = converter.convert(pdf_path)
        
    elif doc_class == "academic" and contains_heavy_math(pdf_path):
        # Use Mathpix for math-heavy papers
        converter = MathpixConverter()
        md = converter.convert(pdf_path)
        
    else:  # born_digital, general
        # Use Marker locally, fallback to LlamaParse if needed
        try:
            md = marker_pdf.convert(pdf_path)
        except marker_pdf.ProcessingError:
            converter = LlamaParseConverter()
            md = converter.convert(pdf_path)
    
    return post_process(md)

def classify_document(pdf_path):
    """Classify document type based on characteristics"""
    pdf = pypdf.PdfReader(pdf_path)
    
    # Check for text layer (born-digital vs scanned)
    text_layer_density = measure_text_layer(pdf)
    
    # Check for math content
    math_density = scan_for_math_keywords(pdf)
    
    # Check for image density
    image_density = count_embedded_images(pdf) / len(pdf.pages)
    
    if text_layer_density < 0.3:  # Mostly images
        return "scanned_heritage"
    elif math_density > 0.3:
        return "academic"
    else:
        return "born_digital"
```

**Advantages:**
- Optimal service per document type
- Cost-efficient (use specialists where needed)
- Quality maximized per category

**Disadvantages:**
- Most complex implementation
- Multiple service integrations
- Requires document classification logic

---

### Pattern 4: LLM-Based Custom Extraction (Maximum Flexibility)

**Use Case:** Fine-grained control over output structure via LLM prompting

**Implementation:**
```python
import anthropic
import base64
from pathlib import Path

def extract_with_claude_custom(pdf_path, prompt_template=None):
    """Extract markdown with Claude custom prompts"""
    
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Default prompt for structured extraction
    if prompt_template is None:
        prompt_template = """
        You are extracting text from a PDF page image. 
        Return ONLY valid Markdown with:
        1. Headings marked with # (single for page title, ## for sections)
        2. Footnotes marked as [^1] with footnote references at end
        3. Tables as Markdown tables
        4. Math equations as LaTeX: $inline$ or $$display$$
        5. Preserve all text exactly as written (no paraphrasing)
        6. Mark unclear/OCR-error regions with [OCR UNCERTAIN: ...]
        
        Do not add commentary. Return only the Markdown.
        """
    
    # Convert PDF to images
    page_images = pdf_to_images(pdf_path)
    
    markdown_pages = []
    
    for page_num, image_path in enumerate(page_images):
        # Read image as base64
        with open(image_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')
        
        # Call Claude with vision
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt_template
                        }
                    ],
                }
            ],
        )
        
        markdown_pages.append(message.content[0].text)
        print(f"Processed page {page_num + 1}/{len(page_images)}")
    
    return "\n\n".join(markdown_pages)

def pdf_to_images(pdf_path, dpi=150):
    """Convert PDF pages to images"""
    from pdf2image import convert_from_path
    images = convert_from_path(pdf_path, dpi=dpi)
    image_paths = []
    for i, img in enumerate(images):
        path = f"/tmp/page_{i:04d}.png"
        img.save(path)
        image_paths.append(path)
    return image_paths
```

**Advantages:**
- Maximum customization
- Handles edge cases with prompt engineering
- Quality excellent for complex documents
- Spanish language native support

**Disadvantages:**
- Highest cost per page
- Slowest processing
- Hallucination risk (LLM may invent content)
- Requires prompt engineering expertise

**Best Suited For:**
- High-value documents (rare/heritage)
- Small batches (<100 pages)
- When quality > cost
- Complex layouts requiring custom logic

---

## PART 3: SERVICE-SPECIFIC INTEGRATION CODE

### Azure AI Document Intelligence Integration

```python
import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

class AzureDocConverter:
    def __init__(self, endpoint, api_key):
        self.client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
    
    def convert_pdf_to_markdown(self, pdf_path, model="prebuilt-read"):
        """Convert PDF using Azure Read or Layout model"""
        
        with open(pdf_path, "rb") as f:
            poller = self.client.begin_analyze_document(
                model,
                analyze_request=AnalyzeDocumentRequest(base64_source=base64.b64encode(f.read()).decode())
            )
        
        result = poller.result()
        markdown = self._extract_markdown(result)
        return markdown
    
    def _extract_markdown(self, result):
        """Convert Azure JSON structure to Markdown"""
        md_lines = []
        
        for page in result.pages:
            # Extract headings with roles
            for line in page.lines:
                role = getattr(line, 'role', None)
                content = line.content
                
                if role == "pageHeader":
                    md_lines.append(f"# {content}\n")
                elif role == "pageFooter":
                    md_lines.append(f"*{content}*\n")
                elif role == "footnote":
                    md_lines.append(f"[^footnote]: {content}\n")
                elif role == "title":
                    md_lines.append(f"# {content}\n")
                elif role == "sectionHeading":
                    md_lines.append(f"## {content}\n")
                else:
                    md_lines.append(f"{content}\n")
        
        # Handle tables
        for table in result.tables:
            md_lines.append(self._table_to_markdown(table))
        
        return "".join(md_lines)
    
    def _table_to_markdown(self, table):
        """Convert Azure table structure to Markdown"""
        rows = [[cell.content for cell in row] for row in table.cells]
        
        # Header separator
        header = "| " + " | ".join(rows[0]) + " |\n"
        separator = "|" + "|".join(["---"] * len(rows[0])) + "|\n"
        
        # Data rows
        data = "".join([f"| {' | '.join(row)} |\n" for row in rows[1:]])
        
        return header + separator + data

# Usage
endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
converter = AzureDocConverter(endpoint, api_key)
md = converter.convert_pdf_to_markdown("book.pdf")
```

### LlamaParse Integration

```python
from llama_index.readers.file import PDFReader
from llama_parse import LlamaParse

class LlamaParseConverter:
    def __init__(self, api_key):
        self.parser = LlamaParse(api_key=api_key, result_type="markdown")
    
    def convert_pdf_to_markdown(self, pdf_path):
        """Convert PDF using LlamaParse"""
        documents = self.parser.load_data(pdf_path)
        
        # Combine all documents into single markdown
        markdown = "\n\n".join([doc.text for doc in documents])
        return markdown
    
    def convert_pdf_with_batching(self, pdf_paths, batch_size=10):
        """Process multiple PDFs efficiently"""
        results = {}
        for i, pdf_path in enumerate(pdf_paths):
            if i % batch_size == 0:
                print(f"Processing batch: {i}/{len(pdf_paths)}")
            results[pdf_path] = self.convert_pdf_to_markdown(pdf_path)
        return results

# Usage
converter = LlamaParseConverter(api_key=os.getenv("LLAMA_CLOUD_API_KEY"))
md = converter.convert_pdf_to_markdown("book.pdf")
```

### Mathpix Integration

```python
from mathpix_pdf2markdown import ConverterPDF

class MathpixConverter:
    def __init__(self, api_key, api_id):
        self.converter = ConverterPDF(
            mathpix_api_id=api_id,
            mathpix_api_key=api_key
        )
    
    def convert_pdf_to_markdown(self, pdf_path):
        """Convert PDF using Mathpix API"""
        return self.converter.convert(pdf_path, output_format="markdown")
    
    def convert_with_options(self, pdf_path, 
                           output_format="markdown",
                           skip_tables=False,
                           math_inline_delimiters=("$", "$")):
        """Convert with custom options"""
        return self.converter.convert(
            pdf_path,
            output_format=output_format,
            skip_tables=skip_tables,
            math_inline_delimiters=math_inline_delimiters
        )

# Usage
converter = MathpixConverter(
    api_key=os.getenv("MATHPIX_API_KEY"),
    api_id=os.getenv("MATHPIX_API_ID")
)
md = converter.convert_pdf_to_markdown("academic_paper.pdf")
```

### Claude Vision-Based Extraction

```python
import anthropic
import base64
import os
from pathlib import Path

class ClaudeDocumentExtractor:
    def __init__(self, model="claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = model
    
    def extract_page_to_markdown(self, image_path):
        """Extract single page image to Markdown"""
        
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system="""You are a document extraction expert. Extract text from the PDF page image and return ONLY valid Markdown.

Requirements:
1. Preserve all text exactly as written
2. Mark headings: # for titles, ## for sections, ### for subsections
3. Mark footnotes as [^1] references
4. Convert tables to Markdown format
5. Preserve equations as LaTeX: $inline$ or $$display$$
6. Maintain reading order
7. Mark OCR-uncertain regions as [?]
8. Do NOT add commentary or explanations
9. Do NOT paraphrase or reword
10. Return ONLY the Markdown content""",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extract this page to Markdown following the requirements above."
                        }
                    ],
                }
            ],
        )
        
        return message.content[0].text
    
    def extract_pdf_to_markdown(self, pdf_path):
        """Extract full PDF to Markdown via image pages"""
        from pdf2image import convert_from_path
        
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=150)
        
        markdown_pages = []
        for i, img in enumerate(images):
            # Save image temporarily
            temp_path = f"/tmp/page_{i:04d}.png"
            img.save(temp_path)
            
            # Extract to markdown
            page_md = self.extract_page_to_markdown(temp_path)
            markdown_pages.append(page_md)
            
            print(f"Extracted page {i + 1}/{len(images)}")
            
            # Clean up
            Path(temp_path).unlink()
        
        return "\n\n---\n\n".join(markdown_pages)

# Usage
extractor = ClaudeDocumentExtractor()
md = extractor.extract_pdf_to_markdown("book.pdf")
```

---

## PART 4: POST-PROCESSING PIPELINE

### Unified Post-Processing Module

```python
import re
from pathlib import Path
from typing import List, Dict

class PostProcessor:
    def __init__(self):
        self.footnote_map = {}  # Map footnote references to definitions
        self.citation_refs = []  # Track citations
    
    def process(self, markdown_text: str) -> str:
        """Run full post-processing pipeline"""
        
        # 1. Normalize whitespace
        md = self._normalize_whitespace(markdown_text)
        
        # 2. Fix hyphenated words
        md = self._fix_hyphenated_words(md)
        
        # 3. Link footnotes
        md = self._link_footnotes(md)
        
        # 4. Link author-year citations
        md = self._link_citations(md)
        
        # 5. Normalize heading levels
        md = self._normalize_headings(md)
        
        # 6. Fix tables
        md = self._fix_markdown_tables(md)
        
        # 7. Normalize math
        md = self._normalize_math(md)
        
        return md
    
    def _normalize_whitespace(self, text: str) -> str:
        """Remove excess whitespace while preserving structure"""
        # Remove multiple blank lines
        text = re.sub(r'\n\n\n+', '\n\n', text)
        # Remove trailing whitespace from lines
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        return text
    
    def _fix_hyphenated_words(self, text: str) -> str:
        """Fix words split across lines (common in PDFs)"""
        # Pattern: word-\n word
        pattern = r'(\w+)-\n(\w+)'
        text = re.sub(pattern, r'\1\2', text)
        return text
    
    def _link_footnotes(self, text: str) -> str:
        """Link inline footnote markers to definitions"""
        # Find footnote definitions: [^1] or similar
        footnote_defs = re.findall(r'\[\^(\d+)\]:\s*(.+?)(?=\n\[|\Z)', text, re.DOTALL)
        
        for ref_num, content in footnote_defs:
            self.footnote_map[ref_num] = content.strip()
        
        # Ensure footnote references are properly formatted
        text = re.sub(r'\b(\d+)\s*(?=\n|\s*[.,;])', r'[^\1]', text)
        
        return text
    
    def _link_citations(self, text: str) -> str:
        """Link author-year citations (e.g., Smith 2020 → Smith, 2020)"""
        # Pattern: Author YYYY
        pattern = r'\b([A-Z][a-z]+)\s+(19|20)\d{2}\b'
        text = re.sub(pattern, r'\1, \2', text)
        
        # Pattern: (Author YYYY) or [Author YYYY]
        pattern = r'[\(\[]([A-Z][a-z]+)\s+(19|20)\d{2}[\)\]]'
        text = re.sub(pattern, r'(\1, \2)', text)
        
        return text
    
    def _normalize_headings(self, text: str) -> str:
        """Ensure heading hierarchy is logical"""
        lines = text.split('\n')
        normalized = []
        heading_stack = []  # Track heading levels
        
        for line in lines:
            match = re.match(r'^(#+)\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                content = match.group(2)
                
                # Adjust if level is not sequential
                if heading_stack and level > heading_stack[-1] + 1:
                    level = heading_stack[-1] + 1
                
                heading_stack = [l for l in heading_stack if l < level]
                heading_stack.append(level)
                
                normalized.append('#' * level + ' ' + content)
            else:
                normalized.append(line)
        
        return '\n'.join(normalized)
    
    def _fix_markdown_tables(self, text: str) -> str:
        """Fix malformed Markdown tables"""
        lines = text.split('\n')
        fixed = []
        i = 0
        
        while i < len(lines):
            # Detect table start (line with |)
            if '|' in lines[i]:
                table_lines = [lines[i]]
                i += 1
                
                # Collect table lines
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                
                # Normalize table
                fixed_table = self._normalize_table(table_lines)
                fixed.extend(fixed_table)
            else:
                fixed.append(lines[i])
                i += 1
        
        return '\n'.join(fixed)
    
    def _normalize_table(self, table_lines: List[str]) -> List[str]:
        """Ensure all table rows have same number of columns"""
        rows = [re.split(r'\s*\|\s*', line.strip('|').strip()) for line in table_lines]
        
        # Find max columns
        max_cols = max(len(row) for row in rows)
        
        # Pad rows
        for row in rows:
            while len(row) < max_cols:
                row.append('')
        
        # Format as Markdown
        result = []
        for i, row in enumerate(rows):
            result.append('| ' + ' | '.join(cell.strip() for cell in row) + ' |')
            if i == 0:  # Add separator after header
                result.append('|' + '|'.join(['---'] * max_cols) + '|')
        
        return result
    
    def _normalize_math(self, text: str) -> str:
        """Normalize LaTeX/math notation"""
        # Convert $$ to newline-delimited for display math
        text = re.sub(r'\$\$', '\n$$\n', text)
        
        # Ensure spaces around inline $
        text = re.sub(r'(\w)\$', r'\1 $', text)
        text = re.sub(r'\$(\w)', r'$ \1', text)
        
        # Fix common OCR errors in math
        text = text.replace('l', 'l')  # Ensure lowercase L
        
        return text

# Usage
processor = PostProcessor()
final_md = processor.process(extracted_markdown)
```

---

## PART 5: COST CALCULATOR & MONITORING

```python
from datetime import datetime
from typing import Dict, List

class CostMonitor:
    def __init__(self):
        self.service_costs = {
            "mathpix": 0.005,  # $/page
            "azure_read": 0.0015,  # $/page standard tier
            "azure_layout": 0.05,  # $/page premium
            "google_docai": 0.15,  # $/page
            "aws_textract_sync": 0.015,  # $/page
            "aws_textract_async": 0.10,  # $/page
            "claude": 0.008,  # $/page (estimated for full extraction)
            "gemini": 0.0075,  # $/page
            "gpt4o": 0.018,  # $/page
            "llamaparse": 0.001,  # $/page (estimated)
            "unstructured_api": 0.0003,  # $/element (estimate)
        }
        
        self.usage_log = []  # Track all conversions
    
    def estimate_cost(self, pdf_path: str, service: str, pages: int = None) -> float:
        """Estimate cost for single PDF"""
        
        if pages is None:
            # Try to read page count from PDF
            import pypdf
            with open(pdf_path, 'rb') as f:
                pages = len(pypdf.PdfReader(f).pages)
        
        cost_per_page = self.service_costs.get(service, 0)
        total_cost = pages * cost_per_page
        
        return total_cost
    
    def estimate_batch_cost(self, pdf_list: List[str], service: str, pages_per_pdf: int = 300) -> float:
        """Estimate cost for batch of PDFs"""
        total_cost = 0
        
        for pdf_path in pdf_list:
            cost = self.estimate_cost(pdf_path, service, pages_per_pdf)
            total_cost += cost
        
        return total_cost
    
    def log_usage(self, pdf_path: str, service: str, pages: int, actual_cost: float):
        """Log actual usage for monitoring"""
        self.usage_log.append({
            "timestamp": datetime.now(),
            "pdf": pdf_path,
            "service": service,
            "pages": pages,
            "cost": actual_cost
        })
    
    def generate_report(self) -> Dict:
        """Generate usage report"""
        if not self.usage_log:
            return {"error": "No usage data"}
        
        report = {
            "total_cost": sum(entry["cost"] for entry in self.usage_log),
            "total_pages": sum(entry["pages"] for entry in self.usage_log),
            "total_documents": len(set(entry["pdf"] for entry in self.usage_log)),
            "by_service": {},
            "cost_per_page": 0,
        }
        
        for entry in self.usage_log:
            service = entry["service"]
            if service not in report["by_service"]:
                report["by_service"][service] = {
                    "cost": 0,
                    "pages": 0,
                    "documents": 0
                }
            report["by_service"][service]["cost"] += entry["cost"]
            report["by_service"][service]["pages"] += entry["pages"]
            report["by_service"][service]["documents"] += 1
        
        if report["total_pages"]:
            report["cost_per_page"] = report["total_cost"] / report["total_pages"]
        
        return report

# Usage
monitor = CostMonitor()

# Estimate before processing
estimated = monitor.estimate_cost("book.pdf", "azure_read")
print(f"Estimated cost: ${estimated:.2f}")

# Log actual usage
monitor.log_usage("book.pdf", "azure_read", 300, actual_cost=0.45)

# Generate report
report = monitor.generate_report()
print(f"Total spent: ${report['total_cost']:.2f}")
print(f"Cost per page: ${report['cost_per_page']:.4f}")
```

---

## PART 6: CONFIGURATION TEMPLATES

### Environment Setup

```bash
# .env.example for cloud service credentials

# Azure AI Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://[region].api.cognitive.microsoft.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your_key_here

# Mathpix
MATHPIX_API_ID=your_id_here
MATHPIX_API_KEY=your_key_here

# Claude (Anthropic)
ANTHROPIC_API_KEY=your_key_here

# Gemini (Google)
GOOGLE_API_KEY=your_key_here

# GPT-4o (OpenAI)
OPENAI_API_KEY=your_key_here

# LlamaParse
LLAMA_CLOUD_API_KEY=your_key_here

# AWS (for Textract)
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_key_here
AWS_REGION=us-east-1

# Mistral
MISTRAL_API_KEY=your_key_here
```

### Service Configuration YAML

```yaml
# services_config.yaml
services:
  marker_local:
    type: local
    enabled: true
    compute: cpu  # or gpu
    timeout: 300

  azure_ai:
    type: cloud
    enabled: true
    endpoint: ${AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT}
    api_key: ${AZURE_DOCUMENT_INTELLIGENCE_KEY}
    model: prebuilt-read
    cost_per_page: 0.0015
    timeout: 60

  mathpix:
    type: cloud
    enabled: true
    api_id: ${MATHPIX_API_ID}
    api_key: ${MATHPIX_API_KEY}
    cost_per_page: 0.005
    timeout: 120

  claude:
    type: llm
    enabled: true
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-3-5-sonnet-20241022
    cost_per_page: 0.008
    timeout: 60

  gemini:
    type: llm
    enabled: false  # Optional
    api_key: ${GOOGLE_API_KEY}
    model: gemini-2-0-flash
    cost_per_page: 0.0075

routing:
  default: marker_local
  fallback_ocr: azure_ai
  fallback_math: mathpix
  fallback_complex: claude
  quality_tiers:
    budget: llamaparse
    standard: azure_ai + marker_local
    premium: claude
```

---

## PART 7: TROUBLESHOOTING & LIMITS

### Service Limits & Quotas

| Service | Rate Limit | Request Size | Processing Time | Notes |
|---------|-----------|-----------|-----------|---------|
| Azure | 20 pages/min | 50 MB | 10-30s | Async batch available |
| Mathpix | 100 pages/day (free) | 100 MB | 20-60s | Fast for math |
| Claude | 50K input tokens/min (free tier) | 100 MB images | 5-15s | Per-message limit |
| Gemini | 15 RPM (free tier) | 100 MB | 5-10s | Most generous free tier |
| GPT-4o | 3500 RPM (free tier) | 20 MB | 5-15s | Token-based, not per-image |
| AWS Textract | 5 TPM (free tier) | 500 MB | Fast sync | Unlimited async |
| LlamaParse | Depends on tier | 100 MB | 10-20s | API-first |

### Common Issues & Solutions

**Issue: High character count from Claude but seems correct**
- Claude charges by token, not by page; output can use 2000+ tokens
- Solution: Monitor input + output tokens separately

**Issue: Azure fails on scanned Spanish books**
- Azure doesn't support Spanish + scanned combination in all regions
- Solution: Test in all regions or fallback to Claude

**Issue: Math extraction produces malformed LaTeX**
- Mathpix sometimes produces mixed notation
- Solution: Post-process with regex, validate LaTeX

**Issue: Cost unexpectedly high**
- Check if using expensive models (GPT-4o vs Gemini)
- Check batch vs. per-page pricing
- Solution: Monitor usage logs, implement spending alerts

---

## REFERENCES

- **Azure AI:** https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/
- **Mathpix:** https://mathpix.com/docs
- **Claude:** https://docs.anthropic.com/
- **Gemini:** https://ai.google.dev/
- **AWS Textract:** https://docs.aws.amazon.com/textract/latest/dg/
- **LlamaParse:** https://docs.llamaindex.ai/
- **Unstructured.io:** https://docs.unstructured.io/
- **Mistral:** https://docs.mistral.ai/

