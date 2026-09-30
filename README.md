# httk-workflow-orca

![Status: Early beta](https://img.shields.io/badge/status-early--beta-orange)

> **⚠️ EARLY BETA**
>
> This is an early beta release of *httk₂*. The organization of the packages
> and their APIs should not yet be regarded as stable, and may change between
> releases.

*httk-workflow-orca* adds [ORCA](https://www.faccts.de/orca/) quantum-chemistry
support to [*httk-workflow*](https://github.com/httk/httk-workflow), the
workflow engine of [*httk₂*](https://github.com/httk/httk2). It provides
`httk.codes.orca`: writing molecular ORCA inputs, parsing its output, stable
diagnostics, supervised execution with a classified run report, and helpers
for reading workflow outputs; and the Bash API that exposes the same helpers to
Bash runners. Installing it registers the `orca` code with *httk₂*; nothing
needs to be configured. ORCA itself is proprietary and not included.

> **Mostly synthetic fixtures.** The output parsers are validated against
> hand-written synthetic fixtures that follow ORCA 5/6's documented output
> markers, anchored by two real ORCA 6 outputs from cclib's test data (a
> converged single point and a converged geometry optimization). The failure
> paths (unconverged SCF, error termination, input error) are checked against
> synthetic fixtures only, until someone with an ORCA license runs the
> end-to-end test.

## Install

```console
python -m pip install httk-workflow-orca
```

## Use

In a Python runner (give ORCA by its absolute path; ORCA needs that for
parallel runs):

```python
from httk.codes.orca import run_orca, write_orca_input

write_orca_input("orca.inp", atoms="water.xyz", keywords="B3LYP def2-SVP")
report = run_orca(["/opt/orca/orca"])
print(report.classification, report.result.final_energy_ev)
```

In a Bash runner, whose manager exports the path of the ORCA API:

```bash
source "$HTTK_WORKFLOW_BASH_API"
: "${HTTK_WORKFLOW_ORCA_BASH_API:?install httk-workflow-orca}"
source "$HTTK_WORKFLOW_ORCA_BASH_API"
httk_orca_run -- /opt/orca/orca
energy=$(httk_orca_energy --unit ev)
```

A complete example workflow package, `orca.singlepoint`, is in
[`workflows/orca-singlepoint`](workflows/orca-singlepoint); `httk plugin
install` of this repository installs it. The API is documented in
[`docs/usage.md`](docs/usage.md) and at
[docs.httk.org/httk-workflow-orca](https://docs.httk.org/httk-workflow-orca/).

## Running tests

`make test` runs the normal profile; `make ci` runs formatting, lint, both type
checkers and the extended tests. The workflow test with a Python stand-in for
ORCA always runs. The end-to-end test runs a real ORCA only when
`HTTK_TEST_ORCA_COMMAND` names it (an absolute path), and skips otherwise;
there is no `PATH` lookup, because `orca` on `PATH` is often the GNOME screen
reader.
