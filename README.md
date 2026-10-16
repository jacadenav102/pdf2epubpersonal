# PDF2EPUB 📚

Convert PDF files to nicely structured Markdown and EPUB format with intelligent layout detection.

## ✨ Features

- 📖 Smart layout detection for books and academic papers
- 🔍 Advanced text extraction and OCR capabilities
- 📊 Table detection and formatting
- 🖼️ Image extraction and optimization
- 📝 Clean markdown output with preserved structure
- 📱 EPUB generation with customizable styling
- 🔗 Linked footnotes, bibliography-linked citations and a full table of contents (Pandoc engine)
- 🌍 Multi-language support
- 🚀 GPU acceleration support (NVIDIA & AMD)
- 🍎 Apple Silicon support

## 🛠️ Dependencies

- Python 3.10–3.14 (3.13 recommended, see below)
- PyTorch (with CUDA/ROCm support for GPU acceleration)
- marker-pdf==1.10.2
- transformers==4.57.6
- markdown==3.10.2
- latex2mathml==3.81.0
- pypandoc_binary==1.17 (bundled Pandoc for the default EPUB builder)

### ⚠️ Python version

Python 3.13 is recommended.

`marker-pdf` constrains `Pillow<11.0.0`, and Pillow only ships Python 3.14
wheels from 11.3.0 onward. On Python 3.10–3.13 every dependency installs as a
prebuilt wheel. On 3.14, pip has to build Pillow from source instead: this
works, but it is slower and requires a working C toolchain plus the image
library headers Pillow links against. On Debian/Ubuntu install them first:

```bash
sudo apt install libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev libwebp-dev
```

Without these headers the install fails with
`RequiredDependencyException: The headers or library files could not be found for jpeg`.

## 💻 Installation

1. Create and activate a virtual environment.

On Linux/Mac:
```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

On Windows:
```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
```

2. Install Python dependencies (this installs PyTorch as well):
```bash
pip install -r requirements.txt
```

3. GPU acceleration (optional):

PyTorch is installed as a dependency in step 2. On Apple Silicon that wheel
already supports MPS, so no further action is needed. For a specific CUDA or
ROCm build, reinstall PyTorch using the selector at
[pytorch.org/get-started/locally](https://pytorch.org/get-started/locally/).
For example, for AMD GPUs with ROCm:
```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2
```

4. Verify GPU support:
```python
import torch
print(torch.__version__)  # PyTorch version
print(torch.cuda.is_available())  # Should return True for NVIDIA
print(torch.backends.mps.is_available())  # Should return True for Apple Silicon
print(torch.version.hip)  # Should print ROCm version for AMD
```

### 🐳 Docker

A CPU-only image can be built from the included `Dockerfile`:

```bash
docker build -t pdf2epub .
```

Run it with your PDFs mounted at `/data` and a model cache volume (marker-pdf
downloads its models on first run):

```bash
docker run -it --rm \
  -v "$(pwd)":/data \
  -v pdf2epub-models:/models \
  pdf2epub input.pdf
```

`-it` is required for EPUB generation because metadata is prompted
interactively; with `--skip-epub` it can run non-interactively.

Tagged releases are also published to
`ghcr.io/overcuriousity/pdf2epub` by the Docker workflow.

## 🚀 Usage

### Basic Usage

Convert a single PDF file:
```bash
python main.py input.pdf
```

Convert all PDFs in a directory:
```bash
python main.py input_directory/
```

EPUB generation prompts interactively for metadata (title, author, language,
and so on; press Enter to accept each default). It therefore needs a terminal —
run it non-interactively and it will fail with `EOFError`. Use `--skip-epub` to
produce only markdown without any prompts.

### Advanced Options

```bash
python main.py [input_path] [output_path] [options]

Options:
  --max-pages INT          Maximum number of pages to process
  --start-page INT         Page number to start from
  --skip-epub              Skip EPUB generation, only create markdown
  --skip-md                Skip markdown generation, use existing markdown files
  --use-llm                Refine output with Claude (needs ANTHROPIC_API_KEY)
  --llm-model NAME         Claude model to use (default: $CLAUDE_MODEL or claude-sonnet-4-5)
  --llm-concurrency N      Parallel LLM requests (default: 2)
  --llm-rpm N              Hard cap on LLM requests per minute (default: adaptive)
  --llm-max-retries N      Retries per LLM request (default: 8)
  --no-llm-cache           Do not checkpoint LLM responses in <output>/.llm_cache
  --allow-llm-failures     Build the EPUB even if some LLM calls failed
  --epub-engine ENGINE     auto (default) | pandoc | legacy
  --toc-depth N            Heading levels in the table of contents (pandoc, default: 2)
  --no-postprocess         Keep marker's markdown untouched
  --no-citation-links      Do not link citations to the bibliography
  --no-ligature-fix        Do not re-join words split at fi/fl ligatures
  --no-table-rescue        Do not turn text blocks that look like borderless tables into tables
  --no-heading-fix         Keep marker's heading levels as they are
  --cover SPEC             EPUB cover: PDF page number, image file, or "none"
                           (default: first non-blank page of the PDF)
```

### Cover

By default the first page of the PDF is rendered as the EPUB cover
(1600 px wide, like e-reader stores recommend; a blank first page is skipped).
To choose another one:

```bash
python main.py book.pdf --cover 3              # page 3 of the PDF
python main.py book.pdf --cover portada.png    # any image (JPEG/PNG/GIF; others are converted)
python main.py book.pdf --cover none           # no cover
```

When run in a terminal without `--cover`, you are asked (Enter keeps the
first page). The cover is saved as `images/cover.jpg` in the output folder and
recorded as `cover_image` in `description.json`; if you point `cover_image`
to an image of your own there, it is kept on later runs.

If `input_path` is omitted, all PDFs in `./input/` are processed.

### Optional: Claude LLM refinement

By default all processing runs locally (Surya models via marker-pdf). With
`--use-llm`, marker-pdf additionally sends page/block images and text to
Claude (Anthropic API) to improve tables, equations, section headers and
complex regions. This is slower, costs API credits, and sends document
content to Anthropic.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python main.py book.pdf --use-llm
```

#### Rate limits and checkpoints

Long books make hundreds of LLM calls, so the Claude integration is built to
survive API rate limits (`modules/llm_service.py`, `modules/llm_resilience.py`).
It sends the same prompts as marker-pdf's own Claude service, plus:

- **Rate limiting:** a single limiter shared by all worker threads. It honors
  `retry-after` and pauses *before* a limit is hit, using the
  `anthropic-ratelimit-*` headers. `--llm-rpm N` adds a hard
  requests-per-minute cap, and `--llm-concurrency N` (default 2) sets the
  number of parallel calls.
- **Retries:** up to `--llm-max-retries` (default 8), with exponential
  backoff, on 429, 529 (overloaded), 5xx, timeouts and connection errors.
  Authentication errors stop the run immediately.
- **Structured answers:** the expected answer format is sent as a forced
  tool call, so Claude returns parsed JSON. marker's prompts show example
  answers in a non-JSON layout, and HTML inside JSON strings is easily
  mis-escaped, which used to cause `Invalid TableSchema response` warnings.
  Free-text answers are still accepted through a lenient parser. An invalid
  answer is requested once more, with a larger token budget if it was cut off.
- **Checkpoint:** every successful response is saved in
  `<output>/.llm_cache/`. If a run fails, re-run the same command: cached
  answers are reused and only the missing calls are sent again. Disable this
  with `--no-llm-cache`.
- **No silent degradation:** if any LLM call still fails, the markdown is
  saved but the EPUB is **not** built and the command exits non-zero. Re-run
  to resume, or pass `--allow-llm-failures` to build the EPUB anyway (failed
  blocks keep marker's uncorrected output).

The local (non-LLM) models run again on a resumed run. That takes time but no
API cost.

```bash
# Gentle settings for low API tiers
python main.py book.pdf --use-llm --llm-concurrency 1 --llm-rpm 20
```

### Borderless tables and vector charts

marker's layout model sometimes labels borderless tables (only horizontal
rules, common in books) as text or caption, and then their cells come out as
one flat paragraph. In that case no table processing runs, whether local or
with Claude. Vector charts can be lost the same way: only their labels
survive, as a garbled paragraph ("Onda descendente Acoplamiento … Años 0 10
15").

A small extra marker processor (`modules/table_rescue.py`) runs before table
recognition and fixes both, using the nearest caption and the line layout:

- next to a table caption (`CUADRO I.1`, `Tabla 2`, `Table 3`…), with lines
  side by side in the same row (columns): converted to a **table**. With no
  caption, only a strong column pattern counts;
- next to a figure caption (`GRÁFICA I.1`, `Figura 2`, `Figure 3`…), with
  rotated axis labels or many short scattered labels: converted to a
  **picture**, so the chart is kept as an image;
- a table **split into several blocks** (row labels read as headings, cells
  as separate paragraphs): the blocks between the table caption and its
  `FUENTE:` / `Source:` / `Nota:` line are merged into one table when they
  sit side by side in columns;
- **captions** mislabelled as running headers/footers (which marker
  deletes) are kept as captions, and a caption line detected as a table of
  its own (garbled into cells) becomes a caption again;
- a table box that **swallows part of its caption** (e.g. the second caption
  line becomes the first table row) is trimmed and the line goes back to the
  caption;
- a table box that covers **only part of the table** (e.g. the header), with
  the remaining rows labelled as an overlapping caption/text block, is grown
  over that block so every row is recognised.

Lists, pictures and normal prose are never changed. Disable with
`--no-table-rescue`.

### Markdown post-processing

After marker-pdf produces the markdown (and also with `--skip-md`), it is
post-processed in place. The original is kept once as `<name>.md.orig`, and
every step is idempotent, so re-running is safe:

1. **Cleanup**: small-caps letters misread as superscripts (`<sup>Y</sup>`),
   escaped `<sup>` artifacts, and words split at fi/fl ligatures
   (`identifi cado` → `identificado`).
2. **Headings**: marker sets heading levels from font sizes, which often
   gives chapters `###` and captions `#`. Since the EPUB is split into
   chapters at level-1 headings and its table of contents comes from the
   headings, levels are normalized:
   - If the PDF has bookmarks (an outline), headings are matched to them in
     reading order (tolerant to truncated titles like `TÍTULO (...)`,
     case/accents, and headings split over two lines) and take the bookmark
     level. Bookmarked titles that marker left as plain text are promoted;
     other headings go one level below their section.
   - Otherwise, chapter-like headings (`CAPÍTULO 3`, `Chapter 3`,
     `IV. TÍTULO`, `INTRODUCCIÓN`, `Bibliography`, …) become level 1 and the
     rest are renumbered below them.
   - Figure/table captions output as headings (`GRÁFICA IV.7. …`,
     `Table 2 …`) become bold text.
3. **Footnotes**: PDF-style notes (`texto.3` … `<sup>3</sup> Nota…`) become
   Markdown footnotes (`[^c2-3]`). Numbering is tracked per chapter; a note is
   only converted when its reference is found, otherwise it is left as-is.
4. **Citations**: author-year citations (`Modelski (1987)`,
   `(Cassidy, 2002; Ernst, 2010)`) get their year linked to the matching entry
   of the *Bibliografía / Referencias / Bibliography* section. Unmatched or
   ambiguous citations stay plain text.

A summary is printed, e.g.
`39 heading(s) adjusted using the PDF outline (30/31 outline entries found; …)`,
`54 footnote(s) linked`,
`230 bibliography entries anchored, 706 citation(s) linked`.

### EPUB engines

- **pandoc** (default when available; bundled via `pypandoc_binary`): one
  chapter file per level-1 heading, table of contents built from headings
  (`--toc-depth`), pop-up footnotes with back-links, and internal links that
  work across chapter files.
- **legacy**: the built-in `mark2epub` builder (one chapter per markdown file).
  Footnotes are linked too, but the TOC only lists markdown files.

Both read and write the same `description.json` metadata.

### Examples

Process a specific range of pages:
```bash
python main.py book.pdf --start-page 10 --max-pages 50
```

Convert to markdown only:
```bash
python main.py thesis.pdf --skip-epub
```

### Output Structure

```
output_directory/
├── document_name/
│   ├── document_name.md
│   ├── document_name.epub
│   ├── document_name_metadata.json
│   └── images/
│       ├── image1.png
│       ├── image2.jpg
│       └── ...
```

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to your branch
5. Create a Pull Request

Please ensure your code follows the existing style and includes appropriate tests.

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/overcuriousity/pdf2epub.git
cd pdf2epub
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install development dependencies:
```bash
pip install -r requirements.txt
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Known Issues

- Some image embedding might need manual adjustment
- Some complex mathematical equations might not be perfectly converted
- Certain PDF layouts with multiple columns may require manual adjustment
- Font detection might be imperfect in some cases

## 🙏 Acknowledgments

This project builds upon several excellent open-source libraries:
- [marker-pdf](https://github.com/VikParuchuri/marker) for PDF processing
- [mark2epub](https://github.com/AlexPof/mark2epub) for markdown conversion
- [PyTorch](https://pytorch.org/) for GPU acceleration
- [Transformers](https://huggingface.co/transformers) for advanced text processing
