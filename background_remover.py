"""Local background removal using rembg (lazy-loaded to avoid startup crashes)."""

from io import BytesIO
from pathlib import Path
from PIL import Image

from image_pipeline import process_pipeline


class BackgroundRemover:
    def __init__(self, model_name="u2net"):
        self.model_name = model_name
        self._session = None
        self._remove_fn = None

    def _ensure_loaded(self):
        """Lazy-load rembg on first use to avoid import-time sys.exit crashes."""
        if self._remove_fn is not None:
            return

        try:
            from rembg import remove, new_session
            self._remove_fn = remove
            self._new_session = new_session
        except SystemExit:
            raise RuntimeError(
                "rembg failed to load (onnxruntime DLL error).\n"
                "Try reinstalling:\n"
                "  py -m pip install --force-reinstall onnxruntime rembg[cpu]"
            )

    def _get_session(self):
        """Lazy-load the ONNX session (downloads model on first use)."""
        self._ensure_loaded()
        if self._session is None:
            self._session = self._new_session(self.model_name)
        return self._session

    def remove_background(self, image_data: bytes) -> bytes:
        """Remove background from image bytes, return raw transparent PNG bytes."""
        self._ensure_loaded()
        return self._remove_fn(image_data, session=self._get_session())

    def process_and_save(self, image_data: bytes, output_path: Path) -> Path:
        """Remove background, run post-processing pipeline, and save.

        Output format is WebP (.webp) regardless of the extension passed in —
        the caller should use a .webp extension.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        raw_png = self.remove_background(image_data)
        final = process_pipeline(raw_png)
        output_path.write_bytes(final)
        return output_path
