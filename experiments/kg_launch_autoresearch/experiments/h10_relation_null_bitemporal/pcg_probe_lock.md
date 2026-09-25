# H10A isolated PCG64DXSM probe lock

Status: `LOCKED_H10A_PCG_PROBE_ONLY`

Scope: `PROBE_ONLY_NO_REAL_INPUTS`

Protocol-SHA256: `D6083A0BE49DF3C8771F99882DC0A957E81B3DB7E60BFADA47E770CC52E4CEF3`

Runner-SHA256: `1EFCEC2BFEA4C0D95387791EE4E9D38B2C576147FF0FAC234144F1A1FB6B7AA2`

Launcher-SHA256: `52C80D090A8A24255625A7D6ECAF6343E9E7E7E6D3D3EA7C4B08A8AFF813FA43`

Base-Interpreter-SHA256: `4F461F0C0DE64E82EB54FBCED0FD1D678D79D34EDA38660B07781E2BBA8064D6`

Venv-Launcher-SHA256: `BAD34B1F39DAD6A375E594AAF006FE84CD96A7AE46F6F2FA84C0536003234AC9`

Venv-Config-SHA256: `A59AE8BCAFF3472F99A259F89DFF2BE70AB8674AADEB5B26D574A237A7FF2426`

Python-Version: `3.12.13`

NumPy-Version: `2.4.4`

The launcher may use this lock only in `Probe` mode. The isolated probe may
read the protocol, runner, launcher, this lock, the hash-bound interpreter and
virtual-environment metadata. It may not read the independent verifier,
synthetic generator or fixture, implementation lock, permitted real inputs,
outcomes, or H6 Phase-B artifacts. The probe result is not known or recorded in
this prospective lock.
