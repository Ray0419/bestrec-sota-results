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
Traceback (most recent call last):
  File "C:\Users\rayxc\Documents\R\_bestrec_run\adjudicate_tfv2.py", line 254, in <module>
    sys.exit(main())
             ^^^^^^
  File "C:\Users\rayxc\Documents\R\_bestrec_run\adjudicate_tfv2.py", line 222, in main
    print(f"  {label}: {fmt(welch(at2, ai2))}")
                            ^^^^^^^^^^^^^^^
  File "C:\Users\rayxc\Documents\R\_bestrec_run\adjudicate_tfv2.py", line 98, in welch
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
         ~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ZeroDivisionError: float division by zero
