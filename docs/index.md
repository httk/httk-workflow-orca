# *httk-workflow-orca*

This site documents the *httk-workflow-orca* module. For the full documentation
of *httk₂*, see [docs.httk.org](https://docs.httk.org).

The module adds ORCA quantum-chemistry support to *httk-workflow*: the Python
helpers in `httk.codes.orca` (input writing, output parsing, diagnostics,
supervised execution and a result collector), the Bash API a Bash runner sources
as `$HTTK_WORKFLOW_ORCA_BASH_API`, and the `orca-*` bridge commands behind that
API. Installing it registers the `orca` code with *httk₂* through the
`httk.registry.codes.orca` registration package. The repository also carries
the example workflow package `orca.singlepoint`. The output parsers are
validated against synthetic fixtures only; see {doc}`usage`.

```{admonition} Quick links
:class: tip

- {doc}`usage` — the Python and Bash API, the example workflow, and the diagnostics
- {doc}`reference/index` — the generated API reference
```

## Install

```console
python -m pip install httk-workflow-orca
```

```{toctree}
:maxdepth: 2
:caption: Documentation

usage
reference/index
```
