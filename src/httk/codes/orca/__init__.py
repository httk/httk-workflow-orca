"""ORCA quantum-chemistry support for *httk₂* workflows: the *httk-workflow-orca* package.

``inputs`` writes molecular ORCA inputs, ``outputs`` parses its text output,
``diagnostics`` classifies a finished calculation, ``reports`` runs it under
supervision, and ``collect`` reads workflow outputs out of result files, for
workflow collect hooks. This package is a thin facade re-exporting their
surface. The example workflow
package ``workflows/orca-singlepoint`` in this distribution's repository
builds on it. The parsers are validated against synthetic output fixtures and
two real ORCA 6 outputs (a single point and a geometry optimization).
"""

from httk.core import register_citation

register_citation(
    applies_to="Calculations with ORCA",
    references=(
        {
            "authors": ({"name": "Frank Neese"},),
            "title": "Software update: The ORCA program system—Version 5.0",
            "journal": "WIREs Computational Molecular Science",
            "volume": "12",
            "pages": "e1606",
            "year": "2022",
            "doi": "10.1002/wcms.1606",
            "bib_type": "article",
        },
    ),
)

from .diagnostics import diagnose_orca
from .inputs import write_orca_input
from .outputs import EH_TO_EV, OrcaResult, parse_orca_output
from .reports import OrcaRunReport, run_orca

__all__ = [
    "EH_TO_EV",
    "OrcaResult",
    "OrcaRunReport",
    "diagnose_orca",
    "parse_orca_output",
    "run_orca",
    "write_orca_input",
]
