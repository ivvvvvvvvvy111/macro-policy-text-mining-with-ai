from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


HALFLIFE_DAYS = {
    "immediate": 5,
    "short": 20,
    "medium": 60,
    "long": 120,
    "unknown": 20,
    "": 20,
}

ALL_A_CHANNELS = [
    "market_backstop",
    "incremental_capital",
    "trading_cost_liquidity",
    "financing_share_supply",
    "governance_quality",
    "regulatory_risk",
    "institutional_openness",
    "uncertainty_coordination",
]

# Truncate decay contributions beyond this multiple of half-life.
DECAY_WINDOW_MULT = 4.0
MIN_ABS_SIGNAL = 1e-12


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_date(value: str) -> Optional[date]:
    text = (value or "").strip()[:10]
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def half_life_days(horizon: str) -> int:
    key = (horizon or "").strip().lower()
    return HALFLIFE_DAYS.get(key, HALFLIFE_DAYS["unknown"])


def decay_signal(score: float, days_since: int, half_life: int) -> float:
    if half_life <= 0:
        return 0.0
    return score * (2.0 ** (-float(days_since) / float(half_life)))


def dispersion(positive: float, negative: float) -> float:
    """|Positive| + |Negative| - |Net| ; Net = Positive + Negative."""
    net = positive + negative
    return abs(positive) + abs(negative) - abs(net)


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "none":
        return None
    try:
        return float(text)
    except ValueError:
        return None


@dataclass
class RelationEvent:
    track: str
    t0: date
    score: float
    half_life: int
    channel: str
    industry_l2_code: str
    industry_l2_name: str
    industry_l1_name: str
    style_axis: str
    news_id: str
    horizon: str


def load_events(path: Path) -> List[RelationEvent]:
    import csv

    events: List[RelationEvent] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            track = (row.get("track") or "").strip()
            t0 = parse_date(row.get("date") or "")
            if t0 is None:
                continue
            horizon = (row.get("horizon") or "unknown").strip() or "unknown"
            if track == "industry":
                score = _to_float(row.get("state_score"))
            elif track == "all_a":
                score = _to_float(row.get("state_score"))
            elif track == "style":
                score = _to_float(row.get("a_unit"))
            else:
                continue
            if score is None:
                continue
            events.append(
                RelationEvent(
                    track=track,
                    t0=t0,
                    score=score,
                    half_life=half_life_days(horizon),
                    channel=(row.get("channel") or "").strip(),
                    industry_l2_code=(row.get("industry_l2_code") or "").strip(),
                    industry_l2_name=(row.get("industry_l2_name") or "").strip(),
                    industry_l1_name=(row.get("industry_l1_name") or "").strip(),
                    style_axis=(row.get("style_axis") or "").strip(),
                    news_id=(row.get("news_id") or "").strip(),
                    horizon=horizon,
                )
            )
    return events


def _date_range(start: date, end: date) -> List[date]:
    out: List[date] = []
    cur = start
    while cur <= end:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def _accum_key_maps(
    events: Iterable[RelationEvent],
    key_fn,
) -> Tuple[Dict[Tuple, Dict[str, float]], date, date]:
    """Accumulate pos/neg/count/news for each key including date as first element of key."""
    buckets: Dict[Tuple, Dict[str, float]] = defaultdict(
        lambda: {"positive": 0.0, "negative": 0.0, "n_relations": 0.0}
    )
    news_sets: Dict[Tuple, set] = defaultdict(set)
    min_d: Optional[date] = None
    max_d: Optional[date] = None

    for ev in events:
        window = max(1, int(math.ceil(DECAY_WINDOW_MULT * ev.half_life)))
        end = ev.t0 + timedelta(days=window)
        if min_d is None or ev.t0 < min_d:
            min_d = ev.t0
        if max_d is None or end > max_d:
            max_d = end
        for offset in range(window + 1):
            t = ev.t0 + timedelta(days=offset)
            signal = decay_signal(ev.score, offset, ev.half_life)
            if abs(signal) < MIN_ABS_SIGNAL:
                continue
            key = key_fn(ev, t)
            if key is None:
                continue
            b = buckets[key]
            if signal > 0:
                b["positive"] += signal
            else:
                b["negative"] += signal
            b["n_relations"] += 1.0
            if ev.news_id:
                news_sets[key].add(ev.news_id)

    for key, news in news_sets.items():
        buckets[key]["n_news"] = float(len(news))
    if min_d is None or max_d is None:
        today = date.today()
        return {}, today, today
    return buckets, min_d, max_d


def build_industry_panels(events: List[RelationEvent]):
    ind_events = [
        e
        for e in events
        if e.track == "industry" and e.industry_l2_code and e.channel
    ]
    channel_buckets, min_d, max_d = _accum_key_maps(
        ind_events,
        lambda ev, t: (t, ev.industry_l2_code, ev.industry_l2_name, ev.industry_l1_name, ev.channel),
    )
    channel_rows = []
    for key, b in channel_buckets.items():
        t, code, name, l1, channel = key
        pos, neg = b["positive"], b["negative"]
        channel_rows.append(
            {
                "date": t.isoformat(),
                "industry_l2_code": code,
                "industry_l2_name": name,
                "industry_l1_name": l1,
                "channel": channel,
                "positive": pos,
                "negative": neg,
                "net": pos + neg,
                "dispersion": dispersion(pos, neg),
                "n_relations": int(b["n_relations"]),
                "n_news": int(b.get("n_news", 0)),
            }
        )
    channel_rows.sort(key=lambda r: (r["date"], r["industry_l2_code"], r["channel"]))

    # Roll up across channels for industry_daily
    roll: Dict[Tuple[str, str, str, str], Dict[str, float]] = defaultdict(
        lambda: {"positive": 0.0, "negative": 0.0, "n_relations": 0.0, "n_news": 0.0}
    )
    news_roll: Dict[Tuple[str, str, str, str], set] = defaultdict(set)
    for row in channel_rows:
        k = (
            row["date"],
            row["industry_l2_code"],
            row["industry_l2_name"],
            row["industry_l1_name"],
        )
        roll[k]["positive"] += row["positive"]
        roll[k]["negative"] += row["negative"]
        roll[k]["n_relations"] += row["n_relations"]

    # Rebuild n_news properly from events
    for ev in ind_events:
        window = max(1, int(math.ceil(DECAY_WINDOW_MULT * ev.half_life)))
        for offset in range(window + 1):
            t = ev.t0 + timedelta(days=offset)
            signal = decay_signal(ev.score, offset, ev.half_life)
            if abs(signal) < MIN_ABS_SIGNAL:
                continue
            k = (
                t.isoformat(),
                ev.industry_l2_code,
                ev.industry_l2_name,
                ev.industry_l1_name,
            )
            if ev.news_id:
                news_roll[k].add(ev.news_id)

    industry_rows = []
    for k, b in roll.items():
        pos, neg = b["positive"], b["negative"]
        industry_rows.append(
            {
                "date": k[0],
                "industry_l2_code": k[1],
                "industry_l2_name": k[2],
                "industry_l1_name": k[3],
                "positive_sum": pos,
                "negative_sum": neg,
                "net_sum": pos + neg,
                "dispersion": dispersion(pos, neg),
                "n_relations": int(b["n_relations"]),
                "n_news": len(news_roll.get(k, set())),
                "note": "cross_channel_sum_baseline_not_unique_total",
            }
        )
    industry_rows.sort(key=lambda r: (r["date"], r["industry_l2_code"]))
    return channel_rows, industry_rows, min_d, max_d


def build_all_a_panels(events: List[RelationEvent]):
    alla = [e for e in events if e.track == "all_a" and e.channel]
    channel_buckets, min_d, max_d = _accum_key_maps(
        alla, lambda ev, t: (t, ev.channel)
    )
    channel_rows = []
    for key, b in channel_buckets.items():
        t, channel = key
        pos, neg = b["positive"], b["negative"]
        channel_rows.append(
            {
                "date": t.isoformat(),
                "channel": channel,
                "positive": pos,
                "negative": neg,
                "net": pos + neg,
                "dispersion": dispersion(pos, neg),
                "n_relations": int(b["n_relations"]),
                "n_news": int(b.get("n_news", 0)),
            }
        )
    channel_rows.sort(key=lambda r: (r["date"], r["channel"]))

    by_date: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {
            "positive": 0.0,
            "negative": 0.0,
            "n_relations": 0.0,
            "temperature": 0.0,
        }
    )
    nets_by_date_channel: Dict[str, Dict[str, float]] = defaultdict(dict)
    news_by_date: Dict[str, set] = defaultdict(set)
    horizon_net: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"immediate": 0.0, "short": 0.0, "medium": 0.0, "long": 0.0, "unknown": 0.0}
    )

    for row in channel_rows:
        d = row["date"]
        by_date[d]["positive"] += row["positive"]
        by_date[d]["negative"] += row["negative"]
        by_date[d]["n_relations"] += row["n_relations"]
        nets_by_date_channel[d][row["channel"]] = row["net"]

    for ev in alla:
        window = max(1, int(math.ceil(DECAY_WINDOW_MULT * ev.half_life)))
        hz_key = (
            ev.horizon
            if ev.horizon in {"immediate", "short", "medium", "long"}
            else "unknown"
        )
        for offset in range(window + 1):
            t = ev.t0 + timedelta(days=offset)
            signal = decay_signal(ev.score, offset, ev.half_life)
            if abs(signal) < MIN_ABS_SIGNAL:
                continue
            ds = t.isoformat()
            if ev.news_id:
                news_by_date[ds].add(ev.news_id)
            horizon_net[ds][hz_key] += signal

    weight = 1.0 / float(len(ALL_A_CHANNELS))
    daily_rows = []
    # Ensure continuous calendar for temperature panel over observed range
    if min_d and max_d:
        calendar = _date_range(min_d, max_d)
    else:
        calendar = []
    for d in calendar:
        ds = d.isoformat()
        pos = by_date[ds]["positive"] if ds in by_date else 0.0
        neg = by_date[ds]["negative"] if ds in by_date else 0.0
        nets = nets_by_date_channel.get(ds, {})
        temperature = sum(nets.get(ch, 0.0) * weight for ch in ALL_A_CHANNELS)
        hz = horizon_net.get(ds, {})
        daily_rows.append(
            {
                "date": ds,
                "temperature": temperature,
                "positive": pos,
                "negative": neg,
                "net": pos + neg,
                "dispersion": dispersion(pos, neg),
                "attention_relations": int(by_date[ds]["n_relations"]) if ds in by_date else 0,
                "attention_news": len(news_by_date.get(ds, set())),
                "net_immediate": hz.get("immediate", 0.0),
                "net_short": hz.get("short", 0.0),
                "net_medium": hz.get("medium", 0.0),
                "net_long": hz.get("long", 0.0),
                "net_unknown": hz.get("unknown", 0.0),
                "channel_weighting": "equal_1_over_8",
            }
        )
    return channel_rows, daily_rows, min_d, max_d


def build_style_panels(events: List[RelationEvent]):
    style_events = [e for e in events if e.track == "style" and e.style_axis]
    buckets, min_d, max_d = _accum_key_maps(
        style_events, lambda ev, t: (t, ev.style_axis)
    )
    rows = []
    for key, b in buckets.items():
        t, axis = key
        pos, neg = b["positive"], b["negative"]
        rows.append(
            {
                "date": t.isoformat(),
                "style_axis": axis,
                "positive": pos,
                "negative": neg,
                "net": pos + neg,
                "dispersion": dispersion(pos, neg),
                "n_relations": int(b["n_relations"]),
                "n_news": int(b.get("n_news", 0)),
                "note": "axes_not_summed_to_total_style_score",
            }
        )
    rows.sort(key=lambda r: (r["date"], r["style_axis"]))
    return rows, min_d, max_d
