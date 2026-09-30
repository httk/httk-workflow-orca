# Using the ORCA helpers

*httk-workflow-orca* ships the ORCA helpers that workflow runners are built on,
in two languages: the Python package {py:mod}`httk.codes.orca` and the Bash ORCA
API, whose `httk_orca_*` functions call the same code through the
*httk-workflow* shell bridge.

```{warning}
ORCA is proprietary and was not available when this module was written. The
output parsers are validated against hand-written **synthetic fixtures** that
carry the documented ORCA 5/6 output markers, anchored by **two real ORCA 6
outputs** redistributed by cclib (a converged single point and a converged
geometry optimization; see the repository's `tests/data/README.md`). The
failure paths (unconverged SCF, error termination, input error) have no real
anchor until someone with an ORCA license runs the end-to-end test
(`HTTK_TEST_ORCA_COMMAND=/abs/path/to/orca make test`).
```

## Install

```console
python -m pip install httk-workflow-orca
```

The distribution depends on *httk-core* and *httk-workflow*. Installing it
registers the `orca` code through the `httk.registry.codes.orca` registration
package, which makes the `orca-*` bridge commands and the Bash API available to
every job the manager starts; nothing needs to be configured. ORCA itself is
not included: obtain it from its developers under their license.

## The ORCA command

ORCA is started as `orca INPUT > OUTPUT`. For parallel (`%pal`) runs ORCA
starts its own MPI processes and must then be invoked by its **absolute path**,
so give every ORCA command as an absolute path, e.g. `/opt/orca/orca`, never
`mpirun orca`. A bare `orca` on `PATH` is also often the unrelated GNOME screen
reader, which is why neither the example workflow nor the tests ever look ORCA
up on `PATH`.

## Python

```python
from httk.codes.orca import run_orca, write_orca_input

write_orca_input(
    "orca.inp",
    atoms="water.xyz",
    keywords="B3LYP def2-SVP",
    nprocs=4,
    maxcore_mb=2000,
    blocks={"scf": "MaxIter 200"},
)
report = run_orca(["/opt/orca/orca"], timeout=3600)
if report.ok:
    print(report.result.final_energy_ev)
else:
    print(report.classification, [item.code for item in report.diagnostics])
```

- {py:func}`~httk.codes.orca.write_orca_input` writes the simple-input line
  `! KEYWORDS`, optional `%pal nprocs N end` and `%maxcore MB`, further `%`
  blocks, and the `* xyz CHARGE MULTIPLICITY` ... `*` coordinate block (Å) from
  `(symbol, x, y, z)` tuples or an `.xyz` file.
- {py:func}`~httk.codes.orca.parse_orca_output` returns an
  {py:class}`~httk.codes.orca.OrcaResult`: the last `FINAL SINGLE POINT ENERGY`
  (Eh, and eV through `final_energy_ev`; `None` when the last SCF did not
  converge, so only a converged energy is ever reported), SCF convergence and
  cycle count of the last SCF, geometry-optimization convergence, whether ORCA
  terminated normally, and the error lines.
- {py:func}`~httk.codes.orca.run_orca` runs the command with the input file name
  appended under the *httk-workflow* process supervisor, saves standard output
  as `orca.out`, and returns an {py:class}`~httk.codes.orca.OrcaRunReport`
  classified as `completed`, `crashed`, `nonconverged`, `process_failure` or
  `timeout`, also written to `orca-run-report.json`.
- {py:func}`~httk.codes.orca.diagnose_orca` diagnoses a finished calculation.

## Diagnostics

| Code | Severity | Meaning |
| --- | --- | --- |
| `orca.input_error` | fatal | ORCA refused the input (`INPUT ERROR`, `UNRECOGNIZED OR DUPLICATED KEYWORD(S) IN SIMPLE INPUT LINE`); reported instead of the error termination it causes |
| `orca.error_termination` | fatal | `ORCA finished by error termination in <PROGRAM>` or `aborting the run`; the summary is the termination line |
| `orca.scf_not_converged` | error | the last SCF reported `SCF NOT CONVERGED AFTER n CYCLES` |
| `orca.optimization_not_converged` | error | a geometry optimization terminated normally without `THE OPTIMIZATION HAS CONVERGED` |
| `orca.incomplete` | error | neither `****ORCA TERMINATED NORMALLY****` nor an error termination, e.g. a killed process |

A converged, normally terminated calculation has no diagnostics.

## Bash

The manager exports the path of the ORCA API as `HTTK_WORKFLOW_ORCA_BASH_API`
when *httk-workflow-orca* is installed, so a Bash runner guards it and sources
it after the generic library:

```bash
source "$HTTK_WORKFLOW_BASH_API"
: "${HTTK_WORKFLOW_ORCA_BASH_API:?install httk-workflow-orca}"
source "$HTTK_WORKFLOW_ORCA_BASH_API"

httk_orca_write_input --options options.json   # the write_orca_input keywords as JSON
httk_orca_run --timeout 3600 -- /opt/orca/orca
energy=$(httk_orca_energy --unit ev)
```

| Function | Bridge command | Exit status |
| --- | --- | --- |
| `httk_orca_write_input --options FILE [--input orca.inp]` | `orca-write-input` | `0` |
| `httk_orca_run [--directory] [--input] [--output] [--timeout] -- CMD...` | `orca-run` | `0` completed, `20` crashed, `21` nonconverged, `22` process failure, `124` timeout (as `vasp-run`); prints the report path |
| `httk_orca_energy [--output orca.out] [--unit eh\|ev]` | `orca-energy` | `0` and the energy, `1` when there is none |
| `httk_orca_converged [--output orca.out]` | `orca-converged` | `0` SCF (and any optimization) converged, `1` otherwise |
| `httk_orca_diagnose [--output orca.out] [--json]` | `orca-diagnose` | `0` clean, `20` when it printed diagnostics |

A refused call (for example a missing output file) exits `2`. The API sets
`HTTK_ORCA_BASH_API_VERSION=1`.

## The example workflow

The repository's `workflows/orca-singlepoint` is the workflow package
`orca.singlepoint`: one Python runner step that stages the `molecule` input (an
`.xyz` file, staged as `molecule.xyz`), writes `orca.inp`, runs ORCA, and fails
with the first diagnostic code when the calculation is not clean. Install it
with `httk plugin install` of the repository, or use it directly with
`--workflow-dir`:

```console
httk workspace settings set --key orca.command --value /opt/orca/orca WORKSPACE
httk job new --workflow orca.singlepoint --input molecule=water.xyz \
    --parameter 'keywords="HF def2-SVP"'
httk workflow run
httk workflow collect --into results.sqlite
```

Its parameters are `keywords` (default `B3LYP def2-SVP`), `charge` (default 0)
and `multiplicity` (default 1). The setting `orca.command` is required and has
no default: without it the step fails with `orca.not_configured` rather than
guess (and possibly start the screen reader).

## Collecting

{py:func}`~httk.codes.orca.collect.read_total_energy` reads the final single
point energy of the molecule from an ORCA output file as a
{py:class}`httk.core.DataRecord` of the property
`https://schemas.httk.org/defs/v0.1/properties/core/total_energy` in eV. An
output without a converged energy, or of a geometry optimization that did not
converge, is refused.

The packaged workflow's `collect.py` hook shows how a workflow locates the file
with `record.result_file` and returns the role mapping; to collect more outputs,
add lines to your copy of the hook:

```python
from httk.codes.orca.collect import read_total_energy


def collect(record):
    return {"total_energy": read_total_energy(record.result_file("orca.out"))}
```
