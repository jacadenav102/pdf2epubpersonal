#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path
import modules.pdf2md as pdf2md
import modules.mark2epub as mark2epub
import modules.md2epub_pandoc as md2epub_pandoc
import modules.postprocessing as postprocessing
import modules.cover as cover
import torch


def prepare_epub_cover(markdown_dir: Path, pdf_path: Path, spec: str | None) -> None:
    """
    Create the EPUB cover. An explicit --cover value must work (errors fail
    this PDF); the automatic default only warns when it cannot make a cover.
    """
    if spec is None and sys.stdin.isatty():
        spec = cover.ask_cover_spec()
    explicit = cover.parse_cover_spec(spec)[0] != cover.AUTO
    try:
        path = cover.prepare_cover(markdown_dir, pdf_path, spec)
    except Exception as e:
        if explicit:
            raise
        print(f"Warning: could not create a cover from the PDF ({e}); continuing without one")
        return
    print(f"Cover: {path.name if path else 'none'}")


def main():
    if torch.cuda.is_available():
        print("CUDA is available. Using GPU for processing.")
    elif torch.backends.mps.is_available():
        print("MPS is available. Using Apple Silicon for processing.")
    else:
        print("CUDA is not available. Using CPU for processing.")
        
    parser = argparse.ArgumentParser(
        description='Convert PDF files to EPUB format via Markdown'
    )
    parser.add_argument(
        'input_path',
        nargs='?',
        type=str,
        help='Path to input PDF file or directory (default: ./input/*.pdf)'
    )
    parser.add_argument(
        'output_path',
        nargs='?',
        type=str,
        help='Path to output directory (default: directory named after PDF)'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=None,
        help='Maximum number of pages to process'
    )
    parser.add_argument(
        '--start-page',
        type=int,
        default=None,
        help='Page number to start from'
    )
    parser.add_argument(
        '--skip-epub',
        action='store_true',
        help='Skip EPUB generation, only create markdown'
    )
    parser.add_argument(
        '--skip-md',
        action='store_true',
        help='Skip markdown generation, use existing markdown files'
    )
    
    parser.add_argument(
        '--cover',
        type=str,
        default=None,
        metavar='SPEC',
        help='EPUB cover: a PDF page number (e.g. 3), a path to an image file, or "none". '
             'Default: the first non-blank page of the PDF (asked interactively when '
             'running in a terminal)'
    )
    parser.add_argument(
        '--use-llm',
        action='store_true',
        help='Use Claude (Anthropic API) to refine tables, equations, headers and '
             'complex regions. Requires the ANTHROPIC_API_KEY environment variable.'
    )
    parser.add_argument(
        '--llm-model',
        type=str,
        default=None,
        help='Claude model name to use with --use-llm '
             f'(default: $CLAUDE_MODEL or {pdf2md.DEFAULT_CLAUDE_MODEL})'
    )
    parser.add_argument(
        '--llm-concurrency',
        type=int,
        default=pdf2md.DEFAULT_LLM_CONCURRENCY,
        help='Parallel LLM requests (default: %(default)s; marker default is 3). '
             'Lower it if you keep hitting rate limits.'
    )
    parser.add_argument(
        '--llm-rpm',
        type=float,
        default=0,
        help='Hard cap on LLM requests per minute (default: 0 = adaptive, driven by '
             'the API rate-limit headers and retry-after)'
    )
    parser.add_argument(
        '--llm-max-retries',
        type=int,
        default=pdf2md.DEFAULT_LLM_MAX_RETRIES,
        help='Retries per LLM request on rate limits/overload/timeouts (default: %(default)s)'
    )
    parser.add_argument(
        '--no-llm-cache',
        action='store_true',
        help='Do not checkpoint LLM responses in <output>/.llm_cache (re-runs pay again)'
    )
    parser.add_argument(
        '--allow-llm-failures',
        action='store_true',
        help='Build the EPUB even if some LLM calls failed (those blocks keep the '
             'uncorrected output). By default the EPUB is skipped so you can re-run.'
    )
    parser.add_argument(
        '--epub-engine',
        choices=['auto', 'pandoc', 'legacy'],
        default='auto',
        help='EPUB builder: pandoc (chapters split by heading, TOC from headings, '
             'pop-up footnotes), legacy (built-in mark2epub), or auto = pandoc if '
             'available, otherwise legacy (default: auto)'
    )
    parser.add_argument(
        '--toc-depth',
        type=int,
        default=2,
        help='Heading levels included in the table of contents (pandoc engine, default: 2)'
    )
    parser.add_argument(
        '--no-postprocess',
        action='store_true',
        help='Do not post-process the markdown (footnote linking, cleanup, citation links)'
    )
    parser.add_argument(
        '--no-citation-links',
        action='store_true',
        help='Do not link author-year citations to the bibliography'
    )
    parser.add_argument(
        '--no-ligature-fix',
        action='store_true',
        help='Do not re-join words split at fi/fl ligatures ("identifi cado")'
    )
    parser.add_argument(
        '--no-table-rescue',
        action='store_true',
        help='Do not convert text blocks that look like borderless tables into tables '
             '(by default they are detected from column layout + a nearby table caption)'
    )
    parser.add_argument(
        '--no-heading-fix',
        action='store_true',
        help='Keep marker\'s heading levels (by default they are normalized using the '
             'PDF bookmarks, or chapter heuristics when the PDF has none)'
    )
    
    args = parser.parse_args()

    epub_engine = args.epub_engine
    if epub_engine == 'auto':
        epub_engine = 'pandoc' if md2epub_pandoc.find_pandoc() else 'legacy'
        if epub_engine == 'legacy' and not args.skip_epub:
            print("Note: pandoc not found; using the legacy EPUB builder "
                  "(install pandoc or pypandoc_binary for chapter splitting and a full TOC).")
    elif epub_engine == 'pandoc' and not args.skip_epub and not md2epub_pandoc.find_pandoc():
        print("Error: --epub-engine pandoc requested but pandoc was not found "
              "(install pandoc or `pip install pypandoc_binary`).", file=sys.stderr)
        sys.exit(1)

    if args.use_llm and args.skip_md:
        print("Warning: --use-llm has no effect with --skip-md.", file=sys.stderr)
    if args.use_llm and not args.skip_md and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: --use-llm requires the ANTHROPIC_API_KEY environment variable.",
              file=sys.stderr)
        sys.exit(1)
    
    # Get input path
    input_path = Path(args.input_path) if args.input_path else pdf2md.get_default_input_dir()
    
    # Get queue of PDFs to process
    queue = pdf2md.add_pdfs_to_queue(input_path)
    print(f"Found {len(queue)} PDF files to process")
    
    # Process each PDF
    failed = []
    for pdf_path in queue:
        print(f"\nProcessing: {pdf_path.name}")
        
        # Get output directory for this PDF
        if args.output_path:
            output_path = Path(args.output_path)
            markdown_dir = output_path / pdf_path.stem
        else:
            markdown_dir = pdf2md.get_default_output_dir(pdf_path)
            output_path = markdown_dir.parent
            
        try:
            # Check if markdown directory exists when skipping MD generation
            if args.skip_md:
                if not markdown_dir.exists():
                    print(f"Error: Markdown directory not found: {markdown_dir}", file=sys.stderr)
                    failed.append(pdf_path.name)
                    continue
                print(f"Using existing markdown files from: {markdown_dir}")
                
            # Convert PDF to Markdown unless skipped
            llm_incomplete = False
            if not args.skip_md:
                print("Converting PDF to Markdown...")
                llm_stats = pdf2md.convert_pdf(
                    str(pdf_path),
                    markdown_dir,
                    args.max_pages,
                    args.start_page,
                    use_llm=args.use_llm,
                    llm_model=args.llm_model,
                    llm_cache=not args.no_llm_cache,
                    llm_concurrency=args.llm_concurrency,
                    llm_rpm=args.llm_rpm,
                    llm_max_retries=args.llm_max_retries,
                    table_rescue=not args.no_table_rescue,
                )
                if llm_stats is not None and llm_stats.unsuccessful:
                    llm_incomplete = True
                    print(
                        f"\nWarning: {llm_stats.unsuccessful} LLM call(s) did not succeed; the "
                        "affected tables/blocks keep marker's uncorrected output.",
                        file=sys.stderr,
                    )
                    for err in llm_stats.errors[:5]:
                        print(f"  - {err}", file=sys.stderr)
                    if not args.no_llm_cache:
                        print(
                            "  Re-run the same command to resume: successful responses are "
                            "cached and only the failed calls will be sent again.",
                            file=sys.stderr,
                        )
            
            # Post-process markdown (idempotent, keeps a .md.orig backup)
            if not args.no_postprocess:
                postprocessing.postprocess_markdown_dir(
                    markdown_dir,
                    link_cites=not args.no_citation_links,
                    fix_ligatures=not args.no_ligature_fix,
                    fix_headings=not args.no_heading_fix,
                    pdf_path=pdf_path,
                )

            # Do not produce an incomplete EPUB silently.
            if llm_incomplete and not args.skip_epub and not args.allow_llm_failures:
                print(
                    "  EPUB not built because of the failed LLM calls "
                    "(use --allow-llm-failures to build it anyway).",
                    file=sys.stderr,
                )
                failed.append(pdf_path.name)
                continue

            # Convert Markdown to EPUB unless skipped
            if not args.skip_epub:
                prepare_epub_cover(markdown_dir, pdf_path, args.cover)
                print(f"Converting Markdown to EPUB ({epub_engine} engine)...")
                if epub_engine == 'pandoc':
                    md2epub_pandoc.convert_to_epub(markdown_dir, toc_depth=args.toc_depth)
                else:
                    mark2epub.convert_to_epub(markdown_dir, output_path)
                
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {str(e)}", file=sys.stderr)
            failed.append(pdf_path.name)
            continue

    if failed:
        print(
            f"\nFailed to process {len(failed)} of {len(queue)} PDF file(s):",
            file=sys.stderr,
        )
        for name in failed:
            print(f"  - {name}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()