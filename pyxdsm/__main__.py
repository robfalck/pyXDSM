"""Command-line interface for pyXDSM."""

import argparse
import json
import sys
from pathlib import Path

from pyxdsm import __version__
from pyxdsm.XDSM import XDSM
from pyxdsm.matrix_eqn import MatrixEquation
from pydantic import ValidationError


def _load_from_json(data: dict):
    """Load JSON as either XDSM or MatrixEquation."""
    try:
        return XDSM(**data), "xdsm"
    except ValidationError:
        pass
    
    try:
        return MatrixEquation(**data), "matrix_equation"
    except ValidationError:
        pass
    
    raise ValueError("JSON does not match XDSM or MatrixEquation schema")


def main():
    """Main entry point for the pyXDSM command-line interface."""
    parser = argparse.ArgumentParser(
        prog="pyxdsm",
        description="Python script to generate PDF XDSM diagrams using TikZ and LaTeX",
    )

    parser.add_argument("filename", 
                        help="The JSON file containing the representation of "
                        "an XDSM or matrix equation to be loaded.")

    parser.add_argument("-o", "--outfile",
                        default=None,
                        help="The output file to which the XDSM or matrix equation should be written. "
                             "Defaults to the input filename with the extension removed.")

    parser.add_argument("-v", "--version",
                        action="version",
                        version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    if args.filename:
        if args.outfile is None:
            args.outfile = Path(args.filename).stem
        try:
            xdsm = XDSM.from_json(args.filename)
            xdsm.write(args.outfile, quiet=True)
        except ValidationError:
            try:
                mat_eqn = MatrixEquation.from_json("args.filename")
                mat_eqn.write(args.outfile, quiet=True)
            except ValidationError:
                raise IOError("The given file {args.filename} is not a valid JSON representation of an XDSM or MatrixEquation.") 



if __name__ == "__main__":
    main()
