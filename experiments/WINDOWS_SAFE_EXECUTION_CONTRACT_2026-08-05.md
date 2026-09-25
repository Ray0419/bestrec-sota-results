# Windows-safe experiment execution contract

Status: mandatory for new experiment runners launched after 2026-08-05.

## Incident diagnosis

The user-visible exception was not a numerical or OpenMP thread failure. An
earlier proof-of-concept was launched with a one-second foreground tool timeout.
The launcher closed its stdout pipe while Python was still printing, producing
`OSError: [Errno 22] Invalid argument` and a secondary exception from the
stdout text wrapper. The same script completed normally when given enough time.

A separate RQ3 `WinError 5` came from replacing an existing checkpoint on
Windows. RQ3 was repaired to use append-only, fingerprinted checkpoint files;
the subsequent complete 48-cell run validated that repair.

## Mandatory launch rules

1. Invoke the workspace virtual-environment interpreter directly. Do not nest
   an outcome-producing run inside `uv run`.
2. Use unbuffered Python (`python -u`).
3. Never give foreground compute a short tool timeout. Either:
   - run with a timeout longer than the conservative runtime bound and yield
     the tool cell for monitoring; or
   - launch one hidden process with stdout and stderr redirected to persistent
     files, record its PID, and poll the PID plus an explicit result marker.
4. Do not capture a long-running child with `stdout=PIPE` or `stderr=PIPE`.
   Persistent file handles must own both streams for the process lifetime.
5. On cancellation, terminate and wait for the child before closing its log
   handles.
6. A run is complete only when the PID has exited, the result marker exists,
   the declared hashes verify, and the experiment lock is released.
7. RQ4 outcome execution must use its bound
   `run_rq4_smar_k0_safe.ps1` launcher. The launcher holds a share-none lock,
   normalizes duplicate-case `PATH`/`Path` entries before Windows PowerShell
   5.1 can construct its case-insensitive `Start-Process` environment, and
   starts the hash-bound base interpreter image hidden with `-B -u`, sets
   `__PYVENV_LAUNCHER__` so CPython retains the workspace venv, and gives the
   child persistent stdout/stderr files. This bypasses the venv redirector:
   the token/SHA-bound PID atomically published by Python must equal the process
   handle returned by `Start-Process`. Its acknowledgement is also published
   atomically before any source is loaded. Failed or cooperatively cancelled
   handshakes kill and wait the local process handle in `finally`. The launcher
   waits for that actual PID, launches a
   separately authorized deep-chain verifier with the same handshake, and only
   then creates a unique hash-bound commit marker.
   A runner final JSON without that post-exit marker is not a completed result
   and may not authorize an outcome rerun. A sole deeply valid uncommitted final
   is recovered and committed without outcome recomputation only after the
   original launcher, runner, and bootstrap PIDs are verified dead and the
   original launch record, stdout, zero-byte stderr, and zero-byte bootstrap
   exception ledger are hash-bound into a recovery attestation; multiple or
   malformed finals fail closed.

## Mandatory thread bounds

Set these variables to `1` before importing NumPy, SciPy, scikit-learn, or
PyTorch:

- `OMP_NUM_THREADS`
- `MKL_NUM_THREADS`
- `OPENBLAS_NUM_THREADS`
- `NUMEXPR_NUM_THREADS`
- `VECLIB_MAXIMUM_THREADS`
- `BLIS_NUM_THREADS`

CPU-only experiments also set `CUDA_VISIBLE_DEVICES=-1` before importing
PyTorch.

For PyTorch, also call `torch.set_num_threads(1)` and
`torch.set_num_interop_threads(1)` before model work. All data loaders must use
`num_workers=0` on native Windows unless a separate prospective benchmark
explicitly justifies worker processes.

## Mandatory artifact semantics

1. Outcome checkpoints and progress snapshots are append-only and include a
   protocol fingerprint plus monotone sequence number in the filename.
2. Do not overwrite or `replace()` a live checkpoint path on Windows.
3. Resume scans backward for the newest hash-valid snapshot and rejects any
   snapshot whose protocol, runner, input, or configuration hash differs.
4. Logs, checkpoints, and final results are written under an experiment-
   specific directory; no shared paper or confirmatory artifact is mutated.
5. Install `threading.excepthook` and `sys.unraisablehook` in new Python runners
   so any genuine future background-thread or finalizer exception is recorded
   in the experiment error log before process exit. A nonempty asynchronous-
   error ledger is forensic evidence, never a committable outcome: the process
   exits nonzero and automatic recovery/retry is refused pending an explicit
   integrity audit.
6. A resumed fold may finish the scientific table, but it cannot satisfy a
   clean wall-clock gate: the runtime gate is automatically false after any
   partial-fold resume. This prevents a restart from erasing prior compute
   time or turning a slow/crashed execution into a pass.
7. Completed-domain and final-run resumes recursively verify every referenced
   fold, row-table, bootstrap, snapshot, error-ledger, stdout/stderr, verifier,
   and commit-marker hash and recompute all gates/verdicts from the bound raw
   arrays before returning `COMPLETE`.
8. Every verifier launch uses a fresh append-only asynchronous-error ledger;
   an earlier failed verifier cannot poison or be erased by a later attempt.
   Fresh and recovered-uncommitted completion markers are launch-unique. If a
   later invocation recursively validates an already committed chain, it
   returns the existing marker unchanged rather than creating a shallow wrapper
   marker, making completed-run reuse idempotent.
9. Locks record an owner PID. A readable dead-owner lock may be atomically
   renamed to a unique append-only retirement record before one acquisition
   retry. A live, unreadable, malformed, or racing lock is never removed and
   causes a fail-closed refusal.
10. Append-only JSON, including PID handshakes, authorizations, reports, and
    markers, is serialized and fsynced under a unique same-directory temporary
    name before one atomic, no-overwrite publication. Readers never accept a
    partially serialized final pathname.

## Coordination

GPU jobs must hold `experiments/GPU_EXPERIMENT.lock` for the full process and
must refuse launch when another compute process owns the GPU. Before returning
a final result, drain all subagents so completed-agent UI routing cannot race a
still-streaming response.

CPU outcome jobs must likewise hold their experiment-specific runner lock, and
the Windows launcher must hold a separate outer lock across the runner,
post-exit verifier, and marker commit. Concurrent direct or launcher execution
is refused.
