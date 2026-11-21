#!/usr/bin/env python3
"""
Generate bespoke animated SVG telemetry assets for VK-Amogh's GitHub profile.
Uses Python stdlib only so GitHub Actions stays fast and dependency-free.
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

LANG_COLORS = {
    "Python": ("#38BDF8", "#2563EB"),
    "Dart": ("#2DD4BF", "#0D9488"),
    "TypeScript": ("#60A5FA", "#3B82F6"),
    "JavaScript": ("#FBBF24", "#D97706"),
    "C++": ("#F472B6", "#DB2777"),
    "C": ("#A78BFA", "#7C3AED"),
    "HTML": ("#FB923C", "#EA580C"),
    "CSS": ("#C084FC", "#9333EA"),
    "ShaderLab": ("#34D399", "#059669"),
    "Jupyter Notebook": ("#F59E0B", "#B45309"),
    "Kotlin": ("#A78BFA", "#6D28D9"),
    "Java": ("#FB7185", "#E11D48"),
    "PLpgSQL": ("#22D3EE", "#0891B2"),
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
            "User-Agent": "VK-Amogh-Profile-Generator",
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

    # Repo-weighted language share so one repo with large data files doesn't skew everything
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

    # B.Tech ECE at MIT Bengaluru: Aug 1, 2024 -> May 31, 2028
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
        "date_str": now.strftime("%Y-%m-%d UTC"),
    }


def render_animated_bar(
    uid: str,
    x: float,
    y: float,
    width: float,
    height: float,
    pct: float,
    c1: str,
    c2: str,
    delay: float = 0.0,
    shimmer_dur: float = 3.0,
    shimmer_offset: float = 0.0,
) -> tuple[str, str]:
    """Return (defs_snippet, elements_snippet) for a kinetic animated progress bar."""
    clamped = max(5.0, min(100.0, pct))
    fill_w = round(width * (clamped / 100.0), 2)
    rx = round(height / 2.0, 2)
    tip_cx = round(x + fill_w - max(2.5, rx * 0.55), 2)
    tip_cy = round(y + height / 2.0, 2)

    defs = f"""
    <linearGradient id="grad_{uid}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <clipPath id="clip_{uid}">
      <rect x="{x}" y="{y}" width="{fill_w}" height="{height}" rx="{rx}"/>
    </clipPath>"""

    # Telemetry tick marks at 25%, 50%, 75%
    t25 = round(x + width * 0.25, 1)
    t50 = round(x + width * 0.50, 1)
    t75 = round(x + width * 0.75, 1)

    shimmer_w = max(68.0, round(width * 0.30, 1))
    s_from = round(x - shimmer_w - 14, 1)
    s_to = round(x + fill_w + 26, 1)
    stripe_dur = round(1.15 + (shimmer_offset % 0.4), 2)

    elems = f"""
    <g>
      <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{rx}" fill="#0F172A" stroke="#1E293B" stroke-width="1"/>
      <line x1="{t25}" y1="{y + 1.5}" x2="{t25}" y2="{y + height - 1.5}" stroke="#1E293B" stroke-width="1"/>
      <line x1="{t50}" y1="{y + 1.5}" x2="{t50}" y2="{y + height - 1.5}" stroke="#1E293B" stroke-width="1"/>
      <line x1="{t75}" y1="{y + 1.5}" x2="{t75}" y2="{y + height - 1.5}" stroke="#1E293B" stroke-width="1"/>
      <g clip-path="url(#clip_{uid})">
        <rect x="{x}" y="{y}" width="{fill_w}" height="{height}" rx="{rx}" fill="url(#grad_{uid})"/>
        <rect x="{x - 24}" y="{y}" width="{fill_w + 48}" height="{height}" fill="url(#kineticStripes)" opacity="0.26">
          <animateTransform attributeName="transform" type="translate" from="0 0" to="20 0" dur="{stripe_dur:.2f}s" repeatCount="indefinite"/>
        </rect>
        <rect x="{x}" y="{y}" width="{fill_w}" height="{round(height * 0.42, 2)}" fill="#FFFFFF" opacity="0.16"/>
        <rect x="{s_from}" y="{y - 2}" width="{shimmer_w}" height="{height + 4}" fill="url(#barShimmer)" opacity="0.88">
          <animate attributeName="x" from="{s_from}" to="{s_to}" begin="{shimmer_offset:.2f}s" dur="{shimmer_dur:.2f}s" repeatCount="indefinite"/>
        </rect>
      </g>
      <circle cx="{tip_cx}" cy="{tip_cy}" r="{round(height * 0.65, 2)}" fill="{c2}" opacity="0.34">
        <animate attributeName="opacity" values="0.14;0.55;0.14" begin="{shimmer_offset:.2f}s" dur="2.1s" repeatCount="indefinite"/>
        <animate attributeName="r" values="{round(height * 0.45, 2)};{round(height * 0.92, 2)};{round(height * 0.45, 2)}" begin="{shimmer_offset:.2f}s" dur="2.1s" repeatCount="indefinite"/>
      </circle>
      <circle cx="{tip_cx}" cy="{tip_cy}" r="{round(height * 0.30, 2)}" fill="#FFFFFF" opacity="0.94">
        <animate attributeName="opacity" values="0.62;1;0.62" begin="{shimmer_offset:.2f}s" dur="2.1s" repeatCount="indefinite"/>
      </circle>
    </g>"""
    return defs, elems


def generate_hero_banner() -> str:
    return """<svg width="900" height="278" viewBox="0 0 900 278" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Amogh V K — Systems, AI, Security, Flutter, and Aerospace Engineer">
  <defs>
    <linearGradient id="heroBg" x1="0" y1="0" x2="900" y2="278" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#090D16"/>
      <stop offset="55%" stop-color="#0E1525"/>
      <stop offset="100%" stop-color="#111A2E"/>
    </linearGradient>
    <radialGradient id="glowTeal" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(170 60) rotate(25) scale(340 210)">
      <stop offset="0%" stop-color="#14B8A6" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#14B8A6" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowSky" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(765 138) rotate(-15) scale(220 180)">
      <stop offset="0%" stop-color="#38BDF8" stop-opacity="0.18"/>
      <stop offset="65%" stop-color="#A78BFA" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="#090D16" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="nameGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#F8FAFC"/>
      <stop offset="38%" stop-color="#E2E8F0"/>
      <stop offset="50%" stop-color="#5EEAD4"/>
      <stop offset="62%" stop-color="#E2E8F0"/>
      <stop offset="100%" stop-color="#F8FAFC"/>
      <animate attributeName="x1" values="-100%;100%" dur="5.5s" repeatCount="indefinite"/>
      <animate attributeName="x2" values="0%;200%" dur="5.5s" repeatCount="indefinite"/>
    </linearGradient>
    <linearGradient id="railBeam" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#14B8A6" stop-opacity="0"/>
      <stop offset="30%" stop-color="#14B8A6" stop-opacity="0.9"/>
      <stop offset="65%" stop-color="#38BDF8" stop-opacity="1"/>
      <stop offset="88%" stop-color="#F59E0B" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="#F59E0B" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="radarSweep" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#14B8A6" stop-opacity="0.48"/>
      <stop offset="100%" stop-color="#14B8A6" stop-opacity="0"/>
    </linearGradient>
    <pattern id="dotGrid" width="24" height="24" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="#334155" opacity="0.35"/>
    </pattern>
    <clipPath id="heroClip">
      <rect x="1" y="1" width="898" height="276" rx="16"/>
    </clipPath>
    <style>
      .mono { font-family: 'Cascadia Code', 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
      .sans { font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; }
    </style>
  </defs>

  <g clip-path="url(#heroClip)">
    <rect x="0" y="0" width="900" height="278" fill="url(#heroBg)"/>
    <rect x="0" y="0" width="900" height="278" fill="url(#dotGrid)"/>
    <rect x="0" y="0" width="900" height="278" fill="url(#glowTeal)"/>
    <rect x="0" y="0" width="900" height="278" fill="url(#glowSky)"/>

    <!-- Subtle aerospace technical hairlines -->
    <line x1="0" y1="54" x2="900" y2="54" stroke="#1E293B" stroke-width="1" opacity="0.65"/>
    <line x1="636" y1="0" x2="636" y2="278" stroke="#1E293B" stroke-width="1" stroke-dasharray="4 6" opacity="0.55"/>

    <!-- Top telemetry strip -->
    <g transform="translate(34, 16)">
      <rect x="0" y="0" width="268" height="23" rx="11.5" fill="#0F1D2C" stroke="#1E3A5F" stroke-width="1"/>
      <circle cx="15" cy="11.5" r="4" fill="#10B981">
        <animate attributeName="opacity" values="1;0.3;1" dur="1.8s" repeatCount="indefinite"/>
      </circle>
      <circle cx="15" cy="11.5" r="7" fill="#10B981" opacity="0.25">
        <animate attributeName="r" values="4;9;4" dur="1.8s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.35;0;0.35" dur="1.8s" repeatCount="indefinite"/>
      </circle>
      <text x="28" y="15" class="mono" font-size="10.5" font-weight="600" fill="#5EEAD4" letter-spacing="0.8">SYSTEMS ONLINE · BENGALURU, IN</text>
    </g>

    <text x="866" y="31" text-anchor="end" class="mono" font-size="10.5" fill="#64748B" letter-spacing="1.2">ORBITAL // AI // SECURITY // MOBILE</text>

    <!-- Main Hero Typography -->
    <text x="34" y="124" class="sans" font-size="50" font-weight="800" fill="url(#nameGrad)" letter-spacing="1.5">AMOGH V K</text>

    <text x="36" y="156" class="sans" font-size="16" font-weight="500" fill="#CBD5E1">
      Software, AI &amp; Agents, Security, Flutter &amp; Aerospace Systems Engineer
    </text>

    <text x="36" y="182" class="mono" font-size="11.5" fill="#94A3B8">
      From ESP32 firmware &amp; CubeSat ADCS to agentic AI, security &amp; Flutter systems.
    </text>

    <!-- Structured Credential Pills (generous width, zero overlap) -->
    <g transform="translate(34, 208)">
      <rect x="0" y="0" width="174" height="28" rx="7" fill="#132238" stroke="#1E3A5F" stroke-width="1"/>
      <circle cx="13" cy="14" r="3" fill="#F59E0B"/>
      <text x="23" y="18" class="mono" font-size="10" font-weight="600" fill="#FDE68A">Founder · EvenEi &amp; TDC</text>

      <rect x="182" y="0" width="122" height="28" rx="7" fill="#1F1522" stroke="#4C1D3D" stroke-width="1"/>
      <circle cx="195" cy="14" r="3" fill="#FB7185"/>
      <text x="205" y="18" class="mono" font-size="10" font-weight="600" fill="#FECDD3">IAF · HAWKEYE</text>

      <rect x="312" y="0" width="146" height="28" rx="7" fill="#0F2429" stroke="#155E75" stroke-width="1"/>
      <circle cx="325" cy="14" r="3" fill="#2DD4BF"/>
      <text x="335" y="18" class="mono" font-size="10" font-weight="600" fill="#99F6E4">UNOOSA / KiboCUBE</text>

      <rect x="466" y="0" width="126" height="28" rx="7" fill="#1A1833" stroke="#3B3278" stroke-width="1"/>
      <circle cx="479" cy="14" r="3" fill="#A78BFA"/>
      <text x="489" y="18" class="mono" font-size="10" font-weight="600" fill="#DDD6FE">Google GSA '26</text>
    </g>

    <!-- Right-side Animated Orbital CubeSat + Radar Telemetry Display -->
    <g transform="translate(768, 160)">
      <circle cx="0" cy="0" r="82" stroke="#1E293B" stroke-width="1" stroke-dasharray="3 5"/>
      <circle cx="0" cy="0" r="57" stroke="#1E3A5F" stroke-width="1" opacity="0.85"/>
      <circle cx="0" cy="0" r="31" stroke="#14B8A6" stroke-width="1" stroke-dasharray="2 4" opacity="0.55"/>
      <line x1="-88" y1="0" x2="88" y2="0" stroke="#1E293B" stroke-width="1" opacity="0.6"/>
      <line x1="0" y1="-88" x2="0" y2="88" stroke="#1E293B" stroke-width="1" opacity="0.6"/>

      <!-- Rotating radar sweep sector -->
      <g>
        <path d="M 0 0 L 0 -80 A 80 80 0 0 1 63 -49 Z" fill="url(#radarSweep)"/>
        <line x1="0" y1="0" x2="0" y2="-80" stroke="#2DD4BF" stroke-width="1.4" opacity="0.8"/>
        <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="8s" repeatCount="indefinite"/>
      </g>

      <!-- Tilted CubeSat orbital ring -->
      <g transform="rotate(-24)">
        <ellipse cx="0" cy="0" rx="76" ry="27" stroke="#38BDF8" stroke-width="1.2" stroke-opacity="0.45" stroke-dasharray="5 4"/>
        <circle cx="0" cy="0" r="4.5" fill="#FBBF24">
          <animateMotion dur="6.5s" repeatCount="indefinite" path="M 76,0 A 76,27 0 1,1 -76,0 A 76,27 0 1,1 76,0"/>
        </circle>
        <circle cx="0" cy="0" r="9" fill="#FBBF24" opacity="0.28">
          <animateMotion dur="6.5s" repeatCount="indefinite" path="M 76,0 A 76,27 0 1,1 -76,0 A 76,27 0 1,1 76,0"/>
        </circle>
      </g>

      <!-- Secondary counter-orbiting node -->
      <g transform="rotate(32)">
        <ellipse cx="0" cy="0" rx="58" ry="20" stroke="#A78BFA" stroke-width="1" stroke-opacity="0.35"/>
        <circle cx="0" cy="0" r="3" fill="#38BDF8">
          <animateMotion dur="9s" repeatCount="indefinite" path="M -58,0 A 58,20 0 1,0 58,0 A 58,20 0 1,0 -58,0"/>
        </circle>
      </g>

      <!-- Core node -->
      <circle cx="0" cy="0" r="10.5" fill="#0F172A" stroke="#14B8A6" stroke-width="1.8"/>
      <circle cx="0" cy="0" r="4" fill="#5EEAD4">
        <animate attributeName="opacity" values="1;0.35;1" dur="2.1s" repeatCount="indefinite"/>
      </circle>

      <!-- Radar ping targets -->
      <circle cx="38" cy="-31" r="2.6" fill="#FB7185">
        <animate attributeName="opacity" values="0.15;1;0.15" dur="4s" begin="0.8s" repeatCount="indefinite"/>
      </circle>
      <circle cx="-44" cy="25" r="2.6" fill="#38BDF8">
        <animate attributeName="opacity" values="0.15;1;0.15" dur="4s" begin="2.4s" repeatCount="indefinite"/>
      </circle>

      <text x="0" y="99" text-anchor="middle" class="mono" font-size="9.5" fill="#64748B" letter-spacing="1.4">ADCS // B-DOT // FOD-FUSION</text>
    </g>

    <!-- Bottom continuous animated scanning progress rail -->
    <rect x="0" y="274" width="900" height="4" fill="#162032"/>
    <rect x="-260" y="274" width="260" height="4" fill="url(#railBeam)">
      <animate attributeName="x" from="-260" to="920" dur="3.4s" repeatCount="indefinite"/>
    </rect>
  </g>

  <rect x="1" y="1" width="898" height="276" rx="16" stroke="#243247" stroke-width="1.2"/>
</svg>
"""


def generate_divider() -> str:
    return """<svg width="900" height="18" viewBox="0 0 900 18" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated section divider">
  <defs>
    <linearGradient id="divBeam" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#14B8A6" stop-opacity="0"/>
      <stop offset="35%" stop-color="#14B8A6" stop-opacity="0.95"/>
      <stop offset="65%" stop-color="#38BDF8" stop-opacity="1"/>
      <stop offset="88%" stop-color="#F59E0B" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="#F59E0B" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="divClip">
      <rect x="0" y="7" width="900" height="4" rx="2"/>
    </clipPath>
  </defs>
  <rect x="0" y="8" width="900" height="2" rx="1" fill="#1E293B"/>
  <g clip-path="url(#divClip)">
    <rect x="-220" y="7" width="220" height="4" fill="url(#divBeam)">
      <animate attributeName="x" from="-220" to="920" dur="3.8s" repeatCount="indefinite"/>
    </rect>
  </g>
  <polygon points="450,3 456,9 450,15 444,9" fill="#0F172A" stroke="#14B8A6" stroke-width="1.2"/>
  <circle cx="450" cy="9" r="2" fill="#5EEAD4">
    <animate attributeName="opacity" values="0.35;1;0.35" dur="2.2s" repeatCount="indefinite"/>
  </circle>
</svg>
"""


def generate_terminal_card(metrics: dict) -> str:
    contribs = f"{metrics['total_contributions']:,}+"
    kpis = [
        (contribs, "GitHub Contribs (1Y)", "#14B8A6", "#0F2929"),
        ("10,000+", "Vets via Vetifi AI", "#38BDF8", "#0E2235"),
        ("1,000+", "TDC Builders (5+ Univ)", "#A78BFA", "#1C1836"),
        ("0.261s", "TRACE 189-File Audit", "#2DD4BF", "#0E2926"),
        ("96.23%", "RAG Eval Accuracy", "#FBBF24", "#2B2110"),
        ("70%", "Faster MIT KPI Sync", "#FB7185", "#2B141F"),
    ]

    kpi_svg = []
    for idx, (val, label, accent, tint) in enumerate(kpis):
        col = idx % 2
        row = idx // 2
        kx = 576 + col * 156
        ky = 58 + row * 74
        delay = 0.2 * idx
        kpi_svg.append(f"""
    <g transform="translate({kx}, {ky})">
      <rect x="0" y="0" width="146" height="64" rx="10" fill="{tint}" stroke="#243247" stroke-width="1"/>
      <rect x="0" y="0" width="146" height="3" rx="1.5" fill="{accent}" opacity="0.85">
        <animate attributeName="opacity" values="0.45;1;0.45" begin="{delay:.1f}s" dur="3.0s" repeatCount="indefinite"/>
      </rect>
      <text x="13" y="31" class="sans" font-size="20" font-weight="800" fill="#F8FAFC">{esc(val)}</text>
      <text x="13" y="50" class="mono" font-size="9.2" fill="#94A3B8">{esc(label)}</text>
    </g>""")

    return f"""<svg width="900" height="296" viewBox="0 0 900 296" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Amogh V K developer terminal and verified impact telemetry">
  <defs>
    <linearGradient id="termBg" x1="0" y1="0" x2="900" y2="296" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0B1120"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <style>
      .mono {{ font-family: 'Cascadia Code', 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
      .sans {{ font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; }}
    </style>
  </defs>

  <rect x="1" y="1" width="898" height="294" rx="14" fill="url(#termBg)" stroke="#243247" stroke-width="1.2"/>

  <!-- Left Terminal Window (generous 546px width) -->
  <rect x="14" y="14" width="546" height="268" rx="11" fill="#090D16" stroke="#1E293B" stroke-width="1"/>
  <path d="M 14 25 A 11 11 0 0 1 25 14 L 549 14 A 11 11 0 0 1 560 25 L 560 44 L 14 44 Z" fill="#131B2E"/>
  <line x1="14" y1="44" x2="560" y2="44" stroke="#1E293B" stroke-width="1"/>
  <circle cx="32" cy="29" r="5" fill="#EF4444"/>
  <circle cx="48" cy="29" r="5" fill="#F59E0B"/>
  <circle cx="64" cy="29" r="5" fill="#10B981"/>
  <text x="287" y="33" text-anchor="middle" class="mono" font-size="10.8" fill="#64748B">amogh@evenei:~/systems — zsh</text>

  <!-- Terminal Body (sized cleanly to stay well inside 560px) -->
  <g class="mono" font-size="10.6">
    <text x="28" y="69">
      <tspan fill="#14B8A6">➜</tspan>
      <tspan fill="#38BDF8"> ~/systems</tspan>
      <tspan fill="#E2E8F0"> cat identity.json</tspan>
    </text>

    <text x="28" y="92" fill="#64748B">{{</text>
    <text x="40" y="112"><tspan fill="#38BDF8">"ventures"</tspan><tspan fill="#94A3B8">: </tspan><tspan fill="#FDE68A">["EvenEi (Specular)", "The Developer Community"]</tspan><tspan fill="#64748B">,</tspan></text>
    <text x="40" y="132"><tspan fill="#38BDF8">"defense_space"</tspan><tspan fill="#94A3B8">: </tspan><tspan fill="#5EEAD4">["IAF (HAWKEYE)", "UNOOSA / JAXA KiboCUBE"]</tspan><tspan fill="#64748B">,</tspan></text>
    <text x="40" y="152"><tspan fill="#38BDF8">"engineering"</tspan><tspan fill="#94A3B8">: </tspan><tspan fill="#DDD6FE">["Vetifi AI (10k+ vets)", "MIT BLR Data Systems"]</tspan><tspan fill="#64748B">,</tspan></text>
    <text x="40" y="172"><tspan fill="#38BDF8">"education"</tspan><tspan fill="#94A3B8">: </tspan><tspan fill="#CBD5E1">"B.Tech ECE · MIT Bengaluru · AICTE Scholar"</tspan><tspan fill="#64748B">,</tspan></text>
    <text x="40" y="192"><tspan fill="#38BDF8">"principle"</tspan><tspan fill="#94A3B8">: </tspan><tspan fill="#86EFAC">"Deterministic verification · Systems over demos"</tspan><tspan fill="#64748B">,</tspan></text>
    <text x="40" y="212"><tspan fill="#38BDF8">"motto"</tspan><tspan fill="#94A3B8">: </tspan><tspan fill="#FECDD3">"What people find boring, is what interests me."</tspan></text>
    <text x="28" y="232" fill="#64748B">}}</text>

    <text x="28" y="261">
      <tspan fill="#14B8A6">➜</tspan>
      <tspan fill="#38BDF8"> ~/systems</tspan>
      <tspan fill="#E2E8F0"> ./ship --verify=deterministic --stage=prod</tspan>
    </text>
    <rect x="387" y="249" width="8" height="14.5" rx="1.5" fill="#14B8A6">
      <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.49;0.5;1" dur="1.05s" repeatCount="indefinite"/>
    </rect>
  </g>

  <!-- Right KPI Header -->
  <text x="576" y="36" class="mono" font-size="11.5" font-weight="700" fill="#CBD5E1" letter-spacing="1.2">VERIFIED IMPACT METRICS</text>
  <circle cx="874" cy="32" r="4" fill="#14B8A6">
    <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/>
  </circle>

  {''.join(kpi_svg)}
</svg>
"""


def generate_progress_bars(metrics: dict, chrono: dict) -> str:
    contribs = metrics["total_contributions"]
    contrib_goal = max(1200, int(math.ceil((contribs + 100) / 500.0) * 500))
    contrib_pct = round(min(100.0, (contribs / contrib_goal) * 100.0), 1)

    pub_repos = metrics["public_repos"]
    repo_goal = max(25, int(math.ceil((pub_repos + 2) / 5.0) * 5))
    repo_pct = round(min(100.0, (pub_repos / repo_goal) * 100.0), 1)

    left_bars = [
        (
            f"Year Progress ({chrono['year']})",
            f"Day {chrono['day_of_year']} / {chrono['days_in_year']}",
            chrono["year_pct"],
            "#0EA5E9",
            "#38BDF8",
        ),
        (
            "B.Tech ECE · MIT Bengaluru (2024–2028)",
            f"Semester {chrono['sem']} / 8 · AICTE Scholar",
            chrono["deg_pct"],
            "#8B5CF6",
            "#A78BFA",
        ),
        (
            f"Annual GitHub Contributions ({contribs:,} / {contrib_goal:,})",
            f"{metrics['commits']:,} commits · {metrics['active_days']} active days",
            contrib_pct,
            "#0D9488",
            "#2DD4BF",
        ),
        (
            f"Open-Source Repositories ({pub_repos} / {repo_goal})",
            f"{metrics['total_repos_note']}+ total repos incl. private ventures",
            repo_pct,
            "#D97706",
            "#FBBF24",
        ),
    ]

    right_bars = [
        ("TRACE · Neuro-Symbolic Security Scanner", "npm & PyPI · 0.261s · 250+ Tests", 95.0, "#0D9488", "#2DD4BF"),
        ("Your Space · Android Media Super-App", "14 Packages · 151 Tests · Play Pre-Release", 92.0, "#2563EB", "#38BDF8"),
        ("ICARUS · 1U CubeSat ADCS & EPS", "UNOOSA / JAXA KiboCUBE · 10/10 Physics", 88.0, "#7C3AED", "#A78BFA"),
        ("HAWKEYE · IAF Runway FOD Fusion", "76–81 GHz Radar + 8 Cams · Aero India '27", 82.0, "#E11D48", "#FB7185"),
        ("Specular · EvenEi AI Smart Glasses", "$1K Seed Funded · Google/Antler Immersion", 68.0, "#D97706", "#FBBF24"),
    ]

    defs_parts = []
    bars_parts = []

    # Left column bars
    for i, (title, sub, pct, c1, c2) in enumerate(left_bars):
        by = 102 + i * 72
        d, e = render_animated_bar(
            uid=f"L{i}",
            x=32,
            y=by + 21,
            width=392,
            height=13,
            pct=pct,
            c1=c1,
            c2=c2,
            delay=0.10 * i,
            shimmer_dur=3.0 + i * 0.25,
            shimmer_offset=0.4 * i,
        )
        defs_parts.append(d)
        bars_parts.append(f"""
    <text x="32" y="{by + 11}" class="sans" font-size="12.5" font-weight="600" fill="#F1F5F9">{esc(title)}</text>
    <text x="424" y="{by + 11}" text-anchor="end" class="mono" font-size="12" font-weight="700" fill="{c2}">{pct:.1f}%</text>
    {e}
    <text x="32" y="{by + 50}" class="mono" font-size="10" fill="#64748B">{esc(sub)}</text>""")

    # Right column bars
    for i, (title, sub, pct, c1, c2) in enumerate(right_bars):
        by = 102 + i * 68
        d, e = render_animated_bar(
            uid=f"R{i}",
            x=476,
            y=by + 20,
            width=392,
            height=12,
            pct=pct,
            c1=c1,
            c2=c2,
            delay=0.12 + 0.10 * i,
            shimmer_dur=2.8 + i * 0.22,
            shimmer_offset=0.35 * i + 0.2,
        )
        defs_parts.append(d)
        bars_parts.append(f"""
    <text x="476" y="{by + 10}" class="sans" font-size="12.5" font-weight="600" fill="#F1F5F9">{esc(title)}</text>
    <text x="868" y="{by + 10}" text-anchor="end" class="mono" font-size="12" font-weight="700" fill="{c2}">{int(pct)}%</text>
    {e}
    <text x="476" y="{by + 47}" class="mono" font-size="10" fill="#64748B">{esc(sub)}</text>""")

    # Animated mini heartbeat equalizer bars in bottom-left telemetry widget
    eq_bars = []
    eq_heights = [8, 16, 11, 20, 14, 18, 9, 22, 13, 17, 10, 19, 12, 15]
    for j, h in enumerate(eq_heights):
        ex = 32 + j * 9
        dur = 1.1 + (j % 5) * 0.28
        eq_bars.append(
            f'<rect x="{ex}" y="{424 - h}" width="5" height="{h}" rx="2.5" fill="#14B8A6" opacity="0.88">'
            f'<animate attributeName="height" values="{max(4, h - 8)};{h + 4};{max(5, h - 6)}" dur="{dur:.2f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{424 - max(4, h - 8)};{424 - (h + 4)};{424 - max(5, h - 6)}" dur="{dur:.2f}s" repeatCount="indefinite"/>'
            f"</rect>"
        )

    return f"""<svg width="900" height="470" viewBox="0 0 900 470" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated live progress bars for year progress, degree, GitHub goals, and flagship projects">
  <defs>
    <linearGradient id="progBg" x1="0" y1="0" x2="900" y2="470" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0B1120"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="barShimmer" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0"/>
      <stop offset="45%" stop-color="#FFFFFF" stop-opacity="0.48"/>
      <stop offset="55%" stop-color="#FFFFFF" stop-opacity="0.62"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
    <pattern id="kineticStripes" width="20" height="20" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect x="0" y="0" width="8" height="20" fill="#FFFFFF" opacity="0.55"/>
    </pattern>
    {''.join(defs_parts)}
    <style>
      .mono {{ font-family: 'Cascadia Code', 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
      .sans {{ font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; }}
    </style>
  </defs>

  <rect x="1" y="1" width="898" height="468" rx="14" fill="url(#progBg)" stroke="#243247" stroke-width="1.2"/>

  <!-- Header Bar -->
  <path d="M 1 15 A 14 14 0 0 1 15 1 L 885 1 A 14 14 0 0 1 899 15 L 899 54 L 1 54 Z" fill="#121B2E"/>
  <line x1="1" y1="54" x2="899" y2="54" stroke="#1E293B" stroke-width="1"/>
  <text x="28" y="33" class="mono" font-size="13" font-weight="700" fill="#F8FAFC" letter-spacing="1.3">LIVE PROGRESS TELEMETRY &amp; ACTIVE MISSIONS</text>

  <!-- Auto-sync Live Pill -->
  <g transform="translate(658, 15)">
    <rect x="0" y="0" width="218" height="24" rx="12" fill="#0B2426" stroke="#14B8A6" stroke-width="1" stroke-opacity="0.5"/>
    <circle cx="14" cy="12" r="3.5" fill="#14B8A6">
      <animate attributeName="opacity" values="1;0.25;1" dur="1.7s" repeatCount="indefinite"/>
    </circle>
    <text x="25" y="15.5" class="mono" font-size="10" font-weight="600" fill="#5EEAD4">AUTO-SYNC · {esc(chrono['date_str'])}</text>
  </g>

  <!-- Sub-panels -->
  <rect x="16" y="68" width="424" height="384" rx="11" fill="#0A0F1D" stroke="#1E293B" stroke-width="1"/>
  <rect x="460" y="68" width="424" height="384" rx="11" fill="#0A0F1D" stroke="#1E293B" stroke-width="1"/>

  <text x="32" y="89" class="mono" font-size="10.5" font-weight="700" fill="#38BDF8" letter-spacing="1.2">01 // CHRONOLOGY &amp; GITHUB TARGETS</text>
  <text x="476" y="89" class="mono" font-size="10.5" font-weight="700" fill="#2DD4BF" letter-spacing="1.2">02 // FLAGSHIP BUILD PIPELINES</text>

  {''.join(bars_parts)}

  <!-- Bottom-left Live Velocity Strip -->
  <line x1="32" y1="390" x2="424" y2="390" stroke="#1E293B" stroke-width="1"/>
  {''.join(eq_bars)}
  <text x="172" y="411" class="mono" font-size="10.5" font-weight="600" fill="#CBD5E1">PEAK VELOCITY: {metrics['peak_day']} COMMITS / DAY</text>
  <text x="172" y="428" class="mono" font-size="9.5" fill="#64748B">Synced daily via GitHub Actions GraphQL</text>
</svg>
"""


def generate_skills_progress(metrics: dict) -> str:
    langs = metrics["languages"][:6]
    domains = [
        ("AI / ML, RAG & Computer Vision", "YOLO · DETR · Knowledge Graphs · LLMs", 95.0, "#0D9488", "#2DD4BF"),
        ("Flutter, Dart & Mobile Systems", "Riverpod · Drift · Native Android Plugins", 93.0, "#0284C7", "#38BDF8"),
        ("Backend, FastAPI & Postgres RLS", "Supabase · Firebase · Node.js · Realtime", 92.0, "#059669", "#34D399"),
        ("Full-Stack Web (React / TS / SSR)", "React 19 · React Router 7 · Next.js", 91.0, "#7C3AED", "#A78BFA"),
        ("Security, AST & MCP Agents", "TRACE · Attack-Path Models · Android Sec", 90.0, "#E11D48", "#FB7185"),
        ("Embedded, C++ & Aerospace ADCS", "ESP32-S3 · I2C · CubeSat B-dot · OrCAD", 86.0, "#D97706", "#FBBF24"),
    ]

    defs_parts = []
    bars_parts = []

    lang_notes = {
        "Python": "TRACE · HAWKEYE · Vetifi AI · ICARUS · FastAPI",
        "Dart": "Your Space · Stockie · Saral AI · Driftinn · Specular",
        "TypeScript": "EvenEi · TDC · AdSpace · MIT KPI Portal",
        "HTML": "CubeSat EPS Sim · Web Interfaces · Dashboards",
        "CSS": "Design Tokens · Responsive Modules · Glass UI",
        "ShaderLab": "DroneController Unity FPV & Visual Shaders",
        "JavaScript": "Three.js WebGL · Node.js · SquashDeck",
        "C++": "CubeSat B-Dot Control · ESP32-S3 Firmware",
        "Jupyter Notebook": "ML Evaluation · SafeSpace Benchmarks",
        "Kotlin": "Native Android MediaStore & Security Channels",
    }

    for i, (lang, pct) in enumerate(langs):
        c1, c2 = LANG_COLORS.get(lang, ("#14B8A6", "#38BDF8"))
        note = lang_notes.get(lang, "Production & Open-Source Repositories")
        by = 100 + i * 52
        d, e = render_animated_bar(
            uid=f"LANG{i}",
            x=32,
            y=by + 17,
            width=392,
            height=11,
            pct=max(pct, 6.0),
            c1=c1,
            c2=c2,
            delay=0.08 * i,
            shimmer_dur=3.2 + i * 0.2,
            shimmer_offset=0.3 * i,
        )
        defs_parts.append(d)
        bars_parts.append(f"""
    <circle cx="38" cy="{by + 6}" r="4" fill="{c1}"/>
    <text x="49" y="{by + 10}" class="sans" font-size="12.5" font-weight="600" fill="#F1F5F9">{esc(lang)}</text>
    <text x="424" y="{by + 10}" text-anchor="end" class="mono" font-size="11.5" font-weight="700" fill="{c1}">{pct:.1f}%</text>
    {e}
    <text x="32" y="{by + 41}" class="mono" font-size="9.5" fill="#64748B">{esc(note)}</text>""")

    for i, (domain, stack, pct, c1, c2) in enumerate(domains):
        by = 100 + i * 52
        d, e = render_animated_bar(
            uid=f"DOM{i}",
            x=476,
            y=by + 17,
            width=392,
            height=11,
            pct=pct,
            c1=c1,
            c2=c2,
            delay=0.10 + 0.08 * i,
            shimmer_dur=2.9 + i * 0.22,
            shimmer_offset=0.45 * i,
        )
        defs_parts.append(d)
        bars_parts.append(f"""
    <text x="476" y="{by + 10}" class="sans" font-size="12.5" font-weight="600" fill="#F1F5F9">{esc(domain)}</text>
    <text x="868" y="{by + 10}" text-anchor="end" class="mono" font-size="11.5" font-weight="700" fill="{c2}">{int(pct)}%</text>
    {e}
    <text x="476" y="{by + 41}" class="mono" font-size="9.5" fill="#64748B">{esc(stack)}</text>""")

    return f"""<svg width="900" height="432" viewBox="0 0 900 432" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated language distribution and engineering domain mastery progress bars">
  <defs>
    <linearGradient id="skillBg" x1="0" y1="0" x2="900" y2="432" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0B1120"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="barShimmer" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0"/>
      <stop offset="45%" stop-color="#FFFFFF" stop-opacity="0.48"/>
      <stop offset="55%" stop-color="#FFFFFF" stop-opacity="0.62"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
    <pattern id="kineticStripes" width="20" height="20" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect x="0" y="0" width="8" height="20" fill="#FFFFFF" opacity="0.55"/>
    </pattern>
    {''.join(defs_parts)}
    <style>
      .mono {{ font-family: 'Cascadia Code', 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
      .sans {{ font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; }}
    </style>
  </defs>

  <rect x="1" y="1" width="898" height="430" rx="14" fill="url(#skillBg)" stroke="#243247" stroke-width="1.2"/>

  <path d="M 1 15 A 14 14 0 0 1 15 1 L 885 1 A 14 14 0 0 1 899 15 L 899 50 L 1 50 Z" fill="#121B2E"/>
  <line x1="1" y1="50" x2="899" y2="50" stroke="#1E293B" stroke-width="1"/>
  <text x="28" y="31" class="mono" font-size="12.5" font-weight="700" fill="#F8FAFC" letter-spacing="1.2">LIVE LANGUAGE TELEMETRY &amp; ENGINEERING PROFICIENCY</text>
  <text x="872" y="31" text-anchor="end" class="mono" font-size="10" fill="#64748B">REPO-WEIGHTED LIVE SHARE</text>

  <rect x="16" y="62" width="424" height="354" rx="11" fill="#0A0F1D" stroke="#1E293B" stroke-width="1"/>
  <rect x="460" y="62" width="424" height="354" rx="11" fill="#0A0F1D" stroke="#1E293B" stroke-width="1"/>

  <text x="32" y="84" class="mono" font-size="10.5" font-weight="700" fill="#38BDF8" letter-spacing="1.1">GITHUB LANGUAGES (PUBLIC REPOS)</text>
  <text x="476" y="84" class="mono" font-size="10.5" font-weight="700" fill="#FBBF24" letter-spacing="1.1">CORE SYSTEMS DOMAINS</text>

  {''.join(bars_parts)}
</svg>
"""


def generate_footer_wave() -> str:
    return """<svg width="900" height="145" viewBox="0 0 900 145" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Amogh V K animated footer">
  <defs>
    <linearGradient id="footBg" x1="0" y1="0" x2="900" y2="145" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#090D16"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="wave1" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#14B8A6" stop-opacity="0.24"/>
      <stop offset="50%" stop-color="#38BDF8" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="#14B8A6" stop-opacity="0.24"/>
    </linearGradient>
    <linearGradient id="wave2" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#A78BFA" stop-opacity="0.18"/>
      <stop offset="50%" stop-color="#F59E0B" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#14B8A6" stop-opacity="0.18"/>
    </linearGradient>
    <clipPath id="footClip">
      <rect x="1" y="1" width="898" height="143" rx="14"/>
    </clipPath>
    <style>
      .mono { font-family: 'Cascadia Code', 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
      .sans { font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; }
    </style>
  </defs>

  <g clip-path="url(#footClip)">
    <rect x="0" y="0" width="900" height="145" fill="url(#footBg)"/>

    <!-- Drifting layered sine waves -->
    <g>
      <path d="M 0 92 Q 112 66 225 92 T 450 92 T 675 92 T 900 92 T 1125 92 T 1350 92 L 1350 145 L 0 145 Z" fill="url(#wave1)"/>
      <animateTransform attributeName="transform" type="translate" from="0 0" to="-450 0" dur="9s" repeatCount="indefinite"/>
    </g>
    <g>
      <path d="M 0 105 Q 112 126 225 105 T 450 105 T 675 105 T 900 105 T 1125 105 T 1350 105 L 1350 145 L 0 145 Z" fill="url(#wave2)"/>
      <animateTransform attributeName="transform" type="translate" from="-450 0" to="0 0" dur="12s" repeatCount="indefinite"/>
    </g>

    <!-- Subtle ambient pulsing stars -->
    <circle cx="95" cy="32" r="2" fill="#2DD4BF"><animate attributeName="opacity" values="0.2;1;0.2" dur="3.2s" repeatCount="indefinite"/></circle>
    <circle cx="165" cy="54" r="1.5" fill="#38BDF8"><animate attributeName="opacity" values="0.9;0.2;0.9" dur="2.6s" repeatCount="indefinite"/></circle>
    <circle cx="745" cy="36" r="2" fill="#FBBF24"><animate attributeName="opacity" values="0.2;1;0.2" dur="3.6s" repeatCount="indefinite"/></circle>
    <circle cx="818" cy="58" r="1.6" fill="#A78BFA"><animate attributeName="opacity" values="1;0.25;1" dur="2.9s" repeatCount="indefinite"/></circle>

    <!-- Signature Motto -->
    <text x="450" y="52" text-anchor="middle" class="sans" font-size="18" font-weight="600" font-style="italic" fill="#F8FAFC">
      "What people find boring, is what interests me."
    </text>
    <text x="450" y="78" text-anchor="middle" class="mono" font-size="11.5" fill="#94A3B8">
      Engineering intelligent systems quietly, rigorously, and end to end.
    </text>
    <text x="450" y="122" text-anchor="middle" class="mono" font-size="10.5" fill="#CBD5E1" letter-spacing="1.4">
      AMOGH V K  ·  EVENEI  ·  THE DEVELOPER COMMUNITY  ·  AMOGH.EVENEI.COM
    </text>
  </g>

  <rect x="1" y="1" width="898" height="143" rx="14" stroke="#243247" stroke-width="1.2"/>
</svg>
"""


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    metrics = fetch_github_data()
    chrono = compute_chronology(now)

    outputs = {
        "hero-banner.svg": generate_hero_banner(),
        "divider.svg": generate_divider(),
        "terminal-card.svg": generate_terminal_card(metrics),
        "progress-bars.svg": generate_progress_bars(metrics, chrono),
        "skills-progress.svg": generate_skills_progress(metrics),
        "footer-wave.svg": generate_footer_wave(),
    }

    for filename, content in outputs.items():
        path = ASSETS_DIR / filename
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path} ({len(content):,} bytes)")


if __name__ == "__main__":
    main()
