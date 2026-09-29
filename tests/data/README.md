# Test data

ORCA is proprietary and was not run for this repository. The top-level `.out`
files are **synthetic fixtures written by hand** for these tests;
`real/` holds two real ORCA 6 outputs redistributed by cclib (below), which
anchor the markers. Each synthetic `.out` file is not program output, is not
copied from the ORCA manual or from any third-party output, and says so in its own header. It contains only the
ORCA 5/6 output markers the parsers read, laid out the way ORCA prints them,
around placeholder numbers. Beyond the two real outputs, the parsers are
validated against these markers only, until the end-to-end test is run with a
real, licensed ORCA (`HTTK_TEST_ORCA_COMMAND`). In particular the failure
markers (non-converged SCF, error termination, input error) have no real
anchor.

| File | What it models | Markers it carries |
| --- | --- | --- |
| `water.xyz` | water geometry (Å) for the inputs and the workflow | count line, comment line, `Sym x y z` lines |
| `water_sp.out` | converged HF/def2-SVP single point | `SCF CONVERGED AFTER  11 CYCLES`, `FINAL SINGLE POINT ENERGY       -75.960185412345`, `****ORCA TERMINATED NORMALLY****` |
| `water_scf_noconv.out` | SCF that stopped unconverged, run continued | `SCF NOT CONVERGED AFTER 125 CYCLES`, the `The SCF is NOT converged` warning block, normal termination, no energy line |
| `water_error.out` | SCF failure that aborts the run | `SCF NOT CONVERGED AFTER  50 CYCLES`, `aborting the run`, `ORCA finished by error termination in SCF` |
| `water_input_error.out` | misspelled basis set `def2-SVPP` | `INPUT ERROR` banner, `UNRECOGNIZED OR DUPLICATED KEYWORD(S) IN SIMPLE INPUT LINE` |
| `water_opt.out` | three-cycle converged geometry optimization | `GEOMETRY OPTIMIZATION CYCLE`, one `FINAL SINGLE POINT ENERGY` per cycle (the last, `-75.961098765432`, wins), `THE OPTIMIZATION HAS CONVERGED`, `*** OPTIMIZATION RUN DONE ***` |
| `water_truncated.out` | a killed process | the first 1500 bytes of `water_sp.out`: no energy line and no termination line |

Marker meanings: `FINAL SINGLE POINT ENERGY` is the total energy in Hartree
(Eh) of the last energy evaluation; `SCF [NOT ]CONVERGED AFTER n CYCLES` closes
each SCF; `****ORCA TERMINATED NORMALLY****` is the normal end of the run;
`ORCA finished by error termination in <PROGRAM>` and `aborting the run` mark a
failure of one ORCA program; `INPUT ERROR` and `UNRECOGNIZED OR DUPLICATED
KEYWORD(S) IN SIMPLE INPUT LINE` mark a refused input.

## Real outputs (`real/`)

Real ORCA 6 program output from the test data of
[cclib](https://github.com/cclib/cclib), redistributed under cclib's BSD
3-Clause License, whose text is in `real/LICENSE`. Both files are from cclib
commit `f90be37ffa1ab4cfec97495bdd01d670ca329f17`, unmodified except as noted.

| File | Source | What it is |
| --- | --- | --- |
| `real/water_hf_solvent_cpcm.out` | <https://raw.githubusercontent.com/cclib/cclib/f90be37ffa1ab4cfec97495bdd01d670ca329f17/data/ORCA/basicORCA6.0/water_hf_solvent_cpcm.log> (renamed from `.log`, which this repository's `.gitignore` ignores; sha256 `0ab19f6bc055ac91235f2703b7d0ef707c9be5e4d56aaa401d152ed09a9821b8`) | ORCA 6.0.1 HF/STO-3G CPCM single point of water: `SCF CONVERGED AFTER   9 CYCLES`, `FINAL SINGLE POINT ENERGY       -74.967672596588`, normal termination |
| `real/dvb_gopt.out.gz` | <https://raw.githubusercontent.com/cclib/cclib/f90be37ffa1ab4cfec97495bdd01d670ca329f17/data/ORCA/basicORCA6.0/dvb_gopt.out> (gzip-compressed; the uncompressed sha256 is `3f1722c8807dc5198f978119056cec1e16a02bca80ea0ef21d1d222ea0871c07`) | ORCA 6.0.0 geometry optimization of divinylbenzene: three `GEOMETRY OPTIMIZATION CYCLE`s, `THE OPTIMIZATION HAS CONVERGED`, a final single point (`-382.055133399486`, `SCF CONVERGED AFTER   3 CYCLES`), `*** OPTIMIZATION RUN DONE ***`, normal termination |
