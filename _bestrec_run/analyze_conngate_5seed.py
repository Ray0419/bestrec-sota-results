"""Pre-registered conn-gate 5-seed MI confirmation analysis.
Seed-paired tail Delta = tail(conn-gate k8) - tail(control MI_TAIL_V2_text), seeds 08-12.
GATE: 95% CI of paired Delta excludes 0 AND mean>0 => actionable; includes 0 => Table 2 negative.
"""
import json, math, statistics as st

SEEDS = [20260608, 20260609, 20260610, 20260611, 20260612]

def tail(path):
    d = json.load(open(path))
    bt = d["best_test"]
    bp = bt["by_popularity"]
    return (bp["tail"]["NDCG@10"], bt["NDCG@10"], bt["n_eval"], bp["tail"]["n"],
            d.get("learned_conn_gate_alpha"), d.get("learned_conn_gate_slope"))

rows, diffs = [], []
print(f"{'seed':>10} {'cg_tail':>10} {'ctl_tail':>10} {'Δtail':>11} {'cg_over':>9} {'ctl_over':>9} {'α':>8} {'n_eval':>7} {'tail_n':>6}")
for s in SEEDS:
    cg = tail(f"_bestrec_run/results_CONNGATE_MI_k8_seed{s}.json")
    ct = tail(f"_bestrec_run/results_MI_TAIL_V2_text_seed{s}.json")
    dt = cg[0] - ct[0]
    diffs.append(dt)
    a = cg[4]
    astr = f"{a:.4f}" if a is not None else "n/a"
    flag = "" if (cg[2] == 57439 and cg[3] == 8800) else "  <<EVAL MISMATCH"
    print(f"{s:>10} {cg[0]:>10.6f} {ct[0]:>10.6f} {dt:>+11.6f} {cg[1]:>9.5f} {ct[1]:>9.5f} {astr:>8} {cg[2]:>7} {cg[3]:>6}{flag}")

n = len(diffs)
mean = st.mean(diffs)
sd = st.stdev(diffs)
se = sd / math.sqrt(n)
# t_0.975, df=4 = 2.776
tcrit = 2.776
lo, hi = mean - tcrit*se, mean + tcrit*se
tstat = mean / se if se > 0 else float('nan')
npos = sum(1 for d in diffs if d > 0)
print(f"\nPaired tail Δ (n={n}): mean {mean:+.6f}  sd {sd:.6f}  se {se:.6f}")
print(f"  t = {tstat:+.3f} (df={n-1}),  {npos}/{n} positive")
print(f"  95% CI [{lo:+.6f}, {hi:+.6f}]")
excl0 = (lo > 0) or (hi < 0)
print(f"\nGATE: CI excludes 0 = {excl0}; mean>0 = {mean>0}")
if excl0 and mean > 0:
    print("  => GENUINE ACTIONABLE TAIL LEVER (per pre-registration) -> VG 5-seed confirm + NEW contribution")
else:
    print("  => CI INCLUDES 0 -> KILL -> conn-gate = interpretable §5.5 Table 2 NEGATIVE")
