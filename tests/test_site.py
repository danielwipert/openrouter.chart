"""The website: built from READY weeks only, every link points at a real file."""

import re
import shutil
from pathlib import Path

import site_build

REAL_WEEK = Path(__file__).resolve().parent.parent / "output" / "2026-W40"


def make_output(tmp_path):
    out = tmp_path / "output"
    shutil.copytree(REAL_WEEK, out / "2026-W40")
    # A newer week that is NOT READY must not be published
    shutil.copytree(REAL_WEEK, out / "2026-W41")
    report = out / "2026-W41" / "run_report.md"
    report.write_text(report.read_text().replace("# READY TO POST", "# NOT READY TO POST", 1))
    return out


def test_only_ready_weeks_are_published(tmp_path):
    build_dir, weeks = site_build.build(make_output(tmp_path), tmp_path / "_site")
    assert weeks == ["2026-W40"]
    assert not (build_dir / "weeks" / "2026-W41").exists()


def test_every_link_and_image_exists(tmp_path):
    build_dir, _ = site_build.build(make_output(tmp_path), tmp_path / "_site")
    for page in [build_dir / "index.html", build_dir / "weeks" / "2026-W40" / "index.html"]:
        text = page.read_text()
        targets = re.findall(r'(?:src|href|data-full)="([^"#:]+)"', text)
        assert targets
        for target in targets:
            path = (page.parent / target)
            path = path / "index.html" if target.endswith("/") or target in ("./",) else path
            assert path.resolve().exists(), f"{page.name}: missing {target}"


def test_page_shows_every_chart_and_the_stats(tmp_path):
    build_dir, _ = site_build.build(make_output(tmp_path), tmp_path / "_site")
    text = (build_dir / "index.html").read_text()
    charts = {p.name.rsplit("_", 1)[0] for p in (REAL_WEEK / "charts").glob("*_square.png")}
    for name in charts:
        assert f'id="{name}"' in text, name
    assert text.count('class="stat"') == 4
    assert "Week 40, 2026 (latest)" in text
    assert "CC BY 4.0" in text


def test_stat_change_vs_last_week():
    weekly = site_build.read_weekly(REAL_WEEK)
    name, share, change = site_build.stat(weekly, "company", "top_named")
    assert name == "DeepSeek" and 0 < share < 1 and change is not None
