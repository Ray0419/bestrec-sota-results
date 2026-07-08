"""CPU-only strict-reviewer recompute (no torch, no CUDA).
Builds the paper's §5.4 per-rung interaction-titration table and re-verifies the
§5.2 MI cross-category filter numbers and the §5.3 MI tail-law contrast, directly
from the on-disk result JSONs. Read-only; writes nothing but stdout.
"""
import json, glob, math, os

D = os.path.dirname(os.path.abspath(__file__))

def load(path):
    with open(path) as f:
        return json.load(f)

def tail_head_ndcg(d):
    bt = d.get("best_test") or {}
    bp = (bt.get("by_popularity") if isinstance(bt, dict) else None) or {}
    def g(bucket):
        v = bp.get(bucket)
        if isinstance(v, dict):
            return v.get("NDCG@10")
        return None
    return g("tail"), g("head"), g("mid")

def best_test(d):
    bt = d.get("best_test")
    if isinstance(bt, dict):
        return bt.get("NDCG@10")
    return bt

def mean_std(xs):
    n = len(xs)
    if n == 0:
        return None, None
    m = sum(xs) / n
    if n == 1:
        return m, 0.0
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, math.sqrt(var)

# ---- interaction/item per rung (from ledger: full=24.405, rho066 kept 16.109) ----
INT_PER_ITEM = {1.00: 24.405, 0.97: None, 0.94: None, 0.91: None,
                0.88: 21.5, 0.78: None, 0.66: 16.109}

def collect_rung(rho_token, text_glob, id_glob):
    """Return per-seed text-ID deltas for tail/head."""
    texts = sorted(glob.glob(os.path.join(D, text_glob)))
    rows = []
    for tp in texts:
        ip = tp.replace("text", "idonly")
        if not os.path.exists(ip):
            continue
        td, idd = load(tp), load(ip)
        tt, th, _ = tail_head_ndcg(td)
        it, ih, _ = tail_head_ndcg(idd)
        if None in (tt, th, it, ih):
            continue
        seed = td.get("config", {}).get("seed")
        rows.append({"seed": seed, "tail_d": tt - it, "head_d": th - ih,
                     "text_tail": tt, "id_tail": it})
    return rows

def summarize(name, intperitem, rows):
    if not rows:
        print(f"  {name:>10s} | (no data)")
        return
    tail = [r["tail_d"] for r in rows]
    head = [r["head_d"] for r in rows]
    tm, ts = mean_std(tail)
    hm, hs = mean_std(head)
    tpos = sum(1 for x in tail if x > 0)
    hpos = sum(1 for x in head if x > 0)
    ipi = f"{intperitem:.3f}" if intperitem else "  ?  "
    print(f"  {name:>10s} | int/item {ipi} | n={len(rows)} | "
          f"tail Δ {tm:+.6f} ± {ts:.6f} ({tpos}/{len(rows)}+) | "
          f"head Δ {hm:+.6f} ± {hs:.6f} ({hpos}/{len(rows)}+)")
    return tm, head, tail

print("=" * 100)
print("§5.4  INTERACTION-THINNING TITRATION LADDER  (Video_Games, text-ID Δ, by_popularity terciles)")
print("=" * 100)

# Full density rho=1.0 baseline
rows_full = []
tp, ip = os.path.join(D, "results_TAIL_V2_text_VG.json"), os.path.join(D, "results_TAIL_idonly_VG.json")
if os.path.exists(tp) and os.path.exists(ip):
    td, idd = load(tp), load(ip)
    tt, th, _ = tail_head_ndcg(td); it, ih, _ = tail_head_ndcg(idd)
    if None not in (tt, th, it, ih):
        rows_full = [{"seed": td.get("config", {}).get("seed"), "tail_d": tt-it, "head_d": th-ih,
                      "text_tail": tt, "id_tail": it}]
summarize("rho=1.00", INT_PER_ITEM[1.00], rows_full)

for rho, tok in [(0.97, "rho097"), (0.94, "rho094"), (0.91, "rho091"),
                 (0.88, "rho088"), (0.78, "rho078")]:
    rows = collect_rung(tok, f"results_TITR_text_{tok}_s*_VG.json", f"results_TITR_idonly_{tok}_s*_VG.json")
    summarize(f"rho={rho:.2f}", INT_PER_ITEM.get(rho), rows)

# rho=0.66 lives under TITRATE naming (2 seeds: base file + seed09 file)
rows66 = []
for tp in [os.path.join(D, "results_TITRATE_text_rho066_VG.json"),
           os.path.join(D, "results_TITRATE_text_rho066_seed09_VG.json")]:
    ip = tp.replace("text", "idonly")
    if os.path.exists(tp) and os.path.exists(ip):
        td, idd = load(tp), load(ip)
        tt, th, _ = tail_head_ndcg(td); it, ih, _ = tail_head_ndcg(idd)
        if None not in (tt, th, it, ih):
            rows66.append({"seed": td.get("config", {}).get("seed"), "tail_d": tt-it, "head_d": th-ih,
                           "text_tail": tt, "id_tail": it})
summarize("rho=0.66", INT_PER_ITEM[0.66], rows66)

print()
print("=" * 100)
print("§5.2 / §5.3  MUSICAL_INSTRUMENTS cross-category + tail-law (5 seeds 20260608-12)")
print("=" * 100)
mi_text = sorted(glob.glob(os.path.join(D, "results_MI_TAIL_V2_text_seed*.json")))
mi_tail_d, mi_head_d, mi_overall_text, mi_overall_id = [], [], [], []
for tp in mi_text:
    ip = tp.replace("V2_text", "idonly")
    if not os.path.exists(ip):
        continue
    td, idd = load(tp), load(ip)
    tt, th, _ = tail_head_ndcg(td); it, ih, _ = tail_head_ndcg(idd)
    mi_tail_d.append(tt - it); mi_head_d.append(th - ih)
    mi_overall_text.append(best_test(td)); mi_overall_id.append(best_test(idd))
tm, ts = mean_std(mi_tail_d); hm, hs = mean_std(mi_head_d)
print(f"  MI tail Δ (text-ID): {tm:+.6f} ± {ts:.6f}  ({sum(1 for x in mi_tail_d if x>0)}/{len(mi_tail_d)} positive)")
print(f"    per-seed: {['%+.6f'%x for x in mi_tail_d]}")
print(f"  MI head Δ (text-ID): {hm:+.6f} ± {hs:.6f}")
# t-CI for tail
if len(mi_tail_d) >= 2:
    n = len(mi_tail_d); se = ts / math.sqrt(n)
    tcrit = 2.776  # df=4, 95%
    print(f"  MI tail 95% t-CI (df={n-1}): [{tm - tcrit*se:+.6f}, {tm + tcrit*se:+.6f}]"
          f"  {'EXCLUDES 0' if (tm - tcrit*se) > 0 else 'includes 0'}")
om, _ = mean_std(mi_overall_text); im, _ = mean_std(mi_overall_id)
print(f"  MI overall best_test: text {om:.5f} vs ID {im:.5f}  (Δ {om-im:+.5f}, +{100*(om-im)/im:.1f}%)")

# MI V2 stack (filter16) 5-seed for §5.2 headline 0.0413
mi_v2 = sorted(glob.glob(os.path.join(D, "results_MI_V2_ls02_filter16_seed*.json")))
v2 = [best_test(load(p)) for p in mi_v2]
v2 = [x for x in v2 if x is not None]
vm, vs = mean_std(v2)
print(f"  MI V2 (ls0.2+filter16) best_test 5-seed: {vm:.5f} ± {vs:.5f}  (paper §5.2 says 0.0413 ± 0.0005)")
mi_base = sorted(glob.glob(os.path.join(D, "results_BEST_MI_sbert_e20_seed*.json")))
b = [best_test(load(p)) for p in mi_base]; b = [x for x in b if x is not None]
bm, bs = mean_std(b)
print(f"  MI SBERT+TAPE base best_test {len(b)}-seed: {bm:.5f} ± {bs:.5f}")
print("=" * 100)
