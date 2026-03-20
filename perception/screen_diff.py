"""
ScreenDiff — compares two screenshots pixel by pixel.
Tells the agent exactly what changed after an action.
Makes action verification reliable — no more guessing if something worked.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw
from dataclasses import dataclass
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class DiffResult:
    changed: bool
    change_percent: float       # 0.0 - 100.0
    changed_regions: list[dict] # [{x, y, w, h, description}]
    diff_image: Image.Image | None = None

    def summary(self) -> str:
        if not self.changed:
            return "Screen unchanged"
        regions = "; ".join(
            f"region at ({r['x']},{r['y']}) size {r['w']}x{r['h']}"
            for r in self.changed_regions[:3]
        )
        return f"Screen changed {self.change_percent:.1f}% — {regions}"


class ScreenDiff:

    def __init__(self, threshold: float = 0.5, min_change_percent: float = 0.1):
        """
        threshold: pixel difference threshold (0-255) to count as changed
        min_change_percent: minimum % of screen that must change to report as changed
        """
        self._threshold = threshold
        self._min_change = min_change_percent

    def compare(self, before: Image.Image, after: Image.Image, highlight: bool = False) -> DiffResult:
        """Compare two screenshots and return what changed."""
        try:
            # Resize to same size if needed
            if before.size != after.size:
                after = after.resize(before.size, Image.LANCZOS)

            arr_before = np.array(before.convert("RGB"), dtype=np.float32)
            arr_after  = np.array(after.convert("RGB"),  dtype=np.float32)

            # Pixel difference
            diff = np.abs(arr_before - arr_after).max(axis=2)  # max channel diff
            mask = diff > self._threshold

            change_percent = mask.mean() * 100

            if change_percent < self._min_change:
                return DiffResult(changed=False, change_percent=change_percent, changed_regions=[])

            # Find bounding boxes of changed regions
            regions = self._find_regions(mask, before.size)

            diff_img = None
            if highlight:
                diff_img = self._make_highlight_image(after, mask)

            return DiffResult(
                changed=True,
                change_percent=round(change_percent, 2),
                changed_regions=regions,
                diff_image=diff_img,
            )

        except Exception as e:
            log.warning(f"Screen diff failed: {e}")
            return DiffResult(changed=False, change_percent=0, changed_regions=[])

    def _find_regions(self, mask: np.ndarray, img_size: tuple, max_regions: int = 5) -> list[dict]:
        """Find rectangular bounding boxes of changed areas using simple connected-components."""
        h, w = mask.shape
        # Downsample mask to grid for faster region finding
        grid_size = 20
        regions = []
        for gy in range(0, h, grid_size):
            for gx in range(0, w, grid_size):
                cell = mask[gy:gy+grid_size, gx:gx+grid_size]
                if cell.mean() > 0.3:  # >30% of this grid cell changed
                    regions.append({
                        "x": gx, "y": gy,
                        "w": min(grid_size, w - gx),
                        "h": min(grid_size, h - gy),
                    })
        # Merge nearby regions
        merged = self._merge_regions(regions)
        return merged[:max_regions]

    def _merge_regions(self, regions: list[dict], gap: int = 40) -> list[dict]:
        if not regions:
            return []
        merged = []
        used = set()
        for i, r in enumerate(regions):
            if i in used:
                continue
            x1, y1 = r["x"], r["y"]
            x2, y2 = r["x"] + r["w"], r["y"] + r["h"]
            for j, r2 in enumerate(regions):
                if j in used or j == i:
                    continue
                if (abs(r2["x"] - x2) < gap or abs(r2["x"] - x1) < gap) and \
                   (abs(r2["y"] - y2) < gap or abs(r2["y"] - y1) < gap):
                    x1 = min(x1, r2["x"])
                    y1 = min(y1, r2["y"])
                    x2 = max(x2, r2["x"] + r2["w"])
                    y2 = max(y2, r2["y"] + r2["h"])
                    used.add(j)
            merged.append({"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1})
            used.add(i)
        return merged

    def _make_highlight_image(self, after: Image.Image, mask: np.ndarray) -> Image.Image:
        img = after.copy().convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # Red tint on changed areas
        h, w = mask.shape
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                if mask[y, x]:
                    draw.rectangle([x, y, x+4, y+4], fill=(255, 0, 0, 80))
        return Image.alpha_composite(img, overlay).convert("RGB")
