"""The shared frame every chart uses: brand stripe, kicker, big number + headline,
subtitle, chart area and footer.

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
from matplotlib.patches import Circle, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LINE_HEIGHT = 1.15
FONT_WEIGHTS = ("regular", "semibold", "bold", "display", "hero")


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
        self._stripe()
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

    def _rect(self, x, y, w, h, color, zorder=1):
        self.fig.add_artist(Rectangle((x / self.width, y / self.height), w / self.width,
                                      h / self.height, transform=self.fig.transFigure,
                                      color=color, linewidth=0, zorder=zorder))

    def _stripe(self):
        """The Chorus color stripe across the top edge."""
        colors = self.colors["stripe"]
        h = self.style["layout"]["stripe_height"]
        part = self.width / len(colors)
        for i, color in enumerate(colors):
            self._rect(i * part, self.height - h, part + 1, h, color)

    # --- top block -------------------------------------------------------------

    def kicker(self, text):
        """Small all-caps label above the headline: in a pill if the theme gives a
        fill color, otherwise plain text after a short accent rule."""
        size = self.sizes["kicker"]
        left, mid = self.margin["left"], self.cursor - size * 0.55
        if self.colors.get("kicker_fill"):
            self.text(left + 10, mid, text, "bold", size, self.colors["kicker_text"],
                      va="center", bbox={"boxstyle": "round,pad=0.45,rounding_size=0.9",
                                         "facecolor": self.colors["kicker_fill"],
                                         "edgecolor": "none"})
        else:
            self._rect(left, mid - 2, 36, 4, self.colors["accent"])
            self.text(left + 50, mid, text, "bold", size, self.colors["kicker_text"],
                      va="center")
        self.cursor -= size * LINE_HEIGHT + 22

    def hero(self, number, headline):
        """A huge number with the headline set beside it."""
        size = self.sizes["hero"]
        big = self.text(self.margin["left"] - 8, self.cursor + size * 0.12, number, "hero",
                        size, self.colors["hero"], va="top", linespacing=1.0)
        x = self.margin["left"] + self.width_of(big) + 20
        # Wrap the headline to the space left beside the number; shrink it if that
        # would take more than three lines.
        room = self.width - self.margin["right"] - x
        hsize = self.sizes["headline"]
        lines = textwrap.wrap(headline, max(8, int(room / (hsize * 0.48))))
        while len(lines) > 3 and hsize > 28:
            hsize -= 4
            lines = textwrap.wrap(headline, max(8, int(room / (hsize * 0.48))))
        block = len(lines) * hsize * LINE_HEIGHT
        cap_mid = self.cursor - size * 0.40  # middle of the number's digits
        self.text(x, cap_mid + block / 2, "\n".join(lines), "display", hsize,
                  self.colors["header_text"], va="top")
        self.cursor -= size * 0.95

    def subtitle(self, text):
        """Subtitle, then the color block behind the whole top section (if the theme has one)."""
        size = self.sizes["subtitle"]
        self.cursor -= 6
        self.text(self.margin["left"], self.cursor, text, "regular", size,
                  self.colors["header_muted"], va="top")
        self.cursor -= size * LINE_HEIGHT
        if self.colors.get("header_panel"):
            self.cursor -= 30
            self._rect(0, self.cursor, self.width, self.height - self.cursor,
                       self.colors["header_panel"], zorder=-1)
        self.cursor -= self.style["layout"]["gap_after_subtitle"]

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
        ax.set_facecolor(self.colors["background"])
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
        lines = textwrap.wrap(source_text, 74)
        self.text(self.margin["left"], bottom, "\n".join(lines), "regular", size,
                  self.colors["text_muted"], va="bottom")
        self.footer_top = bottom + len(lines) * size * LINE_HEIGHT + 28
        # Rule above the footer
        self._rect(self.margin["left"], self.footer_top - 14,
                   self.width - self.margin["left"] - self.margin["right"], 1,
                   self.colors["grid"])
        # Branding: rings + name / company, right-aligned
        bsize = self.sizes["branding"]
        right = self.width - self.margin["right"]
        name = self.text(right, bottom + bsize * 1.25, self.style["text"]["branding_name"],
                         "bold", bsize, self.colors["text"], va="bottom", ha="right")
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
