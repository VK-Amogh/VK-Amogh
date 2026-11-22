#!/usr/bin/env python3
"""
Daily zero-SVG telemetry builder for VK-Amogh's GitHub profile.
Generates:
  - assets/progress.gif  : Silky smooth animated progress bars (Year, B.Tech, GitHub, Flagship builds)
  - assets/activity.gif  : Animated 52-week GitHub contribution matrix + live stats + language ribbon
  - Updates the live Unicode progress ledger block inside README.md
Requires only Pillow (pip install pillow) + bundled fonts in fonts/.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

USERNAME = "VK-Amogh"
ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
FONTS_DIR = ROOT / "fonts"
README_PATH = ROOT / "README.md"

PAPER = (244, 237, 227)
PAPER_DEEP = (236, 227, 213)
INK = (26, 20, 18)
INK_SOFT = (61, 47, 40)
INK_MUTED = (143, 62, 38)
INK_TEAL = (30, 90, 82)
INK_NAVY = (42, 63, 102)
LINE = (220, 211, 198)
LINE_STRONG = (196, 184, 168)

CORAL = (217, 93, 57)
CORAL_SOFT = (240, 146, 106)
MARIGOLD = (233, 191, 82)
SKY = (157, 189, 216)
ROSE = (237, 179, 195)
SAGE = (186, 207, 174)
SEAGLASS = (169, 204, 196)
LILAC = (195, 187, 227)
PEACH = (241, 180, 142)

LANG_COLORS = {
    "Python": INK_NAVY,
    "Dart": INK_TEAL,
    "HTML": CORAL_SOFT,
    "TypeScript": SKY,
    "CSS": LILAC,
    "ShaderLab": SAGE,
    "JavaScript": MARIGOLD,
    "C++": ROSE,
    "Jupyter Notebook": PEACH,
}

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        name
        stargazerCount
        forkCount
        languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def load_font(name: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONTS_DIR / name), size)
    if weight is not None:
        try:
            axes = font.get_variation_axes()
            vals = []
            for ax in axes:
                if ax["name"] == b"Weight":
                    vals.append(max(ax["minimum"], min(ax["maximum"], weight)))
                else:
                    vals.append(ax["default"])
            font.set_variation_by_axes(vals)
        except Exception:
            pass
    return font


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    tracking: float = 1.5,
    anchor: str = "lt",
) -> None:
    x, y = xy
    if anchor == "rt":
        total = sum(draw.textlength(c, font=font) for c in text) + tracking * max(0, len(text) - 1)
        x -= total
    elif anchor == "mt":
        total = sum(draw.textlength(c, font=font) for c in text) + tracking * max(0, len(text) - 1)
        x -= total / 2
    cx = x
    for c in text:
        draw.text((cx, y), c, font=font, fill=fill)
        cx += draw.textlength(c, font=font) + tracking


def fetch_github_data() -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    fallback_weeks = [[0] * 7 for _ in range(52)]
    fallback = {
        "total_contributions": 132,
        "commits": 115,
        "public_repos": 18,
        "stars": 3,
        "forks": 6,
        "followers": 2,
        "active_days": 24,
        "peak_day": 38,
        "weeks": fallback_weeks,
        "languages": [
            ("Python", 51.0),
            ("Dart", 11.4),
            ("HTML", 9.6),
            ("TypeScript", 8.5),
            ("CSS", 5.5),
            ("ShaderLab", 5.5),
        ],
    }

    if not token:
        return fallback

    payload = json.dumps({"query": GRAPHQL_QUERY, "variables": {"login": USERNAME}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "VK-Amogh-Telemetry-Builder",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"GraphQL failed ({exc}); using fallback.")
        return fallback

    user = (raw.get("data") or {}).get("user")
    if not user:
        return fallback

    repos = user["repositories"]
    nodes = repos.get("nodes") or []
    contrib = user["contributionsCollection"]
    cal = contrib["contributionCalendar"]

    weights: dict[str, float] = {}
    for repo in nodes:
        edges = (repo.get("languages") or {}).get("edges") or []
        rtot = sum(e.get("size", 0) for e in edges)
        if rtot <= 0:
            continue
        for e in edges:
            ln = e["node"]["name"]
            weights[ln] = weights.get(ln, 0.0) + (e["size"] / rtot)

    tot_w = sum(weights.values()) or 1.0
    sorted_langs = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)
    top_langs = [(k, round((v / tot_w) * 100, 1)) for k, v in sorted_langs[:6]] or fallback["languages"]

    raw_weeks = cal.get("weeks") or []
    weeks = [[d.get("contributionCount", 0) for d in (w.get("contributionDays") or [])] for w in raw_weeks[-52:]]
    days = [c for w in weeks for c in w]

    return {
        "total_contributions": cal.get("totalContributions", fallback["total_contributions"]),
        "commits": contrib.get("totalCommitContributions", fallback["commits"]),
        "public_repos": repos.get("totalCount", fallback["public_repos"]),
        "stars": sum(n.get("stargazerCount", 0) for n in nodes),
        "forks": sum(n.get("forkCount", 0) for n in nodes),
        "followers": (user.get("followers") or {}).get("totalCount", fallback["followers"]),
        "active_days": sum(1 for c in days if c > 0),
        "peak_day": max(days, default=fallback["peak_day"]),
        "weeks": weeks,
        "languages": top_langs,
    }


def compute_chronology(now: dt.datetime) -> dict:
    year = now.year
    y0 = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc)
    y1 = dt.datetime(year + 1, 1, 1, tzinfo=dt.timezone.utc)
    year_pct = round(max(0.0, min(100.0, ((now - y0).total_seconds() / (y1 - y0).total_seconds()) * 100.0)), 1)
    day_of_year = (now - y0).days + 1
    days_in_year = (y1 - y0).days

    d0 = dt.datetime(2024, 8, 1, tzinfo=dt.timezone.utc)
    d1 = dt.datetime(2028, 5, 31, tzinfo=dt.timezone.utc)
    deg_pct = round(max(0.0, min(100.0, ((now - d0).total_seconds() / (d1 - d0).total_seconds()) * 100.0)), 1)
    sem = min(8, max(1, int(math.ceil((deg_pct / 100.0) * 8))))

    return {
        "year": year,
        "year_pct": year_pct,
        "day_of_year": day_of_year,
        "days_in_year": days_in_year,
        "deg_pct": deg_pct,
        "sem": sem,
        "date_str": now.strftime("%d %b %Y").upper(),
        "iso_date": now.strftime("%Y-%m-%d UTC"),
    }


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def draw_ruler_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    pct: float,
    color: tuple[int, int, int],
    hatch_offset: int,
    is_dark: bool,
) -> None:
    r = h // 2
    draw.rounded_rectangle((x, y, x + w, y + h), radius=r, fill=PAPER_DEEP, outline=LINE_STRONG, width=1)

    for frac in (0.25, 0.50, 0.75):
        tx = int(x + w * frac)
        draw.line((tx, y + 2, tx, y + h - 2), fill=LINE_STRONG, width=1)

    fill_w = max(h, int(w * max(0.02, min(1.0, pct / 100.0))))
    if pct > 0.3:
        draw.rounded_rectangle((x, y, x + fill_w, y + h), radius=r, fill=color)
        # Subtle pre-blended architectural diagonal hatch inside the filled portion
        target_col = PAPER if is_dark else INK
        blend = 0.24 if is_dark else 0.16
        hatch_col = tuple(int(color[i] * (1 - blend) + target_col[i] * blend) for i in range(3))
        step = 12
        for hx in range(x - h + (hatch_offset % step), x + fill_w, step):
            x1 = max(x + 3, hx)
            x2 = min(x + fill_w - 3, hx + h - 4)
            if x2 > x1:
                y1 = y + h - 2 - (x1 - hx)
                y2 = y + h - 2 - (x2 - hx)
                draw.line((x1, max(y + 2, y1), x2, max(y + 2, y2)), fill=hatch_col, width=1)
        draw.rounded_rectangle((x, y, x + fill_w, y + h), radius=r, outline=(90, 78, 68), width=1)

        # Crisp Vernier needle at exact tip
        tip_x = x + fill_w
        draw.line((tip_x, y - 4, tip_x, y + h + 4), fill=INK, width=2)
        draw.ellipse((tip_x - 3, y - 7, tip_x + 3, y - 1), fill=CORAL)


def generate_progress_gif(metrics: dict, chrono: dict) -> None:
    """Silky smooth animated progress bars GIF — zero SVG, real EB Garamond & Instrument Sans."""
    W, H = 1040, 492
    f_serif = load_font("EBGaramond-Regular.ttf", 38, 400)
    f_serif_i = load_font("EBGaramond-Italic.ttf", 38, 400)
    f_pct = load_font("EBGaramond-Italic.ttf", 19, 500)
    f_title = load_font("InstrumentSans.ttf", 14, 600)
    f_sub = load_font("InstrumentSans.ttf", 11, 400)
    f_label = load_font("InstrumentSans.ttf", 10, 600)
    f_mono = load_font("JetBrainsMono.ttf", 10, 600)

    contribs = metrics["total_contributions"]
    if contribs < 500:
        c_goal = max(200, int(math.ceil((contribs + 25) / 50.0) * 50))
        c_title = f"Public GitHub Contributions ({contribs:,} / {c_goal:,})"
        c_sub = f"{metrics['commits']:,} public commits · 1,073+ total incl. private"
    else:
        c_goal = max(1200, int(math.ceil((contribs + 100) / 500.0) * 500))
        c_title = f"Annual GitHub Contributions ({contribs:,} / {c_goal:,})"
        c_sub = f"{metrics['commits']:,} commits · {metrics['active_days']} active days"
    c_pct = round(min(100.0, (contribs / c_goal) * 100.0), 1)

    pub_repos = metrics["public_repos"]
    r_goal = max(25, int(math.ceil((pub_repos + 2) / 5.0) * 5))
    r_pct = round(min(100.0, (pub_repos / r_goal) * 100.0), 1)

    left_bars = [
        (f"Year Progress ({chrono['year']})", f"Day {chrono['day_of_year']} of {chrono['days_in_year']}", chrono["year_pct"], INK_NAVY, True),
        ("B.Tech ECE · MIT Bengaluru (2024–2028)", f"Semester {chrono['sem']} of 8 · AICTE National Merit Scholar", chrono["deg_pct"], INK_MUTED, True),
        (c_title, c_sub, c_pct, INK_TEAL, True),
        (f"Open-Source Repositories ({pub_repos} / {r_goal})", "26+ total repositories incl. private ventures", r_pct, CORAL, True),
    ]

    right_bars = [
        ("TRACE · Neuro-Symbolic Security", "npm & PyPI · 0.261s audit · 250+ passing tests", 95.0, SEAGLASS, False),
        ("Your Space · Android Super-App", "14 Dart packages · 151 tests · Play Pre-Release", 92.0, LILAC, False),
        ("ICARUS · 1U CubeSat ADCS & EPS", "UNOOSA / JAXA KiboCUBE · 10/10 physics tests", 88.0, SKY, False),
        ("HAWKEYE · IAF Runway FOD Fusion", "76–81 GHz radar + 8 modalities · Aero India 2027", 82.0, CORAL_SOFT, False),
        ("Specular · EvenEi AI Glasses", "USD 1,000 seed · Google / Antler Immersion", 68.0, MARIGOLD, False),
    ]

    # 22 ease-out fill frames (55ms each) + 28 calm hold/hatch-glide frames (130ms each) = 50 crisp frames!
    fill_frames = 22
    hold_frames = 28
    total_frames = fill_frames + hold_frames
    frames: list[Image.Image] = []
    durations: list[int] = []

    for fi in range(total_frames):
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)

        # Header
        draw_tracked(d, (40, 26), "LIVE TELEMETRY · AUTO-SYNCED DAILY", f_label, INK_MUTED, tracking=2.0)
        d.text((38, 44), "Progress ", font=f_serif, fill=INK)
        w0 = d.textlength("Progress ", font=f_serif)
        d.text((38 + w0, 44), "& pipelines", font=f_serif_i, fill=CORAL)

        # Top-right date pill with subtle breathing dot
        d.rounded_rectangle((W - 216, 36, W - 40, 66), radius=15, fill=PAPER_DEEP, outline=LINE_STRONG, width=1)
        dot_col = INK_TEAL if (fi % 10) < 6 else SEAGLASS
        d.ellipse((W - 202, 47, W - 194, 55), fill=dot_col)
        draw_tracked(d, (W - 184, 44), f"SYNCED · {chrono['date_str']}", f_mono, INK_SOFT, tracking=0.8)

        d.line((0, 96, W, 96), fill=LINE, width=1)
        d.line((W // 2, 96, W // 2, H), fill=LINE, width=1)

        draw_tracked(d, (40, 114), "01  /  CHRONOLOGY & GITHUB TARGETS", f_label, INK_MUTED, tracking=1.7)
        draw_tracked(d, (W // 2 + 32, 114), "02  /  ACTIVE BUILD PIPELINES", f_label, INK_MUTED, tracking=1.7)

        hatch_shift = fi * 2

        # Left column bars (staggered smooth fill!)
        for idx, (title, sub, target, col, is_dark) in enumerate(left_bars):
            t_raw = (fi - idx * 1.4) / max(1, fill_frames - 5)
            cur_pct = target * ease_out_cubic(t_raw) if fi < fill_frames else target
            by = 144 + idx * 78
            d.text((40, by), title, font=f_title, fill=INK)
            pct_str = f"{cur_pct:.1f}%"
            pw = d.textlength(pct_str, font=f_pct)
            d.text((W // 2 - 36 - pw, by - 4), pct_str, font=f_pct, fill=INK_MUTED)
            draw_ruler_bar(d, 40, by + 28, W // 2 - 76, 14, cur_pct, col, hatch_shift + idx * 3, is_dark)
            d.text((40, by + 50), sub, font=f_sub, fill=INK_SOFT)

        # Bottom-left animated sine wave cadence indicator
        wy = 456
        d.line((40, 444, W // 2 - 36, 444), fill=LINE, width=1)
        pts = []
        for sx in range(0, 148, 3):
            phase = (sx / 148.0) * math.pi * 4.0 - fi * 0.25
            amp = 9.0 * math.exp(-sx / 120.0)
            pts.append((40 + sx, wy + 10 + int(math.sin(phase) * amp)))
        d.line(pts, fill=INK, width=2)
        dot_pt = pts[min(len(pts) - 1, int(((fi % total_frames) / total_frames) * len(pts)))]
        d.ellipse((dot_pt[0] - 3, dot_pt[1] - 3, dot_pt[0] + 3, dot_pt[1] + 3), fill=CORAL)
        draw_tracked(d, (204, 456), f"PEAK VELOCITY · {metrics['peak_day']} COMMITS / DAY", f_mono, INK_SOFT, tracking=0.8)

        # Right column bars
        for idx, (title, sub, target, col, is_dark) in enumerate(right_bars):
            t_raw = (fi - (idx + 1) * 1.2) / max(1, fill_frames - 5)
            cur_pct = target * ease_out_cubic(t_raw) if fi < fill_frames else target
            by = 144 + idx * 67
            rx0 = W // 2 + 32
            d.text((rx0, by), title, font=f_title, fill=INK)
            pct_str = f"{int(round(cur_pct))}%"
            pw = d.textlength(pct_str, font=f_pct)
            d.text((W - 40 - pw, by - 4), pct_str, font=f_pct, fill=INK_MUTED)
            draw_ruler_bar(d, rx0, by + 26, W // 2 - 72, 13, cur_pct, col, hatch_shift + idx * 2, is_dark)
            d.text((rx0, by + 46), sub, font=f_sub, fill=INK_SOFT)

        d.rectangle((0, 0, W - 1, H - 1), outline=LINE_STRONG, width=1)
        frames.append(img.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
        durations.append(55 if fi < fill_frames else 130)

    out_path = ASSETS_DIR / "progress.gif"
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print(f"Wrote {out_path.name} ({out_path.stat().st_size:,} bytes, {len(frames)} frames)")


def generate_activity_gif(metrics: dict, chrono: dict) -> None:
    """Animated 52-week contribution matrix + live metrics + language ribbon GIF (zero SVG)."""
    W, H = 1040, 304
    f_serif_num = load_font("EBGaramond-Regular.ttf", 34, 400)
    f_label = load_font("InstrumentSans.ttf", 10, 600)
    f_mono = load_font("JetBrainsMono.ttf", 10, 500)

    weeks = metrics["weeks"]
    while len(weeks) < 52:
        weeks.insert(0, [0] * 7)
    weeks = weeks[-52:]

    total_all = max(metrics["total_contributions"], 1073)
    top_stats = [
        (f"{total_all:,}+", "TOTAL CONTRIBUTIONS"),
        (f"{metrics['public_repos']}", "PUBLIC REPOSITORIES"),
        (f"{metrics['active_days']}", "ACTIVE PUBLIC DAYS"),
        (f"{metrics['peak_day']}/day", "PEAK VELOCITY"),
    ]

    langs = metrics["languages"][:6]
    lang_sum = sum(p for _, p in langs) or 100.0

    # 26 frames: quiet terracotta scanning playhead gliding smoothly across 52 weeks (2 weeks/frame)
    frames: list[Image.Image] = []
    n_frames = 26

    for fi in range(n_frames):
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)

        # Top 4-column stat strip
        col_w = W // 4
        for idx, (val, lbl) in enumerate(top_stats):
            cx = idx * col_w
            if idx > 0:
                d.line((cx, 0, cx, 86), fill=LINE, width=1)
            d.text((cx + 34, 10), val, font=f_serif_num, fill=INK)
            draw_tracked(d, (cx + 34, 60), lbl, f_label, INK_MUTED, tracking=1.6)

        d.line((0, 86, W, 86), fill=LINE, width=1)

        # 52-week contribution grid centered cleanly
        cell = 14
        gap = 4
        grid_w = 52 * (cell + gap) - gap
        gx0 = (W - grid_w) // 2
        gy0 = 104
        scan_week = fi * 2

        for wi, wk in enumerate(weeks):
            is_scan = abs(wi - scan_week) <= 1
            for di in range(min(7, len(wk))):
                cnt = wk[di]
                if cnt <= 0:
                    fill = (224, 214, 200) if is_scan else PAPER_DEEP
                elif cnt <= 2:
                    fill = SAGE
                elif cnt <= 5:
                    fill = SEAGLASS
                elif cnt <= 10:
                    fill = INK_TEAL
                else:
                    fill = INK
                if is_scan and cnt > 0:
                    fill = CORAL
                rx = gx0 + wi * (cell + gap)
                ry = gy0 + di * (cell + gap)
                d.rounded_rectangle((rx, ry, rx + cell, ry + cell), radius=3, fill=fill)

        # Quiet hairline scanner indicator line directly beneath the active scan week
        sx = gx0 + scan_week * (cell + gap) + cell // 2
        d.line((gx0, gy0 + 7 * (cell + gap) + 4, gx0 + grid_w, gy0 + 7 * (cell + gap) + 4), fill=LINE, width=1)
        d.rectangle((max(gx0, sx - 18), gy0 + 7 * (cell + gap) + 3, min(gx0 + grid_w, sx + 18), gy0 + 7 * (cell + gap) + 6), fill=CORAL)

        # Bottom stacked language ribbon + legend
        ry0 = 252
        rx = gx0
        for lang, pct in langs:
            seg_w = max(8, int(grid_w * (pct / lang_sum)))
            col = LANG_COLORS.get(lang, INK_TEAL)
            d.rectangle((rx, ry0, min(gx0 + grid_w, rx + seg_w - 2), ry0 + 10), fill=col)
            rx += seg_w

        # Legend row
        lx = gx0
        for lang, pct in langs:
            col = LANG_COLORS.get(lang, INK_TEAL)
            d.ellipse((lx, ry0 + 19, lx + 8, ry0 + 27), fill=col)
            txt = f"{lang} {pct:.1f}%"
            d.text((lx + 13, ry0 + 16), txt, font=f_mono, fill=INK_SOFT)
            lx += int(d.textlength(txt, font=f_mono)) + 30

        d.rectangle((0, 0, W - 1, H - 1), outline=LINE_STRONG, width=1)
        frames.append(img.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))

    out_path = ASSETS_DIR / "activity.gif"
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=120, loop=0, optimize=True)
    print(f"Wrote {out_path.name} ({out_path.stat().st_size:,} bytes, {len(frames)} frames)")


def unicode_bar(pct: float, width: int = 24) -> str:
    filled = max(0, min(width, int(round((pct / 100.0) * width))))
    return "█" * filled + "░" * (width - filled)


def update_readme_telemetry(metrics: dict, chrono: dict) -> None:
    if not README_PATH.exists():
        return
    text = README_PATH.read_text(encoding="utf-8")
    start_marker = "<!-- TELEMETRY:START -->"
    end_marker = "<!-- TELEMETRY:END -->"
    if start_marker not in text or end_marker not in text:
        return

    contribs = metrics["total_contributions"]
    total_all = max(contribs, 1073)
    c_goal = max(1500, int(math.ceil((total_all + 100) / 500.0) * 500))
    c_pct = round(min(100.0, (total_all / c_goal) * 100.0), 1)
    r_pct = round(min(100.0, (metrics["public_repos"] / 25.0) * 100.0), 1)

    lang_lines = []
    for lang, pct in metrics["languages"][:5]:
        lang_lines.append(f"{lang:<14} [{unicode_bar(pct, 22)}]  {pct:5.1f}%")

    block = f"""{start_marker}
```text
LIVE TELEMETRY  ·  SYNCED {chrono['iso_date']}  ·  BENGALURU, IN (12.97° N)
──────────────────────────────────────────────────────────────────────────
YEAR {chrono['year']}      [{unicode_bar(chrono['year_pct'], 22)}]  {chrono['year_pct']:5.1f}%   Day {chrono['day_of_year']} / {chrono['days_in_year']}
B.TECH ECE     [{unicode_bar(chrono['deg_pct'], 22)}]  {chrono['deg_pct']:5.1f}%   Sem {chrono['sem']} / 8 · MIT Bengaluru
CONTRIBUTIONS  [{unicode_bar(c_pct, 22)}]  {c_pct:5.1f}%   {total_all:,}+ total across 26 repos
OPEN SOURCE    [{unicode_bar(r_pct, 22)}]  {r_pct:5.1f}%   {metrics['public_repos']} / 25 public repositories

REPO-WEIGHTED LANGUAGES
{chr(10).join(lang_lines)}
```
{end_marker}"""

    updated = re.sub(
        rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}",
        block,
        text,
        flags=re.DOTALL,
    )
    README_PATH.write_text(updated, encoding="utf-8")
    print("Updated README.md live telemetry block.")


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    metrics = fetch_github_data()
    chrono = compute_chronology(now)

    generate_progress_gif(metrics, chrono)
    generate_activity_gif(metrics, chrono)
    update_readme_telemetry(metrics, chrono)


if __name__ == "__main__":
    main()
