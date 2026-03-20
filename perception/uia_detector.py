"""
Windows UI Automation element detector.
Finds exact pixel positions of buttons, textboxes, menus, links.
No guessing — uses the Windows accessibility API directly.

Falls back gracefully if uiautomation is not installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class UIElement:
    name: str
    control_type: str   # Button, Edit, Text, MenuItem, etc.
    x: int              # center x
    y: int              # center y
    left: int
    top: int
    right: int
    bottom: int
    enabled: bool = True
    value: str = ""

    def click_point(self) -> tuple[int, int]:
        return (self.x, self.y)


class UIADetector:
    """
    Detects UI elements using Windows UI Automation (uiautomation library).
    Returns exact pixel positions — no vision model needed for clicking.
    """

    def __init__(self):
        self._available = False
        try:
            import uiautomation as auto
            self._auto = auto
            self._available = True
            log.info("UIA detector ready (precise element detection enabled)")
        except ImportError:
            log.warning("uiautomation not installed — install with: pip install uiautomation")

    @property
    def available(self) -> bool:
        return self._available

    def get_all_elements(self, depth: int = 4) -> list[UIElement]:
        """Get all interactive elements in the current foreground window."""
        if not self._available:
            return []
        try:
            auto = self._auto
            root = auto.GetForegroundControl()
            elements = []
            self._walk(root, elements, depth)
            return elements
        except Exception as e:
            log.debug(f"UIA scan error: {e}")
            return []

    def find_element(self, name: str = "", control_type: str = "") -> UIElement | None:
        """Find a specific element by name and/or type."""
        if not self._available:
            return None
        try:
            auto = self._auto
            kwargs = {}
            if name:
                kwargs["Name"] = name
            if control_type:
                kwargs["ControlType"] = getattr(auto.ControlType, control_type, None)

            ctrl = auto.Control(searchDepth=8, **kwargs)
            if ctrl.Exists(0.5):
                return self._to_element(ctrl)
        except Exception as e:
            log.debug(f"UIA find error: {e}")
        return None

    def find_by_text(self, text: str) -> list[UIElement]:
        """Find all elements whose name contains the given text."""
        elements = self.get_all_elements(depth=6)
        text_lower = text.lower()
        return [e for e in elements if text_lower in e.name.lower()]

    def get_element_map(self) -> dict:
        """
        Returns structured map of foreground window UI.
        Format: {type: [{"name": ..., "x": ..., "y": ...}]}
        """
        elements = self.get_all_elements()
        result: dict[str, list] = {}
        for el in elements:
            ct = el.control_type
            if ct not in result:
                result[ct] = []
            result[ct].append({
                "name": el.name,
                "x": el.x,
                "y": el.y,
                "value": el.value,
            })
        return result

    def _walk(self, ctrl, elements: list, depth: int) -> None:
        if depth <= 0:
            return
        try:
            el = self._to_element(ctrl)
            if el and el.name:
                elements.append(el)
            for child in ctrl.GetChildren():
                self._walk(child, elements, depth - 1)
        except Exception:
            pass

    def _to_element(self, ctrl) -> UIElement | None:
        try:
            rect = ctrl.BoundingRectangle
            if rect.width() <= 0 or rect.height() <= 0:
                return None
            cx = rect.left + rect.width() // 2
            cy = rect.top + rect.height() // 2
            return UIElement(
                name=ctrl.Name or "",
                control_type=ctrl.ControlTypeName or "Unknown",
                x=cx, y=cy,
                left=rect.left, top=rect.top,
                right=rect.right, bottom=rect.bottom,
                enabled=ctrl.IsEnabled,
                value=getattr(ctrl, "CurrentValue", "") or "",
            )
        except Exception:
            return None
