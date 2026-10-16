"""Tests for EPUB cover selection (need Pillow + pypdfium2, installed with marker-pdf)."""
import json
import tempfile
import unittest
from pathlib import Path

from modules import cover

try:
    import pypdfium2  # noqa: F401
    from PIL import Image

    HAVE_DEPS = True
except ImportError:  # pragma: no cover
    HAVE_DEPS = False


def make_pdf(path: Path, pages):
    """pages: list of colors; "white_with_text" draws a black box on white."""
    from PIL import ImageDraw

    images = []
    for color in pages:
        if color == "white_with_text":
            im = Image.new("RGB", (300, 450), "white")
            ImageDraw.Draw(im).rectangle((40, 60, 260, 120), fill="black")
        else:
            im = Image.new("RGB", (300, 450), color)
        images.append(im)
    images[0].save(path, "PDF", save_all=True, append_images=images[1:])


class ParseSpecTests(unittest.TestCase):
    def test_specs(self):
        self.assertEqual(cover.parse_cover_spec(None), ("auto", None))
        self.assertEqual(cover.parse_cover_spec(""), ("auto", None))
        self.assertEqual(cover.parse_cover_spec("NONE"), ("none", None))
        self.assertEqual(cover.parse_cover_spec("3"), ("page", 3))
        self.assertEqual(cover.parse_cover_spec("page:12"), ("page", 12))
        self.assertEqual(cover.parse_cover_spec("portada.png"), ("file", Path("portada.png")))
        with self.assertRaises(cover.CoverError):
            cover.parse_cover_spec("0")


@unittest.skipUnless(HAVE_DEPS, "Pillow/pypdfium2 not installed")
class PrepareCoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.md_dir = self.root / "book"
        self.md_dir.mkdir()
        (self.md_dir / "description.json").write_text(json.dumps({"metadata": {"dc:title": "T"}}))
        self.pdf = self.root / "book.pdf"
        make_pdf(self.pdf, ["white", "white_with_text", (200, 30, 30), (30, 30, 200)])

    def tearDown(self):
        self.tmp.cleanup()

    def description(self):
        return json.loads((self.md_dir / "description.json").read_text())

    def test_auto_skips_blank_first_page(self):
        path = cover.prepare_cover(self.md_dir, self.pdf)
        self.assertEqual(path, self.md_dir / "images" / "cover.jpg")
        with Image.open(path) as im:
            self.assertEqual(im.format, "JPEG")
            self.assertEqual(im.width, cover.TARGET_WIDTH)
            self.assertLessEqual(im.height, cover.MAX_HEIGHT)
            # Page 2 (white with a black box) was used, not blank page 1.
            self.assertLess(min(im.convert("L").getdata()), 50)
        self.assertEqual(self.description()["cover_image"], "cover.jpg")
        self.assertEqual(self.description()["metadata"]["dc:title"], "T")  # preserved

    def test_explicit_page(self):
        path = cover.prepare_cover(self.md_dir, self.pdf, "3")
        with Image.open(path) as im:
            r, g, b = im.convert("RGB").getpixel((10, 10))
            self.assertGreater(r, 150)
            self.assertLess(b, 80)

    def test_explicit_blank_page_is_respected(self):
        path = cover.prepare_cover(self.md_dir, self.pdf, "1")
        with Image.open(path) as im:
            self.assertGreater(min(im.convert("L").getdata()), 240)

    def test_page_out_of_range(self):
        with self.assertRaises(cover.CoverError):
            cover.prepare_cover(self.md_dir, self.pdf, "9")

    def test_image_file_png_and_webp_conversion(self):
        png = self.root / "portada.png"
        Image.new("RGB", (100, 150), "green").save(png)
        path = cover.prepare_cover(self.md_dir, self.pdf, str(png))
        self.assertEqual(path.name, "cover.png")
        # Switching to another type removes the previous cover file.
        webp = self.root / "portada.webp"
        Image.new("RGB", (100, 150), "blue").save(webp, "WEBP")
        path = cover.prepare_cover(self.md_dir, self.pdf, str(webp))
        self.assertEqual(path.name, "cover.jpg")
        self.assertFalse((self.md_dir / "images" / "cover.png").exists())
        self.assertEqual(self.description()["cover_image"], "cover.jpg")

    def test_missing_file(self):
        with self.assertRaises(cover.CoverError):
            cover.prepare_cover(self.md_dir, self.pdf, str(self.root / "nope.jpg"))

    def test_none_removes_cover(self):
        cover.prepare_cover(self.md_dir, self.pdf)
        self.assertIsNone(cover.prepare_cover(self.md_dir, self.pdf, "none"))
        self.assertFalse((self.md_dir / "images" / "cover.jpg").exists())
        self.assertIsNone(self.description()["cover_image"])

    def test_auto_keeps_hand_picked_cover(self):
        images = self.md_dir / "images"
        images.mkdir()
        Image.new("RGB", (100, 150), "green").save(images / "mi_portada.png")
        data = self.description()
        data["cover_image"] = "mi_portada.png"
        (self.md_dir / "description.json").write_text(json.dumps(data))
        self.assertEqual(cover.prepare_cover(self.md_dir, self.pdf), images / "mi_portada.png")
        self.assertFalse((images / "cover.jpg").exists())

    def test_auto_without_pdf_gives_no_cover(self):
        self.assertIsNone(cover.prepare_cover(self.md_dir, None))
        with self.assertRaises(cover.CoverError):
            cover.prepare_cover(self.md_dir, None, "2")


if __name__ == "__main__":
    unittest.main()
