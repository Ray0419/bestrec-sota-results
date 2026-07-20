## TFV2 adjudication (mechanical; PREREG_TAIL_FIR_V2.md rules)

MI cohorts: items=24587, zero-exposure=31, positive-tail=7969 (boundary freq 5), excl-boundary=4699, band[1,6]=10387
E1 MI positive-tail NDCG@10 (text-id): diff +0.000420, t=3.79, df=13.2, p=2.21e-03, 95% CI [+0.000181, +0.000660]
E2 IS overall NDCG@10 (filter-nofilter): diff +0.002131, t=16.99, df=14.0, p=1.01e-10, 95% CI [+0.001862, +0.002400]
E3 CDs overall NDCG@10 (filter-nofilter): diff +0.005770, t=26.12, df=9.6, p=3.26e-10, 95% CI [+0.005275, +0.006266]

Holm (alpha 0.05):
  E2: p=1.01e-10 vs 0.0167, CI-low +0.001862 -> PASS
  E3: p=3.26e-10 vs 0.0250, CI-low +0.005275 -> PASS
  E1: p=2.21e-03 vs 0.0500, CI-low +0.000181 -> PASS

PRIMARY FAMILY VERDICT: ALL PASS

Secondary (descriptive; no gates):
  MI zero-exposure: diff +0.000000 (degenerate bin: zero between-seed variance in both arms; no t/CI)
  MI tail excl-boundary: diff +0.000071, t=0.67, df=13.9, p=5.17e-01, 95% CI [-0.000159, +0.000302]
  MI band[1,6]: diff +0.000546, t=3.48, df=13.5, p=3.85e-03, 95% CI [+0.000208, +0.000883]
  MI tail HR@10: diff +0.001150, t=5.88, df=13.7, p=4.32e-05, 95% CI [+0.000730, +0.001570]
  VG positive-tail (boundary freq 6): diff +0.000173, t=1.56, df=14.0, p=1.41e-01, 95% CI [-0.000065, +0.000411]
  four-arm (MI-VG) tail contrast: est +0.000247, t=1.57, df=27.2, p=1.27e-01
  IS positive-tail (filter-nofilter): diff +0.000775, t=5.19, df=12.9, p=1.76e-04, 95% CI [+0.000453, +0.001098]
  CDs positive-tail (filter-nofilter): diff +0.002329, t=21.80, df=14.0, p=3.33e-12, 95% CI [+0.002100, +0.002558]
