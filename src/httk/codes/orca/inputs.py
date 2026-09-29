"""Write ORCA input files for molecules."""

import math
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

__all__ = ["write_orca_input"]


def write_orca_input(
    path: str | os.PathLike[str],
    *,
    atoms: Sequence[tuple[str, float, float, float]] | str | os.PathLike[str],
    keywords: str | Sequence[str] = "B3LYP def2-SVP",
    charge: int = 0,
    multiplicity: int = 1,
    nprocs: int | None = None,
    maxcore_mb: int | None = None,
    blocks: Mapping[str, str] | None = None,
) -> Path:
    """Write an ORCA input for one molecule.

    The input is the simple-input line ``! KEYWORDS``, the optional ``%pal``
    and ``%maxcore`` settings, the given ``%`` blocks, and the Cartesian
    coordinate block ``* xyz CHARGE MULTIPLICITY`` ... ``*`` in Å. Coordinates
    are written as the shortest ``repr`` of each float, so they round-trip.

    :param path: Write the input file to this path.
    :param atoms: The atoms as ``(symbol, x, y, z)`` tuples in Å, or the path of an
        ``.xyz`` file (count line, comment line, then ``symbol x y z`` lines).
    :param keywords: The simple-input keywords, as one string or a sequence of keywords.
    :param charge: The total charge.
    :param multiplicity: The spin multiplicity 2S+1.
    :param nprocs: Write ``%pal nprocs N end`` when set.
    :param maxcore_mb: Write ``%maxcore MB`` (memory per process) when set.
    :param blocks: Additional input blocks as ``{name: body}``, written as ``%name``,
        the body, and ``end``, e.g. ``{"scf": "MaxIter 200"}``.
    :return: The written path.
    :raises ValueError: If the keywords, atoms or a numeric setting are invalid.
    """

    line = keywords if isinstance(keywords, str) else " ".join(keywords)
    if not line.strip() or "\n" in line:
        raise ValueError(f"keywords must be a nonempty single line, not {keywords!r}")
    if not _is_int(charge):
        raise ValueError(f"charge must be an integer, not {charge!r}")
    for name, value in (("multiplicity", multiplicity), ("nprocs", nprocs), ("maxcore_mb", maxcore_mb)):
        if value is not None and not (_is_int(value) and value >= 1):
            raise ValueError(f"{name} must be a positive integer, not {value!r}")
    blocks = dict(blocks or {})
    for name in blocks:
        if not name.isidentifier():
            raise ValueError(f"block name must be an identifier, not {name!r}")
        if (name.lower() == "pal" and nprocs is not None) or (name.lower() == "maxcore" and maxcore_mb is not None):
            raise ValueError(f"the {name} block conflicts with the matching keyword argument")
    rows = _read_xyz(Path(atoms)) if isinstance(atoms, str | os.PathLike) else list(atoms)
    if not rows:
        raise ValueError("the molecule has no atoms")
    lines = [f"! {line.strip()}"]
    if nprocs is not None:
        lines.append(f"%pal nprocs {nprocs} end")
    if maxcore_mb is not None:
        lines.append(f"%maxcore {maxcore_mb}")
    for name, body in blocks.items():
        lines += [f"%{name}", *(f"  {item.strip()}" for item in body.strip().splitlines()), "end"]
    lines.append(f"* xyz {charge} {multiplicity}")
    for row in rows:
        if len(row) != 4 or not isinstance(row[0], str) or not row[0].isalnum():
            raise ValueError(f"an atom must be (symbol, x, y, z), not {row!r}")
        coordinates = [float(x) for x in row[1:]]
        if not all(math.isfinite(x) for x in coordinates):
            raise ValueError(f"atom coordinates must be finite, not {row!r}")
        lines.append(" ".join([row[0], *(repr(x) for x in coordinates)]))
    lines += ["*", ""]
    destination = Path(path)
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _read_xyz(path: Path) -> list[tuple[str, float, float, float]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        count = int(lines[0])
        rows = [line.split() for line in lines[2 : 2 + count]]
        atoms = [(row[0], float(row[1]), float(row[2]), float(row[3])) for row in rows]
    except (IndexError, ValueError) as exception:
        raise ValueError(f"{path} is not an .xyz file: {exception}") from None
    if len(atoms) != count:
        raise ValueError(f"{path} declares {count} atoms but lists {len(atoms)}")
    return atoms
