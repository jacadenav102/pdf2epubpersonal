"""
EPUB cover selection.

By default the first (non-blank) page of the source PDF is rendered as the
cover. The user can instead choose another PDF page, an image file, or no
cover. The chosen image is stored as <markdown_dir>/images/cover.<ext> and
recorded as "cover_image" in description.json, which both EPUB engines read
(pandoc passes it to --epub-cover-image; the legacy builder marks it as the
cover-image item).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

COVER_STEM = "cover"
# Image types allowed for EPUB covers (core media types).
EPUB_COVER_TYPES = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".gif": "GIF"}
# Common e-reader cover size (Kindle/Kobo recommendation: 1600 x 2560).
TARGET_WIDTH = 1600
MAX_HEIGHT = 2560
BLANK_STDDEV = 4.0          # below this (0-255 scale) a rendered page counts as blank
AUTO_MAX_PAGES = 3          # pages tried when looking for a non-blank first page

AUTO, NONE = "auto", "none"


class CoverError(ValueError):
    pass


def parse_cover_spec(spec: str | None) -> tuple[str, object]:
    """
    Interpret a --cover value:
      None/""/"auto"      -> ("auto", None)    first non-blank PDF page
      "none"/"no"/"off"   -> ("none", None)    no cover
      "3" / "page:3"      -> ("page", 3)       PDF page (1-based)
      anything else       -> ("file", Path)    image file
    """
    if spec is None:
        return AUTO, None
    s = str(spec).strip()
    low = s.lower()
    if low in ("", AUTO):
        return AUTO, None
    if low in (NONE, "no", "off", "false"):
        return NONE, None
    page = low[5:] if low.startswith("page:") else low
    if page.isdigit():
        n = int(page)
        if n < 1:
            raise CoverError("Cover page numbers start at 1")
        return "page", n
    return "file", Path(s).expanduser()


def _is_blank(image) -> bool:
    from PIL import ImageStat

    return max(ImageStat.Stat(image.convert("L")).stddev) < BLANK_STDDEV


def render_pdf_page(pdf_path: Path | str, page_number: int, dest: Path, skip_blank: int = 0) -> int:
    """
    Render a PDF page (1-based) as a JPEG cover at e-reader resolution.
    With skip_blank > 0, up to that many following pages are tried when the
    page is blank. Returns the page number actually used.
    """
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        total = len(pdf)
        if not 1 <= page_number <= total:
            raise CoverError(f"Cover page {page_number} is out of range (the PDF has {total} pages)")
        last = min(total, page_number + max(0, skip_blank))
        chosen = None
        for number in range(page_number, last + 1):
            page = pdf[number - 1]
            try:
                width, height = page.get_size()
                scale = min(TARGET_WIDTH / width, MAX_HEIGHT / height)
                image = page.render(scale=scale).to_pil()
            finally:
                page.close()
            if chosen is None:
                chosen = (number, image)  # fall back to the requested page
            if not _is_blank(image):
                chosen = (number, image)
                break
    finally:
        pdf.close()
    number, image = chosen
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(dest, "JPEG", quality=90, optimize=True)
    return number


def import_image(source: Path, dest_dir: Path) -> Path:
    """Copy an image to dest_dir/cover.<ext>, converting to JPEG if EPUB doesn't support its type."""
    if not source.is_file():
        raise CoverError(f"Cover image not found: {source}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = source.suffix.lower()
    if ext in EPUB_COVER_TYPES:
        dest = dest_dir / f"{COVER_STEM}{'.jpg' if ext == '.jpeg' else ext}"
        if source.resolve() != dest.resolve():
            shutil.copyfile(source, dest)
        return dest
    try:
        from PIL import Image

        with Image.open(source) as im:
            dest = dest_dir / f"{COVER_STEM}.jpg"
            im.convert("RGB").save(dest, "JPEG", quality=90, optimize=True)
            return dest
    except Exception as e:  # unknown/corrupt image
        raise CoverError(f"Cannot use {source} as a cover image: {e}") from e


def _remove_old_covers(images_dir: Path, keep: Path | None) -> None:
    for ext in (".jpg", ".png", ".gif"):
        p = images_dir / f"{COVER_STEM}{ext}"
        if p.exists() and (keep is None or p.resolve() != keep.resolve()):
            p.unlink()


def _read_description(markdown_dir: Path) -> dict:
    path = markdown_dir / "description.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _write_cover_entry(markdown_dir: Path, name: str | None) -> None:
    path = markdown_dir / "description.json"
    data = _read_description(markdown_dir)
    data["cover_image"] = name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _user_cover(markdown_dir: Path, data: dict) -> Path | None:
    """A cover_image the user set by hand in description.json (not one we generated)."""
    name = data.get("cover_image")
    if not name or Path(name).stem == COVER_STEM:
        return None
    for candidate in (markdown_dir / name, markdown_dir / "images" / name):
        if candidate.is_file():
            return candidate
    return None


def prepare_cover(markdown_dir: Path | str, pdf_path: Path | str | None, spec: str | None = None) -> Path | None:
    """
    Create the cover image for markdown_dir according to spec (see
    parse_cover_spec) and record it in description.json. Returns the cover
    path, or None when there is no cover.
    """
    markdown_dir = Path(markdown_dir)
    images_dir = markdown_dir / "images"
    kind, value = parse_cover_spec(spec)

    if kind == NONE:
        _remove_old_covers(images_dir, None)
        _write_cover_entry(markdown_dir, None)
        return None

    if kind == "file":
        dest = import_image(Path(value), images_dir)
    else:
        if kind == AUTO:
            custom = _user_cover(markdown_dir, _read_description(markdown_dir))
            if custom is not None:
                return custom  # keep the user's hand-picked cover
        if not pdf_path or not Path(pdf_path).is_file():
            if kind == "page":
                raise CoverError("A cover page was requested but the source PDF is not available")
            return None
        dest = images_dir / f"{COVER_STEM}.jpg"
        page = value if kind == "page" else 1
        used = render_pdf_page(pdf_path, page, dest, skip_blank=AUTO_MAX_PAGES - 1 if kind == AUTO else 0)
        if kind == AUTO and used != 1:
            print(f"Page 1 of the PDF is blank; using page {used} as the cover")

    _remove_old_covers(images_dir, dest)
    _write_cover_entry(markdown_dir, dest.name)
    return dest


def ask_cover_spec(default_hint: str = "first page of the PDF") -> str:
    """Interactive cover choice (asks again on invalid input). Empty answer = automatic."""
    while True:
        answer = input(
            f"\nCover image [Enter = {default_hint}; a page number; a path to an image; 'none']: "
        ).strip().strip("'\"")  # drag-and-dropped paths often come quoted
        try:
            kind, value = parse_cover_spec(answer)
        except CoverError as e:
            print(e)
            continue
        if kind == "file" and not Path(value).is_file():
            print(f"File not found: {value}")
            continue
        return answer or AUTO
