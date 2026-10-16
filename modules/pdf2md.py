from pathlib import Path
import os
import sys
import json
from PIL import Image
import io

def get_default_output_dir(input_path: Path) -> Path:
    """
    Generate default output directory path based on input PDF path.
    Creates a directory with same name as PDF (without extension) next to the PDF.
    """
    return input_path.parent / input_path.stem

def get_default_input_dir() -> Path:
    """
    Get default input directory (./input) relative to current working directory.
    Creates it if it doesn't exist.
    """
    input_dir = Path.cwd() / 'input'
    input_dir.mkdir(exist_ok=True)
    return input_dir


def save_images(images: dict, image_dir: Path) -> None:
    """
    Save images with proper error handling and format detection.
    Preserves original image filenames from the input.
    
    Args:
        images: Dictionary of images from marker-pdf conversion where keys are filenames
        image_dir: Directory to save images to
    """
    if not images:
        print("No images found in document")
        return
        
    image_dir.mkdir(exist_ok=True)
    saved_count = 0
    
    for filename, image_data in images.items():
        try:
            # Skip if image data is None or empty
            if not image_data:
                continue
                
            image_path = image_dir / filename
            
            # Handle different image data formats
            if isinstance(image_data, Image.Image):
                image_data.save(image_path)
                saved_count += 1
                    
            elif isinstance(image_data, bytes):
                img = Image.open(io.BytesIO(image_data))
                img.save(image_path)
                saved_count += 1
                    
            elif isinstance(image_data, str):
                if Path(image_data).exists():
                    img = Image.open(image_data)
                    img.save(image_path)
                    saved_count += 1
                else:
                    print(f"Image path does not exist: {image_data}")
            else:
                print(f"Unsupported image data type for {filename}: {type(image_data)}")
                
        except Exception as e:
            print(f"Error saving image {filename}: {str(e)}")
            continue
            
    if saved_count > 0:
        print(f"Successfully saved {saved_count} images to: {image_dir}")
    else:
        print("No valid images were found to save")

# Resilient drop-in for marker.services.claude.ClaudeService (same prompts),
# adding rate limiting, retries and a response cache. See modules/llm_service.py.
CLAUDE_LLM_SERVICE = "modules.llm_service.ResilientClaudeService"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5"
LLM_CACHE_DIRNAME = ".llm_cache"
DEFAULT_LLM_CONCURRENCY = 2
DEFAULT_LLM_MAX_RETRIES = 8


def build_llm_config(
    use_llm: bool,
    llm_model: str | None = None,
    cache_dir: Path | None = None,
    concurrency: int = DEFAULT_LLM_CONCURRENCY,
    requests_per_minute: float = 0,
    max_retries: int = DEFAULT_LLM_MAX_RETRIES,
) -> tuple[dict, str | None]:
    """
    Build the marker-pdf config entries and service path needed to enable
    Claude as the LLM refinement layer.

    Returns a (config, llm_service) tuple. When use_llm is False, returns an
    empty config and None so marker runs fully locally.

    The API key is read from the ANTHROPIC_API_KEY environment variable and
    is never accepted on the command line (to keep it out of shell history).

    cache_dir: where successful responses are checkpointed (None disables).
    concurrency: parallel LLM requests per marker processor (marker default: 3).
    requests_per_minute: optional hard cap; 0 relies on the adaptive limiter.
    """
    if not use_llm:
        return {}, None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "--use-llm requires the ANTHROPIC_API_KEY environment variable to be set."
        )

    config = {
        "use_llm": True,
        "claude_api_key": api_key,
        "claude_model_name": llm_model or os.environ.get("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL),
        # Applied by marker to every LLM processor that has this attribute.
        "max_concurrency": max(1, int(concurrency)),
        "max_retries": max(0, int(max_retries)),
        "llm_requests_per_minute": max(0.0, float(requests_per_minute)),
        "llm_cache_dir": str(cache_dir) if cache_dir else "",
    }
    return config, CLAUDE_LLM_SERVICE


def convert_pdf(
    input_path: str,
    output_dir: Path,
    max_pages: int = None,
    start_page: int = None,
    use_llm: bool = False,
    llm_model: str | None = None,
    llm_cache: bool = True,
    llm_concurrency: int = DEFAULT_LLM_CONCURRENCY,
    llm_rpm: float = 0,
    llm_max_retries: int = DEFAULT_LLM_MAX_RETRIES,
    table_rescue: bool = True,
):
    """
    Convert a single PDF file to markdown format with enhanced image handling.

    table_rescue relabels text blocks that are really borderless tables as
    tables before marker's table processing (see modules/table_rescue.py).

    If use_llm is True, Claude (Anthropic API) is used by marker-pdf to refine
    tables, equations, section headers, complex regions, etc. Successful LLM
    responses are checkpointed in <output_dir>/.llm_cache, so re-running after
    a failure only re-sends the calls that did not succeed.

    Returns the run's LLMStats when use_llm is True, otherwise None.
    """
    try:
        from marker.models import create_model_dict
        from marker.converters.pdf import PdfConverter

        cache_dir = (Path(output_dir) / LLM_CACHE_DIRNAME).resolve() if (use_llm and llm_cache) else None
        llm_config, llm_service = build_llm_config(
            use_llm,
            llm_model,
            cache_dir=cache_dir,
            concurrency=llm_concurrency,
            requests_per_minute=llm_rpm,
            max_retries=llm_max_retries,
        )
        llm = None
        if llm_service:
            from modules import llm_service as llm

            llm.reset_state(requests_per_minute=llm_config["llm_requests_per_minute"])
            print(f"LLM refinement enabled: Claude ({llm_config['claude_model_name']}), "
                  f"concurrency {llm_config['max_concurrency']}"
                  + (f", max {llm_rpm:g} req/min" if llm_rpm else ", adaptive rate limiting"))
            if cache_dir:
                from modules.llm_resilience import ResponseCache

                cached = len(ResponseCache(cache_dir))
                print(f"LLM checkpoint: {cache_dir}"
                      + (f" ({cached} cached response(s) will be reused)" if cached else ""))

        models = create_model_dict()

        # Build page_range config. marker-pdf 1.x requires an explicit list of
        # page indices; there is no "start to end" shorthand. If start_page is
        # given without max_pages we cannot construct the range without knowing
        # the document's page count, so we warn and process all pages instead.
        config = dict(llm_config)
        if max_pages is not None:
            s = start_page or 0
            config["page_range"] = list(range(s, s + max_pages))
        elif start_page is not None:
            print(
                "Warning: --start-page requires --max-pages in marker-pdf 1.x "
                "(no open-ended page range is supported). Processing all pages."
            )

        processor_list = None
        if table_rescue:
            from modules.table_rescue import processor_list_with_rescue

            processor_list = processor_list_with_rescue(PdfConverter.default_processors)

        converter = PdfConverter(
            config=config,
            artifact_dict=models,
            processor_list=processor_list,
            llm_service=llm_service,
        )
        rendered = converter(input_path)

        if llm is not None:
            stats = llm.get_stats()
            print(f"LLM summary: {stats.summary()}")
            fatal = llm.get_fatal_error()
            if fatal is not None:
                raise RuntimeError(f"LLM refinement aborted: {fatal}")

        full_text = rendered.markdown
        images = rendered.images
        metadata = rendered.metadata

        # All output will go to the output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save markdown content
        md_output = output_dir / f"{Path(input_path).stem}.md"
        md_output.write_text(full_text, encoding='utf-8')
        print(f"Markdown saved to: {md_output}")
        # A backup from a previous post-processing run no longer matches the
        # freshly generated markdown; drop it so the next backup is correct.
        stale_backup = md_output.with_name(md_output.name + ".orig")
        if stale_backup.exists():
            stale_backup.unlink()

        # Save metadata as JSON
        meta_output = output_dir / f"{Path(input_path).stem}_metadata.json"
        with open(meta_output, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        print(f"Metadata saved to: {meta_output}")

        # Enhanced image handling
        try:
            if images:
                image_dir = output_dir / "images"
                save_images(images, image_dir)

                # Cleanup PIL Images
                for img in images.values():
                    if isinstance(img, Image.Image):
                        try:
                            img.close()
                        except Exception as e:
                            print(f"Warning: Failed to close image: {e}")
                images.clear()
        except Exception as e:
            print(f"Warning: Error during image cleanup: {e}")

        return llm.get_stats() if llm is not None else None

    except Exception as e:
        print(f"Error converting {input_path}: {str(e)}", file=sys.stderr)
        raise

    
def add_pdfs_to_queue(input_path: Path) -> list[Path]:
    """
    Add PDF files to the processing queue.
    If input_path is a directory, add all PDFs in it.
    If input_path is a file, add just that file.
    """
    queue = []
    
    if input_path.is_dir():
        pdfs = list(input_path.glob('*.pdf'))
        if not pdfs:
            print(f"No PDF files found in directory: {input_path}", file=sys.stderr)
            sys.exit(1)
        queue.extend(pdfs)
    else:
        if not input_path.is_file():
            print(f"Error: Input file does not exist: {input_path}", file=sys.stderr)
            sys.exit(1)
        if input_path.suffix.lower() != '.pdf':
            print(f"Error: Input file must be a PDF: {input_path}", file=sys.stderr)
            sys.exit(1)
        queue.append(input_path)
        
    return queue
