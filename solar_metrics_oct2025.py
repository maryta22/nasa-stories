#!/usr/bin/env python3
import json
from datetime import datetime
from collections import Counter, defaultdict
from pathlib import Path

DATA_PATH = Path("../edited_events.json")

def parse_dt(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def class_letter_and_value(cls):
    if not cls or not isinstance(cls, str):
        return None, None
    cls = cls.strip().upper()
    if not cls or cls[0] not in "ABCMX":
        return None, None
    letter = cls[0]
    try:
        value = float(cls[1:])
    except Exception:
        value = None
    return letter, value

def load_xra_events_month(path: Path, year: int, month: int):
    data = json.loads(path.read_text(encoding="utf-8"))
    events = []
    for e in data:
        if str(e.get("type", "")).upper() != "XRA":
            continue
        begin = parse_dt(e.get("begin_datetime"))
        peak  = parse_dt(e.get("max_datetime") or e.get("peak_datetime"))
        end   = parse_dt(e.get("end_datetime"))
        dt = peak or begin
        if not dt:
            continue
        if dt.year == year and dt.month == month:
            events.append({
                "begin": begin,
                "peak":  peak,
                "end":   end,
                "class": (e.get("particulars1") or e.get("class")),
                "region": e.get("region"),
                "raw": e
            })
    return events

def summarize(events):
    class_counts = Counter()
    durations_by_class = defaultdict(list)
    day_counts = Counter()
    region_counts = Counter()

    for ev in events:
        letter, _ = class_letter_and_value(ev["class"])
        if letter:
            class_counts[letter] += 1
        if ev.get("begin") and ev.get("end"):
            dur = (ev["end"] - ev["begin"]).total_seconds()/60.0
            if letter:
                durations_by_class[letter].append(dur)
            ev["duration_min"] = dur
        dt = ev.get("peak") or ev.get("begin")
        if dt:
            day_counts[dt.strftime("%Y-%m-%d")] += 1
        if ev.get("region"):
            region_counts[ev["region"]] += 1

    most_active_day, most_active_count = (None, 0)
    if day_counts:
        most_active_day, most_active_count = max(day_counts.items(), key=lambda x: x[1])

    top_regions = region_counts.most_common(3)

    rank = {"A":0,"B":1,"C":2,"M":3,"X":4}
    def flare_strength_key(ev):
        letter, value = class_letter_and_value(ev["class"])
        return (rank.get(letter, -1), value or 0.0)
    strongest = max(events, key=flare_strength_key) if events else None

    strongest_duration = None
    if strongest and strongest.get("begin") and strongest.get("end"):
        strongest_duration = (strongest["end"] - strongest["begin"]).total_seconds()/60.0

    cmx_total = sum(class_counts.get(k,0) for k in ("C","M","X"))
    by_class_percent = {k: (class_counts.get(k,0)*100.0/cmx_total) if cmx_total else 0.0
                        for k in ("C","M","X")}

    return {
        "class_counts": class_counts,
        "by_class_percent": by_class_percent,
        "most_active_day": (most_active_day, most_active_count),
        "top_regions": top_regions,
        "strongest": strongest,
        "strongest_duration_min": strongest_duration
    }

def main():
    year, month = 2025, 10
    events = load_xra_events_month(DATA_PATH, year, month)
    s = summarize(events)

    c = s["class_counts"].get("C", 0)
    m = s["class_counts"].get("M", 0)
    x = s["class_counts"].get("X", 0)
    total_cmx = max(c + m + x, 1)
    pc = (c*100.0/total_cmx)
    pm = (m*100.0/total_cmx)
    px = (x*100.0/total_cmx)

    if x > 0:
        print(f'“This month C-class flares lead (≈{pc:.1f}%), M-class are ≈{pm:.1f}%, and X-class ≈{px:.1f}%.”')
    else:
        print(f'“This month C-class flares lead (≈{pc:.1f}%), M-class are ≈{pm:.1f}%, and there were no X-class flares.”')

    most_day, most_cnt = s["most_active_day"]
    if most_day:
        print(f'“{most_day} was a highly active day ({most_cnt} flares).”')

    regs = [str(r) for r,_ in s["top_regions"]]
    if len(regs) >= 3:
        print(f'“Regions {regs[0]}, {regs[1]}, and {regs[2]} were the most active.”')
    elif len(regs) == 2:
        print(f'“Regions {regs[0]} and {regs[1]} were the most active.”')
    elif len(regs) == 1:
        print(f'“Region {regs[0]} was the most active.”')

    strongest = s["strongest"]
    if strongest:
        peak_iso = strongest["peak"].strftime("%Y-%m-%d %H:%M UTC") if strongest["peak"] else "N/A"
        dur = s["strongest_duration_min"]
        dur_txt = f"~{dur:.0f} min" if dur is not None else "N/A"
        region = strongest.get("region","?")
        print(f'“In October, the strongest flare was {strongest["class"]} (peak {peak_iso}, duration {dur_txt}, NOAA region {region}).”')

if __name__ == "__main__":
    main()
