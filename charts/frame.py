"""The shared frame every chart uses: title, subtitle, units label, chart area
and footer.

All positions are worked out in pixels, top to bottom, so the layout is the same
on any computer. Sizes, colors and text come from style.yaml.
"""

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to files only; no screen needed
matplotlib.rcParams["text.parse_math"] = False  # "$0.50" is money, not a formula
import matplotlib.pyplot as plt  # noqa: E402
import yaml  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LINE_HEIGHT = 1.18
FONT_WEIGHTS = ("regular", "medium", "semibold", "bold")


def load_style(path=ROOT / "style.yaml"):
    style = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    style["colors"] = style["themes"][style["theme"]]
    return style


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
        self.sizes = style["text_sizes"]
        self.fig = plt.figure(figsize=(self.width / 100, self.height / 100), dpi=100)
        self.fig.patch.set_facecolor(self.colors["background"])
        self.renderer = self.fig.canvas.get_renderer()
        folder = ROOT / style["fonts"]["folder"]
        self.fonts = {w: FontProperties(fname=folder / style["fonts"][w]) for w in FONT_WEIGHTS}
        self.footer_top = self.margin["bottom"]
        self.cursor = self.height - self.margin["top"]  # pixels from the bottom

    # --- helpers ---------------------------------------------------------------

    def font(self, weight, px):
        prop = self.fonts[weight].copy()
        prop.set_size(pt(px))
        return prop

    def text(self, x_px, y_px, text, weight, px, color, **kwargs):
        kwargs.setdefault("linespacing", LINE_HEIGHT)
        return self.fig.text(x_px / self.width, y_px / self.height, text,
                             fontproperties=self.font(weight, px), color=color, **kwargs)

    def width_of(self, artist):
        return artist.get_window_extent(self.renderer).width

    # --- top block -------------------------------------------------------------

    def title(self, text):
        """Bold title; a long one gets a smaller size so it fits on two lines."""
        size, wrap = self.sizes["title"], self.style["layout"]["title_wrap"]
        lines = textwrap.wrap(text, wrap)
        while len(lines) > 2 and size > 34:
            size -= 4
            lines = textwrap.wrap(text, int(wrap * self.sizes["title"] / size))
        self.text(self.margin["left"], self.cursor, "\n".join(lines), "bold", size,
                  self.colors["text"], va="top")
        self.cursor -= len(lines) * size * LINE_HEIGHT + 10

    def subtitle(self, text):
        size = self.sizes["subtitle"]
        wrap = int((self.width - self.margin["left"] - self.margin["right"]) / (size * 0.47))
        lines = textwrap.wrap(text, wrap)
        self.text(self.margin["left"], self.cursor, "\n".join(lines), "regular", size,
                  self.colors["text"], va="top")
        self.cursor -= len(lines) * size * LINE_HEIGHT + self.style["layout"]["gap_after_subtitle"]

    def units(self, text):
        """Small grey unit label above the chart's top-right corner."""
        size = self.sizes["units"]
        self.text(self.width - self.margin["right"], self.cursor, text, "regular", size,
                  self.colors["text_muted"], va="top", ha="right")
        self.cursor -= size * LINE_HEIGHT + 12

    # --- chart and footer --------------------------------------------------------

    def chart_area(self, left_px=0, right_px=0, below_px=0):
        """Axes for the chart under the subtitle. Call footer() first: the chart
        shrinks if needed so its axis labels (below_px tall) never reach the footer."""
        room = self.cursor - self.footer_top - below_px
        height = min(self.style["layout"]["chart_height"] * self.height, room)
        if self.height > self.width:  # portrait: use the extra height
            height = room
        left = self.margin["left"] + left_px
        width = self.width - left - self.margin["right"] - right_px
        ax = self.fig.add_axes([left / self.width, (self.cursor - height) / self.height,
                                width / self.width, height / self.height])
        ax.patch.set_alpha(0)
        for side in ax.spines.values():
            side.set_visible(False)
        self.cursor -= height
        return ax

    def _rings(self, x, y, r):
        """The Chorus concentric-ring mark (blue, magenta, yellow, center dot) at x, y."""
        ax = self.fig.add_axes([(x - r) / self.width, (y - r) / self.height,
                                2 * r / self.width, 2 * r / self.height])
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.set_aspect("equal")
        ax.axis("off")
        for radius, color in zip([1, 0.72, 0.44, 0.18],
                                 self.colors["stripe"] + [self.colors["text"]]):
            ax.add_patch(Circle((0, 0), radius, facecolor=color,
                                edgecolor=self.colors["background"], linewidth=1.5))

    def footer(self, source_text):
        bottom = self.margin["bottom"]
        size = self.sizes["footer"]
        lines = textwrap.wrap(source_text, 78)
        self.text(self.margin["left"], bottom, "\n".join(lines), "regular", size,
                  self.colors["text_muted"], va="bottom")
        self.footer_top = bottom + len(lines) * size * LINE_HEIGHT + 30
        bsize = self.sizes["branding"]
        right = self.width - self.margin["right"]
        name = self.text(right, bottom + bsize * 1.25, self.style["text"]["branding_name"],
                         "semibold", bsize, self.colors["text"], va="bottom", ha="right")
        company = self.text(right, bottom, self.style["text"]["branding_company"], "regular",
                            bsize, self.colors["text_muted"], va="bottom", ha="right")
        block_w = max(self.width_of(name), self.width_of(company))
        r = bsize * 1.15
        self._rings(right - block_w - 14 - r, bottom + bsize * 1.1, r)

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        # No timestamps or version in the file, so the same data gives the same file.
        self.fig.savefig(path, dpi=100, facecolor=self.colors["background"],
                         metadata={"Software": None})
        plt.close(self.fig)
        return path
