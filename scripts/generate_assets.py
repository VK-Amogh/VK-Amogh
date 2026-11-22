#!/usr/bin/env python3
"""
Generate bespoke Quiet Studio editorial SVG assets for VK-Amogh's GitHub profile.
Mirrors the exact design language of amogh.evenei.com:
  warm cotton paper (#F4EDE3), espresso ink (#1A1412), terracotta coral (#D95D39),
  flat matte Bauhaus pastels, 1px editorial hairlines, serif display typography,
  and calm architectural kinetic micro-animations.
Zero external dependencies (Python stdlib only) for fast GitHub Actions runs.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import math
import os
import urllib.error
import urllib.request
from pathlib import Path

USERNAME = "VK-Amogh"
ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"

# Quiet Studio flat matte pastel/ink palette — ZERO gradients, ZERO neon
PAPER = "#F4EDE3"
PAPER_DEEP = "#ECE3D5"
INK = "#1A1412"
INK_SOFT = "#3D2F28"
INK_MUTED = "#8F3E26"
INK_TEAL = "#1E5A52"
INK_NAVY = "#2A3F66"
LINE = "#DDD4C7"
LINE_STRONG = "#C5B9A9"

CORAL = "#D95D39"
CORAL_SOFT = "#F0926A"
MARIGOLD = "#E9BF52"
SKY = "#9DBDD8"
SKY_SLATE = "#A6C3D6"
ROSE = "#EDB3C3"
SAGE = "#BACFAE"
SEAGLASS = "#A9CCC4"
LILAC = "#C3BBE3"
PEACH = "#F1B48E"
SAND = "#E7D3AE"

LANG_PALETTE = {
    "Python": INK_NAVY,
    "Dart": INK_TEAL,
    "TypeScript": SKY,
    "HTML": CORAL_SOFT,
    "CSS": LILAC,
    "ShaderLab": SAGE,
    "JavaScript": MARIGOLD,
    "C++": ROSE,
    "Jupyter Notebook": PEACH,
    "Kotlin": SAND,
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
            node { name color }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
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


def fetch_github_data() -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    fallback = {
        "total_contributions": 1073,
        "commits": 1046,
        "public_repos": 18,
        "total_repos_note": 26,
        "stars": 3,
        "forks": 6,
        "followers": 2,
        "active_days": 64,
        "peak_day": 110,
        "languages": [
            ("Python", 47.8),
            ("Dart", 12.2),
            ("HTML", 10.2),
            ("TypeScript", 9.1),
            ("CSS", 5.9),
            ("ShaderLab", 5.9),
        ],
    }

    if not token:
        print("No GITHUB_TOKEN found; using fallback metrics.")
        return fallback

    payload = json.dumps({"query": GRAPHQL_QUERY, "variables": {"login": USERNAME}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "VK-Amogh-Quiet-Studio-Generator",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"GraphQL fetch failed ({exc}); using fallback metrics.")
        return fallback

    user = (raw.get("data") or {}).get("user")
    if not user:
        print("GraphQL returned empty user; using fallback metrics.")
        return fallback

    repos = user["repositories"]
    nodes = repos.get("nodes") or []
    contrib = user["contributionsCollection"]
    cal = contrib["contributionCalendar"]

    stars = sum(n.get("stargazerCount", 0) for n in nodes)
    forks = sum(n.get("forkCount", 0) for n in nodes)

    weights: dict[str, float] = {}
    for repo in nodes:
        edges = (repo.get("languages") or {}).get("edges") or []
        repo_total = sum(e.get("size", 0) for e in edges)
        if repo_total <= 0:
            continue
        for edge in edges:
            lang = edge["node"]["name"]
            weights[lang] = weights.get(lang, 0.0) + (edge["size"] / repo_total)

    total_w = sum(weights.values()) or 1.0
    sorted_langs = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)
    top_langs = [(name, round((val / total_w) * 100, 1)) for name, val in sorted_langs[:6]]
    if not top_langs:
        top_langs = fallback["languages"]

    days = [
        d
        for w in (cal.get("weeks") or [])
        for d in (w.get("contributionDays") or [])
    ]
    active_days = sum(1 for d in days if d.get("contributionCount", 0) > 0)
    peak_day = max((d.get("contributionCount", 0) for d in days), default=fallback["peak_day"])

    return {
        "total_contributions": cal.get("totalContributions", fallback["total_contributions"]),
        "commits": contrib.get("totalCommitContributions", fallback["commits"]),
        "public_repos": repos.get("totalCount", fallback["public_repos"]),
        "total_repos_note": max(26, repos.get("totalCount", 18)),
        "stars": stars,
        "forks": forks,
        "followers": (user.get("followers") or {}).get("totalCount", fallback["followers"]),
        "active_days": active_days,
        "peak_day": peak_day,
        "languages": top_langs,
    }


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def compute_chronology(now: dt.datetime) -> dict:
    year = now.year
    year_start = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc)
    year_end = dt.datetime(year + 1, 1, 1, tzinfo=dt.timezone.utc)
    year_pct = ((now - year_start).total_seconds() / (year_end - year_start).total_seconds()) * 100.0
    year_pct = max(0.0, min(100.0, year_pct))
    day_of_year = (now - year_start).days + 1
    days_in_year = (year_end - year_start).days

    deg_start = dt.datetime(2024, 8, 1, tzinfo=dt.timezone.utc)
    deg_end = dt.datetime(2028, 5, 31, tzinfo=dt.timezone.utc)
    deg_pct = ((now - deg_start).total_seconds() / (deg_end - deg_start).total_seconds()) * 100.0
    deg_pct = max(0.0, min(100.0, deg_pct))
    sem = min(8, max(1, int(math.ceil((deg_pct / 100.0) * 8))))

    return {
        "year": year,
        "year_pct": round(year_pct, 1),
        "day_of_year": day_of_year,
        "days_in_year": days_in_year,
        "deg_pct": round(deg_pct, 1),
        "sem": sem,
        "date_str": now.strftime("%d %b %Y"),
    }


def render_editorial_bar(
    uid: str,
    x: float,
    y: float,
    width: float,
    height: float,
    pct: float,
    fill_color: str,
    dark_fill: bool = False,
    hatch_dur: float = 2.6,
    phase: float = 0.0,
) -> tuple[str, str]:
    """Swiss architectural ruler progress bar — flat matte fill, moving draughtsman hatch, crisp ink needle."""
    clamped = max(5.0, min(100.0, pct))
    fill_w = round(width * (clamped / 100.0), 2)
    rx = round(height / 2.0, 2)
    tip_x = round(x + fill_w, 2)
    cy = round(y + height / 2.0, 2)

    hatch_pat = "hatchLight" if dark_fill else "hatchInk"
    hatch_opacity = "0.22" if dark_fill else "0.14"

    t25 = round(x + width * 0.25, 1)
    t50 = round(x + width * 0.50, 1)
    t75 = round(x + width * 0.75, 1)

    defs = f"""
    <clipPath id="clip_{uid}">
      <rect x="{x}" y="{y}" width="{fill_w}" height="{height}" rx="{rx}"/>
    </clipPath>"""

    elems = f"""
    <g>
      <!-- Warm deep-paper ruler track with subtle quarter ticks -->
      <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{rx}" fill="{PAPER_DEEP}" stroke="{LINE_STRONG}" stroke-width="1"/>
      <line x1="{t25}" y1="{y + 2}" x2="{t25}" y2="{y + height - 2}" stroke="{INK}" stroke-opacity="0.14" stroke-width="1"/>
      <line x1="{t50}" y1="{y + 1.5}" x2="{t50}" y2="{y + height - 1.5}" stroke="{INK}" stroke-opacity="0.22" stroke-width="1"/>
      <line x1="{t75}" y1="{y + 2}" x2="{t75}" y2="{y + height - 2}" stroke="{INK}" stroke-opacity="0.14" stroke-width="1"/>

      <!-- Crisp matte solid fill + calm kinetic draughtsman hatching -->
      <g clip-path="url(#clip_{uid})">
        <rect x="{x}" y="{y}" width="{fill_w}" height="{height}" rx="{rx}" fill="{fill_color}"/>
        <rect x="{x - 24}" y="{y}" width="{fill_w + 48}" height="{height}" fill="url(#{hatch_pat})" opacity="{hatch_opacity}">
          <animateTransform attributeName="transform" type="translate" from="0 0" to="14 0" dur="{hatch_dur:.2f}s" repeatCount="indefinite"/>
        </rect>
      </g>

      <!-- Architectural border around fill -->
      <rect x="{x}" y="{y}" width="{fill_w}" height="{height}" rx="{rx}" fill="none" stroke="{INK}" stroke-opacity="0.28" stroke-width="0.9"/>

      <!-- Quiet breathing Vernier calibration needle at exact percentage frontier -->
      <line x1="{tip_x}" y1="{y - 3.5}" x2="{tip_x}" y2="{y + height + 3.5}" stroke="{INK}" stroke-width="1.3" stroke-linecap="round">
        <animate attributeName="opacity" values="0.95;0.45;0.95" begin="{phase:.2f}s" dur="3.4s" repeatCount="indefinite"/>
      </line>
      <circle cx="{tip_x}" cy="{y - 3.5}" r="2.2" fill="{CORAL}">
        <animate attributeName="r" values="2;2.8;2" begin="{phase:.2f}s" dur="3.4s" repeatCount="indefinite"/>
      </circle>
    </g>"""
    return defs, elems


def generate_hero_editorial(metrics: dict) -> str:
    total_all = max(metrics["total_contributions"], 1073)
    contribs_fmt = f"{total_all:,}+"

    return f"""<svg width="900" height="456" viewBox="0 0 900 456" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Amogh V K — Quiet Studio Editorial Profile">
  <defs>
    <clipPath id="heroFrame">
      <rect x="1" y="1" width="898" height="454" rx="18"/>
    </clipPath>
    <style>
      .serif {{ font-family: Georgia, 'Palatino Linotype', 'Book Antiqua', 'Times New Roman', serif; }}
      .sans {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
      .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    </style>
  </defs>

  <g clip-path="url(#heroFrame)">
    <!-- Warm cotton paper canvas -->
    <rect x="0" y="0" width="900" height="456" fill="{PAPER}"/>

    <!-- 4-column quiet vertical hairline grid (straight from amogh.evenei.com) -->
    <line x1="225" y1="48" x2="225" y2="456" stroke="{INK}" stroke-opacity="0.045" stroke-width="1"/>
    <line x1="450" y1="48" x2="450" y2="456" stroke="{INK}" stroke-opacity="0.045" stroke-width="1"/>
    <line x1="675" y1="48" x2="675" y2="456" stroke="{INK}" stroke-opacity="0.045" stroke-width="1"/>

    <!-- Subtle drifting flat Bauhaus geometric forms in background (KineticShapes.jsx) -->
    <circle cx="38" cy="144" r="14" fill="{SKY}" opacity="0.34">
      <animateTransform attributeName="transform" type="translate" values="0,0; 0,-7; 0,0" dur="9s" repeatCount="indefinite"/>
    </circle>
    <rect x="336" y="96" width="16" height="16" rx="4" fill="{MARIGOLD}" opacity="0.38">
      <animateTransform attributeName="transform" type="rotate" values="0 344 104; 90 344 104; 0 344 104" dur="14s" repeatCount="indefinite"/>
    </rect>
    <path d="M 488 268 V 252 A 13 13 0 0 1 514 252 V 268 Z" fill="{SAGE}" opacity="0.42">
      <animateTransform attributeName="transform" type="translate" values="0,0; 0,6; 0,0" dur="10s" repeatCount="indefinite"/>
    </path>
    <rect x="846" y="294" width="34" height="14" rx="7" fill="{ROSE}" opacity="0.48">
      <animateTransform attributeName="transform" type="translate" values="0,0; -6,0; 0,0" dur="11s" repeatCount="indefinite"/>
    </rect>
    <circle cx="526" cy="96" r="16" fill="none" stroke="{INK_MUTED}" stroke-width="1.2" opacity="0.24">
      <animateTransform attributeName="transform" type="translate" values="0,0; 4,5; 0,0" dur="12s" repeatCount="indefinite"/>
    </circle>

    <!-- Quiet Editorial Masthead Bar -->
    <rect x="0" y="0" width="900" height="48" fill="{PAPER}"/>
    <line x1="0" y1="48" x2="900" y2="48" stroke="{LINE}" stroke-width="1"/>
    <!-- Animated terracotta scroll hairline (exact scroll-hairline motif from portfolio) -->
    <rect x="0" y="47" width="180" height="1.8" fill="{CORAL}">
      <animate attributeName="x" values="0;720;0" dur="11s" calcMode="spline" keySplines="0.42 0 0.58 1; 0.42 0 0.58 1" repeatCount="indefinite"/>
    </rect>

    <text x="36" y="30" class="serif" font-size="19" font-weight="500" fill="{INK}">Amogh VK<tspan fill="{CORAL}">.</tspan></text>

    <g class="sans" font-size="9.5" font-weight="500" fill="{INK_SOFT}" letter-spacing="1.7">
      <text x="415" y="28">WORK</text>
      <text x="478" y="28">PROGRESS</text>
      <text x="568" y="28">CRAFT</text>
      <text x="636" y="28">WRITING</text>
    </g>

    <!-- Top-right solid ink Resume / Portfolio pill -->
    <rect x="760" y="12" width="104" height="24" rx="12" fill="{INK}"/>
    <text x="812" y="27.5" text-anchor="middle" class="sans" font-size="9.5" font-weight="500" fill="{PAPER}" letter-spacing="1.3">PORTFOLIO ↗</text>

    <!-- HERO LEFT COLUMN -->
    <text x="36" y="88" class="sans" font-size="10" font-weight="600" fill="{INK_MUTED}" letter-spacing="2.1">ENGINEERING, AI AND PRODUCT</text>

    <text x="34" y="152" class="serif" font-size="60" font-weight="400" fill="{INK}" letter-spacing="-1">Amogh <tspan font-style="italic" fill="{CORAL}">VK.</tspan></text>

    <text x="36" y="186" class="sans" font-size="20.5" font-weight="400" fill="{INK}" letter-spacing="-0.3">I turn ambitious ideas into useful</text>
    <text x="36" y="212" class="sans" font-size="20.5" font-weight="400" fill="{INK}" letter-spacing="-0.3">technology and ventures.</text>

    <text x="36" y="242" class="sans" font-size="13" fill="{INK_SOFT}">Founder of EvenEi and The Developer Community, studying ECE at MIT Bengaluru.</text>
    <text x="36" y="261" class="sans" font-size="13" fill="{INK_SOFT}">Building across software, AI, hardware, security, and spacecraft systems.</text>

    <!-- Editorial Clean Pills (.btn-ink & .btn-clean) -->
    <g transform="translate(36, 282)">
      <rect x="0" y="0" width="194" height="32" rx="16" fill="{INK}"/>
      <text x="97" y="19.5" text-anchor="middle" class="sans" font-size="10" font-weight="500" fill="{PAPER}" letter-spacing="1.3">AMOGH.EVENEI.COM  ↗</text>

      <rect x="206" y="0" width="198" height="32" rx="16" fill="{PAPER}" stroke="{LINE_STRONG}" stroke-width="1"/>
      <text x="305" y="19.5" text-anchor="middle" class="sans" font-size="10" font-weight="500" fill="{INK_SOFT}" letter-spacing="1.3">BENGALURU, INDIA · 12.97° N</text>
    </g>

    <!-- HERO RIGHT COLUMN: Animated Quiet Studio Constellation Plate (SectionArt.jsx) -->
    <g transform="translate(556, 72)">
      <rect x="0" y="0" width="308" height="242" rx="14" fill="{PAPER_DEEP}" stroke="{LINE_STRONG}" stroke-width="1"/>

      <!-- Plate top window bar -->
      <line x1="0" y1="30" x2="308" y2="30" stroke="{LINE}" stroke-width="1"/>
      <circle cx="16" cy="15" r="3.5" fill="{CORAL_SOFT}"/>
      <circle cx="28" cy="15" r="3.5" fill="{MARIGOLD}"/>
      <circle cx="40" cy="15" r="3.5" fill="{SAGE}"/>
      <text x="154" y="18.5" text-anchor="middle" class="sans" font-size="9.5" font-weight="600" fill="{INK_SOFT}" letter-spacing="1.5">SYSTEMS CONSTELLATION</text>
      <text x="294" y="18.5" text-anchor="end" class="mono" font-size="9" fill="{INK_MUTED}">04</text>

      <!-- Systems Constellation artwork (exact geometry from SectionArt.jsx) -->
      <g transform="translate(0, 26)">
        <circle cx="154" cy="84" r="64" fill="none" stroke="{INK}" stroke-opacity="0.16" stroke-width="1" stroke-dasharray="3 6">
          <animateTransform attributeName="transform" type="rotate" from="0 154 84" to="360 154 84" dur="44s" repeatCount="indefinite"/>
        </circle>
        <circle cx="154" cy="84" r="35" fill="none" stroke="{INK}" stroke-opacity="0.12" stroke-width="1"/>

        <!-- Connecting lines -->
        <path d="M 86 48 L 210 38 L 228 118 L 100 128 Z" fill="none" stroke="{INK}" stroke-opacity="0.24" stroke-width="1"/>
        <line x1="86" y1="48" x2="228" y2="118" stroke="{INK}" stroke-opacity="0.12" stroke-width="1"/>
        <line x1="210" y1="38" x2="100" y2="128" stroke="{INK}" stroke-opacity="0.12" stroke-width="1"/>

        <!-- Animated ink traveler moving quietly along the constellation edges -->
        <circle cx="0" cy="0" r="3.4" fill="{INK}">
          <animateMotion dur="9.5s" repeatCount="indefinite" path="M 86,48 L 210,38 L 228,118 L 100,128 Z"/>
        </circle>

        <!-- 4 flat solid pastel principle nodes -->
        <circle cx="86" cy="48" r="15" fill="{CORAL_SOFT}">
          <animate attributeName="r" values="14.5;16.5;14.5" dur="5.2s" repeatCount="indefinite"/>
        </circle>
        <circle cx="86" cy="48" r="20" fill="none" stroke="{INK}" stroke-opacity="0.18" stroke-width="0.9"/>

        <circle cx="210" cy="38" r="13" fill="{SKY}">
          <animate attributeName="r" values="12.5;14.2;12.5" begin="1.2s" dur="5.6s" repeatCount="indefinite"/>
        </circle>
        <circle cx="210" cy="38" r="18" fill="none" stroke="{INK}" stroke-opacity="0.14" stroke-width="0.9"/>

        <circle cx="228" cy="118" r="16" fill="{MARIGOLD}">
          <animate attributeName="r" values="15.5;17.2;15.5" begin="2.4s" dur="5.0s" repeatCount="indefinite"/>
        </circle>
        <circle cx="228" cy="118" r="21" fill="none" stroke="{INK}" stroke-opacity="0.14" stroke-width="0.9"/>

        <circle cx="100" cy="128" r="13.5" fill="{SAGE}">
          <animate attributeName="r" values="13;14.8;13" begin="3.6s" dur="5.4s" repeatCount="indefinite"/>
        </circle>
        <circle cx="100" cy="128" r="18.5" fill="none" stroke="{INK}" stroke-opacity="0.14" stroke-width="0.9"/>

        <!-- Center paper diamond -->
        <rect x="148" y="78" width="12" height="12" rx="2" fill="{PAPER}" stroke="{INK}" stroke-width="1" transform="rotate(45 154 84)"/>

        <!-- Crisp micro node captions -->
        <text x="58" y="25" class="sans" font-size="8.5" font-weight="600" fill="{INK_SOFT}" letter-spacing="1.2">SYSTEMS</text>
        <text x="228" y="21" class="sans" font-size="8.5" font-weight="600" fill="{INK_SOFT}" letter-spacing="1.2">LIMITS</text>
        <text x="234" y="153" text-anchor="middle" class="sans" font-size="8.5" font-weight="600" fill="{INK_SOFT}" letter-spacing="1.2">PROOF</text>
        <text x="64" y="153" class="sans" font-size="8.5" font-weight="600" fill="{INK_SOFT}" letter-spacing="1.2">CLARITY</text>
      </g>

      <!-- Bottom integrated damped B-dot oscillation strip -->
      <line x1="0" y1="196" x2="308" y2="196" stroke="{LINE}" stroke-width="1"/>
      <line x1="18" y1="219" x2="290" y2="219" stroke="{INK}" stroke-opacity="0.16" stroke-width="0.9"/>
      <path d="M 18 219 C 42 199, 64 239, 90 219 C 114 203, 138 234, 166 219 C 190 210, 214 226, 240 219 C 258 216, 274 220, 290 219" fill="none" stroke="{INK}" stroke-width="1.25"/>
      <circle cx="0" cy="0" r="3.2" fill="{CORAL}">
        <animateMotion dur="5.8s" repeatCount="indefinite" path="M 18,219 C 42,199 64,239 90,219 C 114,203 138,234 166,219 C 190,210 214,226 240,219 C 258,216 274,220 290,219"/>
      </circle>
      <circle cx="264" cy="219" r="7.5" fill="{SKY}" opacity="0.55">
        <animate attributeName="r" values="6;9;6" dur="2.8s" repeatCount="indefinite"/>
      </circle>
      <circle cx="264" cy="219" r="2.5" fill="{INK}"/>
    </g>

    <!-- INTEGRATED 4-COLUMN EDITORIAL IMPACT BAND (1:1 match with portfolio) -->
    <line x1="0" y1="342" x2="900" y2="342" stroke="{LINE}" stroke-width="1"/>
    <line x1="225" y1="342" x2="225" y2="456" stroke="{LINE}" stroke-width="1"/>
    <line x1="450" y1="342" x2="450" y2="456" stroke="{LINE}" stroke-width="1"/>
    <line x1="675" y1="342" x2="675" y2="456" stroke="{LINE}" stroke-width="1"/>

    <g transform="translate(36, 388)">
      <text x="0" y="0" class="serif" font-size="33" font-weight="400" fill="{INK}">{esc(contribs_fmt)}</text>
      <text x="0" y="22" class="sans" font-size="9.5" font-weight="600" fill="{INK}" letter-spacing="1.6">GITHUB CONTRIBUTIONS</text>
      <text x="0" y="39" class="sans" font-size="11" fill="{INK_SOFT}">1,046 commits across 26+ repos</text>
    </g>

    <g transform="translate(249, 388)">
      <text x="0" y="0" class="serif" font-size="33" font-weight="400" fill="{INK}">10,000+</text>
      <text x="0" y="22" class="sans" font-size="9.5" font-weight="600" fill="{INK}" letter-spacing="1.6">ACTIVE VETERINARIANS</text>
      <text x="0" y="39" class="sans" font-size="11" fill="{INK_SOFT}">Served via Vetifi AI workflows</text>
    </g>

    <g transform="translate(474, 388)">
      <text x="0" y="0" class="serif" font-size="33" font-weight="400" fill="{INK}">1,000+</text>
      <text x="0" y="22" class="sans" font-size="9.5" font-weight="600" fill="{INK}" letter-spacing="1.6">TDC REGISTRATIONS</text>
      <text x="0" y="39" class="sans" font-size="11" fill="{INK_SOFT}">Builders across 5+ universities</text>
    </g>

    <g transform="translate(699, 388)">
      <text x="0" y="0" class="serif" font-size="33" font-weight="400" fill="{INK}">0.261s</text>
      <text x="0" y="22" class="sans" font-size="9.5" font-weight="600" fill="{INK}" letter-spacing="1.6">TRACE LOCAL AUDIT</text>
      <text x="0" y="39" class="sans" font-size="11" fill="{INK_SOFT}">189 files, 39 endpoints, 0 tokens</text>
    </g>
  </g>

  <rect x="1" y="1" width="898" height="454" rx="18" stroke="{LINE_STRONG}" stroke-width="1"/>
</svg>
"""


def generate_editorial_rule() -> str:
    return f"""<svg width="900" height="20" viewBox="0 0 900 20" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Editorial hairline rule">
  <line x1="0" y1="10" x2="900" y2="10" stroke="{LINE_STRONG}" stroke-width="1"/>
  <g>
    <rect x="0" y="9" width="76" height="2" fill="{CORAL}"/>
    <circle cx="38" cy="10" r="3" fill="{PAPER}" stroke="{CORAL}" stroke-width="1.3"/>
    <animateTransform attributeName="transform" type="translate" values="60,0; 764,0; 60,0" dur="12s" calcMode="spline" keySplines="0.42 0 0.58 1; 0.42 0 0.58 1" repeatCount="indefinite"/>
  </g>
</svg>
"""


def render_poster_card(
    uid: str,
    name: str,
    year: str,
    line1: str,
    line2: str,
    tagline1: str,
    tagline2: str,
    footer: str,
    bg: str,
    bg_shapes_svg: str,
    motif_svg: str,
) -> str:
    return f"""<svg width="440" height="252" viewBox="0 0 440 252" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(name)} — {esc(line1)} {esc(line2)}">
  <defs>
    <clipPath id="pclip_{uid}">
      <rect x="1" y="1" width="438" height="250" rx="16"/>
    </clipPath>
    <style>
      .serif {{ font-family: Georgia, 'Palatino Linotype', 'Book Antiqua', 'Times New Roman', serif; }}
      .sans {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
    </style>
  </defs>

  <g clip-path="url(#pclip_{uid})">
    <rect x="0" y="0" width="440" height="252" fill="{bg}"/>

    <!-- Flat drifting Bauhaus solid forms (straight from Poster.jsx) -->
    {bg_shapes_svg}

    <!-- Top meta bar -->
    <text x="26" y="30" class="sans" font-size="9.5" font-weight="600" fill="{INK}" fill-opacity="0.72" letter-spacing="1.7">{esc(name.upper())}</text>
    <text x="414" y="30" text-anchor="end" class="sans" font-size="9.5" font-weight="600" fill="{INK}" fill-opacity="0.72" letter-spacing="1.5">{esc(year)}</text>

    <!-- Two-line editorial serif headline (second line italic!) -->
    <text x="26" y="102" class="serif" font-size="34" font-weight="400" fill="{INK}" letter-spacing="-0.6">{esc(line1)}</text>
    <text x="26" y="138" class="serif" font-size="34" font-weight="400" font-style="italic" fill="{INK}" letter-spacing="-0.6">{esc(line2)}</text>

    <!-- Concise tagline -->
    <text x="26" y="166" class="sans" font-size="11.5" fill="{INK}" fill-opacity="0.78">{esc(tagline1)}</text>
    <text x="26" y="182" class="sans" font-size="11.5" fill="{INK}" fill-opacity="0.78">{esc(tagline2)}</text>

    <!-- Bespoke animated architectural vector motif on right -->
    <g transform="translate(274, 62)">
      <rect x="0" y="0" width="140" height="122" rx="12" fill="{PAPER}" fill-opacity="0.88" stroke="{INK}" stroke-opacity="0.22" stroke-width="1"/>
      {motif_svg}
    </g>

    <!-- Bottom editorial footer & arrow -->
    <line x1="26" y1="214" x2="414" y2="214" stroke="{INK}" stroke-opacity="0.16" stroke-width="1"/>
    <text x="26" y="234" class="sans" font-size="9.5" font-weight="600" fill="{INK}" fill-opacity="0.76" letter-spacing="1.6">{esc(footer.upper())}</text>
    <text x="414" y="235" text-anchor="end" class="sans" font-size="15" font-weight="400" fill="{INK}">↗</text>
  </g>

  <rect x="1" y="1" width="438" height="250" rx="16" stroke="{INK}" stroke-opacity="0.14" stroke-width="1"/>
</svg>
"""


def generate_posters() -> dict[str, str]:
    posters = {}

    # 1. TRACE — Seaglass #A9CCC4
    posters["poster-trace.svg"] = render_poster_card(
        uid="trace",
        name="TRACE",
        year="2026",
        line1="Security that",
        line2="proves itself.",
        tagline1="Local-first AST & Attack-Path scanner.",
        tagline2="0.261s · 189 files · 0 tokens · MCP",
        footer="Parse, model, verify",
        bg=SEAGLASS,
        bg_shapes_svg=f"""
        <rect x="278" y="-36" width="128" height="270" rx="64" fill="{CORAL_SOFT}">
          <animateTransform attributeName="transform" type="translate" values="0,0; 0,10; 0,0" dur="10s" repeatCount="indefinite"/>
        </rect>
        <circle cx="22" cy="242" r="72" fill="{PAPER}" opacity="0.58"/>
        <rect x="336" y="198" width="90" height="62" rx="10" fill="{MARIGOLD}"/>""",
        motif_svg=f"""
        <line x1="22" y1="61" x2="62" y2="34" stroke="{INK}" stroke-opacity="0.3" stroke-width="1.2"/>
        <line x1="22" y1="61" x2="62" y2="88" stroke="{INK}" stroke-opacity="0.3" stroke-width="1.2"/>
        <line x1="62" y1="34" x2="100" y2="61" stroke="{INK}" stroke-opacity="0.3" stroke-width="1.2"/>
        <line x1="62" y1="88" x2="100" y2="61" stroke="{INK}" stroke-opacity="0.3" stroke-width="1.2"/>
        <line x1="100" y1="61" x2="124" y2="61" stroke="{CORAL}" stroke-width="1.5" stroke-dasharray="3 3"/>
        <circle cx="0" cy="0" r="3.6" fill="{CORAL}">
          <animateMotion dur="3.4s" repeatCount="indefinite" path="M 22,61 L 62,34 L 100,61 L 124,61"/>
        </circle>
        <circle cx="22" cy="61" r="7" fill="{SEAGLASS}" stroke="{INK}" stroke-width="1"/>
        <circle cx="62" cy="34" r="6" fill="{MARIGOLD}" stroke="{INK}" stroke-width="1"/>
        <circle cx="62" cy="88" r="6" fill="{SKY}" stroke="{INK}" stroke-width="1"/>
        <rect x="92" y="53" width="16" height="16" rx="4" fill="{PAPER}" stroke="{INK}" stroke-width="1"/>
        <circle cx="124" cy="61" r="7.5" fill="{CORAL_SOFT}" stroke="{INK}" stroke-width="1"/>
        <text x="12" y="112" class="sans" font-size="8" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.2">APM · 100% RECALL</text>""",
    )

    # 2. SPECULAR — Sage #BACFAE
    posters["poster-specular.svg"] = render_poster_card(
        uid="specular",
        name="Specular · EvenEi",
        year="2024–2026",
        line1="Memory,",
        line2="worn lightly.",
        tagline1="AI smart glasses · ESP32-S3 + Flutter.",
        tagline2="$1K seed · Google / Antler Immersion",
        footer="Glasses, phone, cloud",
        bg=SAGE,
        bg_shapes_svg=f"""
        <circle cx="352" cy="116" r="106" fill="{ROSE}">
          <animateTransform attributeName="transform" type="translate" values="0,0; -7,6; 0,0" dur="11s" repeatCount="indefinite"/>
        </circle>
        <rect x="-18" y="196" width="128" height="72" rx="36" fill="{PAPER}" opacity="0.62"/>
        <rect x="318" y="194" width="108" height="66" rx="12" fill="{SKY}"/>""",
        motif_svg=f"""
        <rect x="16" y="38" width="44" height="30" rx="15" fill="{SAGE}" fill-opacity="0.55" stroke="{INK}" stroke-width="1.1"/>
        <rect x="80" y="38" width="44" height="30" rx="15" fill="{MARIGOLD}" fill-opacity="0.55" stroke="{INK}" stroke-width="1.1"/>
        <path d="M 60 51 Q 70 43 80 51" fill="none" stroke="{INK}" stroke-width="1.2"/>
        <circle cx="38" cy="53" r="8" fill="none" stroke="{INK}" stroke-width="1" stroke-dasharray="2.5 2.5">
          <animateTransform attributeName="transform" type="rotate" from="0 38 53" to="360 38 53" dur="9s" repeatCount="indefinite"/>
        </circle>
        <circle cx="102" cy="53" r="4" fill="{CORAL}">
          <animate attributeName="r" values="3.2;5.2;3.2" dur="2.6s" repeatCount="indefinite"/>
        </circle>
        <text x="12" y="112" class="sans" font-size="8" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.2">SUB-20K INR BOM</text>""",
    )

    # 3. VETIFI AI — Warm Peach #F1B48E
    posters["poster-vetifi.svg"] = render_poster_card(
        uid="vetifi",
        name="Vetifi AI",
        year="2025–2026",
        line1="Care,",
        line2="with evidence.",
        tagline1="Clinical veterinary RAG & knowledge graph.",
        tagline2="10,000+ active vets · 96.23% accuracy",
        footer="Retrieve, reason, recommend",
        bg=PEACH,
        bg_shapes_svg=f"""
        <path d="M 252 252 V 82 A 92 92 0 0 1 436 82 V 252 Z" fill="{SKY}">
          <animateTransform attributeName="transform" type="translate" values="0,0; 0,-8; 0,0" dur="10.5s" repeatCount="indefinite"/>
        </path>
        <circle cx="18" cy="240" r="68" fill="{PAPER}" opacity="0.58"/>
        <rect x="330" y="196" width="96" height="62" rx="10" fill="{SAGE}"/>""",
        motif_svg=f"""
        <circle cx="70" cy="54" r="30" fill="none" stroke="{INK}" stroke-opacity="0.2" stroke-width="1"/>
        <g>
          <circle cx="70" cy="24" r="5" fill="{CORAL_SOFT}" stroke="{INK}" stroke-width="0.9"/>
          <circle cx="100" cy="54" r="4.5" fill="{SKY}" stroke="{INK}" stroke-width="0.9"/>
          <circle cx="40" cy="54" r="4.5" fill="{MARIGOLD}" stroke="{INK}" stroke-width="0.9"/>
          <circle cx="70" cy="84" r="5" fill="{SAGE}" stroke="{INK}" stroke-width="0.9"/>
          <animateTransform attributeName="transform" type="rotate" from="0 70 54" to="360 70 54" dur="16s" repeatCount="indefinite"/>
        </g>
        <circle cx="70" cy="54" r="11" fill="{PEACH}" stroke="{INK}" stroke-width="1"/>
        <rect x="68" y="48" width="4" height="12" rx="1.5" fill="{INK}"/>
        <rect x="64" y="52" width="12" height="4" rx="1.5" fill="{INK}"/>
        <text x="12" y="112" class="sans" font-size="8" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.2">BM25 + ONTOLOGY</text>""",
    )

    # 4. SARAL AI — Sky #9DBDD8
    posters["poster-saral.svg"] = render_poster_card(
        uid="saral",
        name="Saral AI",
        year="2026",
        line1="Civic life,",
        line2="made simple.",
        tagline1="Privacy-first Flutter civic assistant.",
        tagline2="12-state FastAPI · FLAG_SECURE vault",
        footer="Ask, automate, vault",
        bg=SKY,
        bg_shapes_svg=f"""
        <path d="M 248 252 V 76 A 96 96 0 0 1 440 76 V 252 Z" fill="{PAPER}" opacity="0.62">
          <animateTransform attributeName="transform" type="translate" values="0,0; 0,8; 0,0" dur="11.5s" repeatCount="indefinite"/>
        </path>
        <circle cx="38" cy="242" r="56" fill="{CORAL_SOFT}"/>
        <rect x="308" y="196" width="120" height="62" rx="31" fill="{MARIGOLD}"/>""",
        motif_svg=f"""
        <rect x="46" y="14" width="48" height="76" rx="11" fill="{PAPER_DEEP}" stroke="{INK}" stroke-width="1.1"/>
        <line x1="63" y1="22" x2="77" y2="22" stroke="{INK}" stroke-width="1.2" stroke-linecap="round"/>
        <rect x="54" y="31" width="32" height="16" rx="4" fill="{CORAL_SOFT}" opacity="0.82"/>
        <line x1="54" y1="57" x2="86" y2="57" stroke="{INK}" stroke-opacity="0.35" stroke-width="1.2"/>
        <line x1="54" y1="65" x2="76" y2="65" stroke="{INK}" stroke-opacity="0.35" stroke-width="1.2"/>
        <circle cx="54" cy="76" r="3" fill="{INK_TEAL}">
          <animate attributeName="cx" values="54;84;54" dur="3.6s" repeatCount="indefinite"/>
        </circle>
        <text x="12" y="112" class="sans" font-size="8" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.2">ZERO CLOUD SECRETS</text>""",
    )

    # 5. THE DEVELOPER COMMUNITY — Dusty Rose #EDB3C3
    posters["poster-tdc.svg"] = render_poster_card(
        uid="tdc",
        name="The Developer Community",
        year="2025–2026",
        line1="Students",
        line2="who ship.",
        tagline1="1,000+ registrations across 5+ univs.",
        tagline2="React Router 7 SSR · ONE-CREW · STASH",
        footer="Learn, build, prove",
        bg=ROSE,
        bg_shapes_svg=f"""
        <circle cx="350" cy="96" r="98" fill="{MARIGOLD}">
          <animateTransform attributeName="transform" type="translate" values="0,0; 6,-6; 0,0" dur="12s" repeatCount="indefinite"/>
        </circle>
        <path d="M -22 252 V 190 A 74 74 0 0 1 126 190 V 252 Z" fill="{PAPER}" opacity="0.58"/>
        <rect x="314" y="196" width="114" height="62" rx="31" fill="{SAGE}"/>""",
        motif_svg=f"""
        <polygon points="70,22 108,82 32,82" fill="none" stroke="{INK}" stroke-opacity="0.28" stroke-width="1.2"/>
        <circle cx="0" cy="0" r="3.2" fill="{INK}">
          <animateMotion dur="5.2s" repeatCount="indefinite" path="M 70,22 L 108,82 L 32,82 Z"/>
        </circle>
        <circle cx="70" cy="22" r="8" fill="{MARIGOLD}" stroke="{INK}" stroke-width="1"/>
        <circle cx="108" cy="82" r="8" fill="{CORAL_SOFT}" stroke="{INK}" stroke-width="1"/>
        <circle cx="32" cy="82" r="8" fill="{SKY}" stroke="{INK}" stroke-width="1"/>
        <text x="12" y="112" class="sans" font-size="8" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.2">20 COHORT 1 INTERNS</text>""",
    )

    # 6. ICARUS CUBESAT + HAWKEYE — Slate Sky #A6C3D6
    posters["poster-icarus.svg"] = render_poster_card(
        uid="icarus",
        name="ICARUS · KiboCUBE",
        year="2024–2026",
        line1="Calm,",
        line2="in orbit.",
        tagline1="1U CubeSat ADCS, B-dot & 7.4V EPS.",
        tagline2="UNOOSA / JAXA · 10/10 physics tests",
        footer="Sense, detumble, settle",
        bg=SKY_SLATE,
        bg_shapes_svg=f"""
        <circle cx="352" cy="112" r="98" fill="{PAPER}" opacity="0.58">
          <animateTransform attributeName="transform" type="translate" values="0,0; -6,6; 0,0" dur="10.5s" repeatCount="indefinite"/>
        </circle>
        <path d="M -20 252 V 192 A 68 68 0 0 1 116 192 V 252 Z" fill="{MARIGOLD}"/>
        <rect x="334" y="196" width="90" height="62" rx="10" fill="{CORAL_SOFT}"/>""",
        motif_svg=f"""
        <g transform="rotate(-16 70 54)">
          <ellipse cx="70" cy="54" rx="50" ry="20" fill="none" stroke="{INK}" stroke-opacity="0.34" stroke-width="1.1" stroke-dasharray="3 4"/>
          <circle cx="0" cy="0" r="4.5" fill="{CORAL}">
            <animateMotion dur="5.6s" repeatCount="indefinite" path="M 120,54 A 50,20 0 1,1 20,54 A 50,20 0 1,1 120,54"/>
          </circle>
        </g>
        <rect x="59" y="43" width="22" height="22" rx="3.5" fill="{PAPER}" stroke="{INK}" stroke-width="1.2" transform="rotate(14 70 54)"/>
        <circle cx="70" cy="54" r="3" fill="{INK}"/>
        <text x="12" y="112" class="sans" font-size="8" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.2">M × B UNDERACTUATED</text>""",
    )

    return posters


def generate_progress_ledger(metrics: dict, chrono: dict) -> str:
    contribs = metrics["total_contributions"]
    if contribs < 500:
        contrib_goal = max(200, int(math.ceil((contribs + 25) / 50.0) * 50))
        contrib_title = f"Public GitHub Contributions ({contribs:,} / {contrib_goal:,})"
        contrib_sub = f"{metrics['commits']:,} public commits · 1,073+ incl. private repos"
    else:
        contrib_goal = max(1200, int(math.ceil((contribs + 100) / 500.0) * 500))
        contrib_title = f"Annual GitHub Contributions ({contribs:,} / {contrib_goal:,})"
        contrib_sub = f"{metrics['commits']:,} commits · {metrics['active_days']} active days"
    contrib_pct = round(min(100.0, (contribs / contrib_goal) * 100.0), 1)

    pub_repos = metrics["public_repos"]
    repo_goal = max(25, int(math.ceil((pub_repos + 2) / 5.0) * 5))
    repo_pct = round(min(100.0, (pub_repos / repo_goal) * 100.0), 1)

    left_bars = [
        (f"Year Progress ({chrono['year']})", f"Day {chrono['day_of_year']} of {chrono['days_in_year']}", chrono["year_pct"], INK_NAVY, True),
        ("B.Tech ECE · MIT Bengaluru (2024–2028)", f"Semester {chrono['sem']} of 8 · AICTE National Merit Scholar", chrono["deg_pct"], INK_MUTED, True),
        (contrib_title, contrib_sub, contrib_pct, INK_TEAL, True),
        (f"Open-Source Repositories ({pub_repos} / {repo_goal})", f"{metrics['total_repos_note']}+ total repositories incl. private ventures", repo_pct, CORAL, True),
    ]

    right_bars = [
        ("TRACE · Neuro-Symbolic Security", "npm & PyPI · 0.261s audit · 250+ passing tests", 95.0, SEAGLASS, False),
        ("Your Space · Android Super-App", "14 Dart packages · 151 tests · Play Pre-Release", 92.0, LILAC, False),
        ("ICARUS · 1U CubeSat ADCS & EPS", "UNOOSA / JAXA KiboCUBE · 10/10 physics tests", 88.0, SKY, False),
        ("HAWKEYE · IAF Runway FOD Fusion", "76–81 GHz radar + 8 modalities · Aero India 2027", 82.0, CORAL_SOFT, False),
        ("Specular · EvenEi AI Glasses", "USD 1,000 seed · Google / Antler Immersion", 68.0, MARIGOLD, False),
    ]

    defs_parts = []
    bars_parts = []

    for i, (title, sub, pct, col, is_dark) in enumerate(left_bars):
        by = 128 + i * 74
        d, e = render_editorial_bar(
            uid=f"PL{i}",
            x=34,
            y=by + 23,
            width=390,
            height=13,
            pct=pct,
            fill_color=col,
            dark_fill=is_dark,
            hatch_dur=2.4 + i * 0.25,
            phase=i * 0.45,
        )
        defs_parts.append(d)
        bars_parts.append(f"""
    <text x="34" y="{by + 10}" class="sans" font-size="12.5" font-weight="600" fill="{INK}">{esc(title)}</text>
    <text x="424" y="{by + 10}" text-anchor="end" class="serif" font-size="15" font-style="italic" fill="{INK_MUTED}">{pct:.1f}%</text>
    {e}
    <text x="34" y="{by + 51}" class="sans" font-size="10.5" fill="{INK_SOFT}">{esc(sub)}</text>""")

    for i, (title, sub, pct, col, is_dark) in enumerate(right_bars):
        by = 128 + i * 68
        d, e = render_editorial_bar(
            uid=f"PR{i}",
            x=476,
            y=by + 22,
            width=390,
            height=13,
            pct=pct,
            fill_color=col,
            dark_fill=is_dark,
            hatch_dur=2.3 + i * 0.22,
            phase=0.25 + i * 0.4,
        )
        defs_parts.append(d)
        bars_parts.append(f"""
    <text x="476" y="{by + 9}" class="sans" font-size="12.5" font-weight="600" fill="{INK}">{esc(title)}</text>
    <text x="866" y="{by + 9}" text-anchor="end" class="serif" font-size="15" font-style="italic" fill="{INK_MUTED}">{int(pct)}%</text>
    {e}
    <text x="476" y="{by + 49}" class="sans" font-size="10.5" fill="{INK_SOFT}">{esc(sub)}</text>""")

    return f"""<svg width="900" height="498" viewBox="0 0 900 498" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Editorial architectural progress ledger — live year, degree, GitHub and flagship pipelines">
  <defs>
    <pattern id="hatchLight" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <line x1="0" y1="0" x2="0" y2="14" stroke="{PAPER}" stroke-width="2.2"/>
    </pattern>
    <pattern id="hatchInk" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <line x1="0" y1="0" x2="0" y2="14" stroke="{INK}" stroke-width="1.6"/>
    </pattern>
    {''.join(defs_parts)}
    <clipPath id="progClip">
      <rect x="1" y="1" width="898" height="496" rx="18"/>
    </clipPath>
    <style>
      .serif {{ font-family: Georgia, 'Palatino Linotype', 'Book Antiqua', 'Times New Roman', serif; }}
      .sans {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
      .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    </style>
  </defs>

  <g clip-path="url(#progClip)">
    <rect x="0" y="0" width="900" height="498" fill="{PAPER}"/>

    <!-- Editorial Header Band -->
    <text x="34" y="34" class="sans" font-size="10" font-weight="600" fill="{INK_MUTED}" letter-spacing="2">LIVE TELEMETRY · AUTO-SYNCED DAILY</text>
    <text x="34" y="68" class="serif" font-size="33" font-weight="400" fill="{INK}">Progress <tspan font-style="italic" fill="{CORAL}">&amp; pipelines</tspan></text>

    <!-- Crisp paper pill with breathing pine dot -->
    <g transform="translate(702, 34)">
      <rect x="0" y="0" width="164" height="28" rx="14" fill="{PAPER_DEEP}" stroke="{LINE_STRONG}" stroke-width="1"/>
      <circle cx="16" cy="14" r="3.5" fill="{INK_TEAL}">
        <animate attributeName="opacity" values="1;0.35;1" dur="2.4s" repeatCount="indefinite"/>
      </circle>
      <text x="28" y="17.5" class="mono" font-size="9.8" font-weight="600" fill="{INK_SOFT}">SYNCED · {esc(chrono['date_str'].upper())}</text>
    </g>

    <line x1="0" y1="86" x2="900" y2="86" stroke="{LINE}" stroke-width="1"/>
    <line x1="450" y1="86" x2="450" y2="498" stroke="{LINE}" stroke-width="1"/>

    <!-- Column headers -->
    <text x="34" y="112" class="sans" font-size="9.8" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.8">01  /  CHRONOLOGY &amp; GITHUB TARGETS</text>
    <text x="476" y="112" class="sans" font-size="9.8" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.8">02  /  ACTIVE BUILD PIPELINES</text>

    {''.join(bars_parts)}

    <!-- Bottom-left Architectural Waveform Plotter -->
    <line x1="34" y1="422" x2="424" y2="422" stroke="{LINE}" stroke-width="1"/>
    <g transform="translate(34, 434)">
      <rect x="0" y="0" width="136" height="44" rx="8" fill="{PAPER_DEEP}" stroke="{LINE_STRONG}" stroke-width="0.9"/>
      <line x1="10" y1="22" x2="126" y2="22" stroke="{INK}" stroke-opacity="0.14" stroke-width="0.8"/>
      <path d="M 10 22 C 22 6, 34 38, 46 22 C 58 10, 70 34, 82 22 C 94 14, 106 28, 118 22 L 126 22" fill="none" stroke="{INK}" stroke-width="1.25"/>
      <circle cx="0" cy="0" r="3" fill="{CORAL}">
        <animateMotion dur="4.2s" repeatCount="indefinite" path="M 10,22 C 22,6 34,38 46,22 C 58,10 70,34 82,22 C 94,14 106,28 118,22 L 126,22"/>
      </circle>
      <text x="150" y="18" class="sans" font-size="10.5" font-weight="600" fill="{INK}" letter-spacing="1.1">PEAK VELOCITY · {metrics['peak_day']} COMMITS / DAY</text>
      <text x="150" y="35" class="sans" font-size="10.5" fill="{INK_SOFT}">Refreshed daily via GitHub Actions GraphQL</text>
    </g>
  </g>

  <rect x="1" y="1" width="898" height="496" rx="18" stroke="{LINE_STRONG}" stroke-width="1"/>
</svg>
"""


def generate_craft_telemetry(metrics: dict) -> str:
    langs = metrics["languages"][:6]
    lang_notes = {
        "Python": "TRACE · HAWKEYE · Vetifi AI · ICARUS · FastAPI",
        "Dart": "Your Space · Stockie · Saral AI · Driftinn · Specular",
        "TypeScript": "EvenEi · TDC · AdSpace · MIT Bengaluru Portal",
        "HTML": "CubeSat EPS Simulation · Interfaces · Dashboards",
        "CSS": "Design Tokens · Responsive Layouts · Paper UI",
        "ShaderLab": "DroneController Unity FPV & Flight Physics",
        "JavaScript": "Three.js WebGL · Node.js · SquashDeck",
        "C++": "CubeSat B-Dot Controller · ESP32-S3 Firmware",
        "Jupyter Notebook": "ML Evaluation · SafeSpace Blind Benchmarks",
        "Kotlin": "Native Android MediaStore & Security Channels",
    }

    domains = [
        ("AI / ML, RAG & Computer Vision", "YOLO · DETR · Knowledge Graphs · LLMs", 95.0, SEAGLASS, False),
        ("Flutter, Dart & Mobile Systems", "Riverpod · Drift SQLite · Native Android", 93.0, SKY, False),
        ("Backend, FastAPI & Postgres RLS", "Supabase · Firebase · Node.js · Realtime", 92.0, SAGE, False),
        ("Full-Stack Web (React / TS / SSR)", "React 19 · React Router 7 · Next.js", 91.0, SAND, False),
        ("Security, AST & MCP Agents", "TRACE · Attack-Path Models · Android Sec", 90.0, ROSE, False),
        ("Embedded, C++ & Aerospace ADCS", "ESP32-S3 · I2C · CubeSat B-dot · OrCAD", 86.0, MARIGOLD, False),
    ]

    defs_parts = []
    bars_parts = []

    for i, (lang, pct) in enumerate(langs):
        col = LANG_PALETTE.get(lang, INK_TEAL)
        is_dark = col in (INK_NAVY, INK_TEAL, INK_MUTED, CORAL)
        note = lang_notes.get(lang, "Open-source & production systems")
        by = 128 + i * 52
        d, e = render_editorial_bar(
            uid=f"CL{i}",
            x=34,
            y=by + 20,
            width=390,
            height=11,
            pct=max(pct, 6.0),
            fill_color=col,
            dark_fill=is_dark,
            hatch_dur=2.5 + i * 0.2,
            phase=i * 0.35,
        )
        defs_parts.append(d)
        bars_parts.append(f"""
    <circle cx="40" cy="{by + 6}" r="4" fill="{col}" stroke="{INK}" stroke-opacity="0.25" stroke-width="0.8"/>
    <text x="51" y="{by + 10}" class="sans" font-size="12" font-weight="600" fill="{INK}">{esc(lang)}</text>
    <text x="424" y="{by + 10}" text-anchor="end" class="serif" font-size="14" font-style="italic" fill="{INK_MUTED}">{pct:.1f}%</text>
    {e}
    <text x="34" y="{by + 43}" class="sans" font-size="10" fill="{INK_SOFT}">{esc(note)}</text>""")

    for i, (dom, stack, pct, col, is_dark) in enumerate(domains):
        by = 128 + i * 52
        d, e = render_editorial_bar(
            uid=f"CD{i}",
            x=476,
            y=by + 20,
            width=390,
            height=11,
            pct=pct,
            fill_color=col,
            dark_fill=is_dark,
            hatch_dur=2.3 + i * 0.22,
            phase=0.3 + i * 0.35,
        )
        defs_parts.append(d)
        bars_parts.append(f"""
    <text x="476" y="{by + 9}" class="sans" font-size="12" font-weight="600" fill="{INK}">{esc(dom)}</text>
    <text x="866" y="{by + 9}" text-anchor="end" class="serif" font-size="14" font-style="italic" fill="{INK_MUTED}">{int(pct)}%</text>
    {e}
    <text x="476" y="{by + 43}" class="sans" font-size="10" fill="{INK_SOFT}">{esc(stack)}</text>""")

    # Amogh's signature CraftDial (SectionArt.jsx) rotating 5-petal pastel dial
    petals = [CORAL_SOFT, SKY, SAGE, LILAC, MARIGOLD]
    petal_svg = "".join(
        f'<g transform="rotate({i * 72} 0 0)"><rect x="-5" y="-23" width="10" height="17" rx="5" fill="{col}" opacity="0.88"/></g>'
        for i, col in enumerate(petals)
    )

    return f"""<svg width="900" height="456" viewBox="0 0 900 456" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Tools and craft — live GitHub languages and core engineering domains">
  <defs>
    <pattern id="hatchLight" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <line x1="0" y1="0" x2="0" y2="14" stroke="{PAPER}" stroke-width="2.2"/>
    </pattern>
    <pattern id="hatchInk" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <line x1="0" y1="0" x2="0" y2="14" stroke="{INK}" stroke-width="1.6"/>
    </pattern>
    {''.join(defs_parts)}
    <clipPath id="craftClip">
      <rect x="1" y="1" width="898" height="454" rx="18"/>
    </clipPath>
    <style>
      .serif {{ font-family: Georgia, 'Palatino Linotype', 'Book Antiqua', 'Times New Roman', serif; }}
      .sans {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
    </style>
  </defs>

  <g clip-path="url(#craftClip)">
    <rect x="0" y="0" width="900" height="456" fill="{PAPER}"/>

    <text x="34" y="34" class="sans" font-size="10" font-weight="600" fill="{INK_MUTED}" letter-spacing="2">REPO-WEIGHTED TELEMETRY &amp; DISCIPLINES</text>
    <text x="34" y="68" class="serif" font-size="33" font-weight="400" fill="{INK}">Tools <tspan font-style="italic" fill="{CORAL}">&amp; craft</tspan></text>

    <!-- Animated Craft Dial from SectionArt.jsx -->
    <g transform="translate(838, 44)">
      <circle cx="0" cy="0" r="28" fill="none" stroke="{INK}" stroke-opacity="0.16" stroke-width="1"/>
      <g>
        {petal_svg}
        <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="22s" repeatCount="indefinite"/>
      </g>
      <circle cx="0" cy="0" r="7" fill="{PAPER}" stroke="{INK}" stroke-width="1"/>
      <circle cx="0" cy="0" r="2" fill="{INK}"/>
    </g>

    <line x1="0" y1="86" x2="900" y2="86" stroke="{LINE}" stroke-width="1"/>
    <line x1="450" y1="86" x2="450" y2="456" stroke="{LINE}" stroke-width="1"/>

    <text x="34" y="112" class="sans" font-size="9.8" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.8">LIVE GITHUB LANGUAGES (PUBLIC REPOS)</text>
    <text x="476" y="112" class="sans" font-size="9.8" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.8">CORE SYSTEMS DOMAINS</text>

    {''.join(bars_parts)}
  </g>

  <rect x="1" y="1" width="898" height="454" rx="18" stroke="{LINE_STRONG}" stroke-width="1"/>
</svg>
"""


def generate_footer_horizon() -> str:
    """Editorial Horizon Sculpture footer straight from SectionArt.jsx."""
    return f"""<svg width="900" height="184" viewBox="0 0 900 184" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Amogh V K editorial horizon footer">
  <defs>
    <clipPath id="footClip">
      <rect x="1" y="1" width="898" height="182" rx="18"/>
    </clipPath>
    <style>
      .serif {{ font-family: Georgia, 'Palatino Linotype', 'Book Antiqua', 'Times New Roman', serif; }}
      .sans {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
    </style>
  </defs>

  <g clip-path="url(#footClip)">
    <rect x="0" y="0" width="900" height="184" fill="{PAPER}"/>

    <!-- Left: Horizon Sculpture (SectionArt.jsx) -->
    <g transform="translate(128, 96)">
      <circle cx="0" cy="0" r="58" fill="none" stroke="{INK}" stroke-opacity="0.16" stroke-width="1" stroke-dasharray="2 6">
        <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="36s" repeatCount="indefinite"/>
      </circle>
      <path d="M -46 18 A 46 46 0 0 1 46 18 Z" fill="{CORAL_SOFT}">
        <animateTransform attributeName="transform" type="translate" values="0,0; 0,-4; 0,0" dur="5.5s" repeatCount="indefinite"/>
      </path>
      <circle cx="38" cy="-34" r="16" fill="{MARIGOLD}">
        <animateTransform attributeName="transform" type="translate" values="0,0; 0,5; 0,0" dur="4.8s" repeatCount="indefinite"/>
      </circle>
      <line x1="-60" y1="18" x2="60" y2="18" stroke="{INK}" stroke-opacity="0.38" stroke-width="1"/>
      <rect x="-42" y="27" width="84" height="8" rx="4" fill="{SKY}"/>
      <rect x="-26" y="40" width="52" height="8" rx="4" fill="{SAGE}"/>
    </g>

    <line x1="256" y1="24" x2="256" y2="160" stroke="{LINE}" stroke-width="1"/>

    <!-- Right: Editorial Quote & Colophon -->
    <text x="292" y="48" class="sans" font-size="9.5" font-weight="600" fill="{INK_MUTED}" letter-spacing="2">COLOPHON · QUIET STUDIO</text>
    <text x="292" y="88" class="serif" font-size="24" font-style="italic" fill="{INK}">“What people find boring, is what interests me.”</text>
    <text x="292" y="116" class="sans" font-size="13" fill="{INK_SOFT}">Engineering intelligent systems quietly, rigorously, and end to end.</text>

    <line x1="292" y1="136" x2="864" y2="136" stroke="{LINE}" stroke-width="1"/>
    <text x="292" y="156" class="sans" font-size="9.5" font-weight="600" fill="{INK_SOFT}" letter-spacing="1.8">AMOGH V K  ·  EVENEI  ·  THE DEVELOPER COMMUNITY</text>
    <text x="864" y="156" text-anchor="end" class="sans" font-size="9.5" font-weight="600" fill="{INK_MUTED}" letter-spacing="1.6">BENGALURU · 12.97° N</text>
  </g>

  <rect x="1" y="1" width="898" height="182" rx="18" stroke="{LINE_STRONG}" stroke-width="1"/>
</svg>
"""


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    metrics = fetch_github_data()
    chrono = compute_chronology(now)

    outputs: dict[str, str] = {
        "hero-editorial.svg": generate_hero_editorial(metrics),
        "editorial-rule.svg": generate_editorial_rule(),
        "progress-ledger.svg": generate_progress_ledger(metrics, chrono),
        "craft-telemetry.svg": generate_craft_telemetry(metrics),
        "footer-horizon.svg": generate_footer_horizon(),
    }
    outputs.update(generate_posters())

    for filename, content in outputs.items():
        path = ASSETS_DIR / filename
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path.name} ({len(content):,} bytes)")


if __name__ == "__main__":
    main()
