"""The shared frame every chart uses: canvas, headline, subtitle, chart area, footer.

All positions are worked out in pixels, top to bottom, so the layout is the same
on any computer. Sizes, colors and text come from style.yaml.
"""

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to files only; no screen needed
import matplotlib.pyplot as plt  # noqa: E402
import yaml  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LINE_HEIGHT = 1.2


def load_style(path=ROOT / "style.yaml"):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def pt(px):
    """Pixels to font points at 100 dpi."""
    return px * 72 / 100


class Frame:
    def __init__(self, style, size):
        self.style = style
        self.width = style["sizes"][size]["width"]
        self.height = style["sizes"][size]["height"]
        self.margin = style["margins"]
        self.colors = style["colors"]
        self.fig = plt.figure(figsize=(self.width / 100, self.height / 100), dpi=100)
        self.fig.patch.set_facecolor(self.colors["background"])
        self.cursor = self.height - self.margin["top"]  # pixels from the bottom
        self.footer_top = self.margin["bottom"]
        folder = ROOT / style["fonts"]["folder"]
        self.fonts = {w: FontProperties(fname=folder / style["fonts"][w])
                      for w in ("regular", "semibold", "bold")}

    def font(self, weight, px):
        prop = self.fonts[weight].copy()
        prop.set_size(pt(px))
        return prop

    def text(self, x_px, y_px, text, weight, px, color, **kwargs):
        return self.fig.text(x_px / self.width, y_px / self.height, text,
                             fontproperties=self.font(weight, px), color=color, **kwargs)

    def _block(self, text, weight, px, color, wrap):
        lines = textwrap.wrap(text, wrap) if wrap else [text]
        self.text(self.margin["left"], self.cursor, "\n".join(lines), weight, px, color,
                  va="top", linespacing=LINE_HEIGHT)
        self.cursor -= len(lines) * px * LINE_HEIGHT

    def headline(self, text):
        size = self.style["text_sizes"]["headline"]
        self._block(text, "bold", size, self.colors["text"], self.style["layout"]["headline_wrap"])
        self.cursor -= 12

    def subtitle(self, text):
        size = self.style["text_sizes"]["subtitle"]
        wrap = int((self.width - self.margin["left"] - self.margin["right"]) / (size * 0.52))
        self._block(text, "regular", size, self.colors["text_muted"], wrap)
        self.cursor -= self.style["layout"]["gap_after_subtitle"]

    def chart_area(self, left_px=0, right_px=0, below_px=0):
        """Axes for the chart: about 65% of the image height, under the subtitle.

        Call footer() first: the chart shrinks if needed so its axis labels
        (below_px tall) never run into the footer.
        """
        room = self.cursor - self.footer_top - below_px
        height = min(self.style["layout"]["chart_height"] * self.height, room)
        left = self.margin["left"] + left_px
        width = self.width - left - self.margin["right"] - right_px
        ax = self.fig.add_axes([left / self.width, (self.cursor - height) / self.height,
                                width / self.width, height / self.height])
        ax.set_facecolor(self.colors["background"])
        for side in ax.spines.values():
            side.set_visible(False)  # no border
        self.cursor -= height
        return ax

    def footer(self, source_text):
        size = self.style["text_sizes"]["footer"]
        bottom = self.margin["bottom"]
        lines = textwrap.wrap(source_text, 70)
        self.footer_top = bottom + len(lines) * size * LINE_HEIGHT + 24
        self.text(self.margin["left"], bottom, "\n".join(lines), "regular", size,
                  self.colors["text_muted"], va="bottom", linespacing=LINE_HEIGHT)
        self.text(self.width - self.margin["right"], bottom, self.style["text"]["branding"],
                  "semibold", size, self.colors["text"], va="bottom", ha="right")

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        # No timestamps or version in the file, so the same data gives the same file.
        self.fig.savefig(path, dpi=100, facecolor=self.colors["background"],
                         metadata={"Software": None})
        plt.close(self.fig)
        return path
