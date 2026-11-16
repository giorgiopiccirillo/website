"""Small helpers for the make_data.py scripts. Fixed-seed, invented data only."""
def pct(a, b): return round(a / b * 100)
def per_step(cum): return [cum[0]] + [cum[i] - cum[i - 1] for i in range(1, len(cum))]
def spark(total, shape=(.05, .1, .18, .27, .38, .52, .68, .85, 1)): return [round(total * f) for f in shape]
def curve(total, shape):
    out, acc = [], 0
    for s in shape:
        acc += total * s; out.append(round(acc))
    out[-1] = total; return out
def graph_nodes(items, code_of, dots=24):
    """items: (label, group, small_text, record). Returns nodes, records. Adds anonymous dots per group."""
    nodes, records, groups = [], {}, {}
    for label, group, small, rec in items:
        nid = f"{label}-{code_of[group]}"; groups[group] = 1
        nodes.append({"id": nid, "label": label, "group": group, "school": small, "big": True}); records[nid] = rec
    for g in groups:
        for k in range(dots): nodes.append({"id": f"x{code_of[g]}{k}", "label": "record", "group": g, "school": "—"})
    return nodes, records
LOG_TAIL = [["check", "totals match last run ✓"], ["done", "dashboard refreshed"], ["wait", "next sync in 5 min"]]
