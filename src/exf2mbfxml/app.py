import os
import sys
import argparse

from exf2mbfxml.reader import read_exf
from exf2mbfxml.result_codes import FAILED_TO_READ_EXF, MISSING_INPUT_FILE, SUCCESS
from exf2mbfxml.writer import write_mbfxml


def main():
    options = {}
    args = parse_args()
    if os.path.exists(args.input_exf):
        if args.output_mbf is None:
            output_mbf = args.input_exf + '.xml'
        else:
            output_mbf = args.output_mbf

        contents = read_exf(args.input_exf)
        if contents is None:
            return FAILED_TO_READ_EXF
        else:
            write_mbfxml(output_mbf, contents, options)
    else:
        return MISSING_INPUT_FILE

    return SUCCESS


def parse_args():
    parser = argparse.ArgumentParser(description="Transform exf format to Neurolucida XML data file.")
    parser.add_argument("input_exf", help="Location of the input exf file.")
    parser.add_argument("--output-mbf", help="Location of the output MBF XML file."
                                             "[defaults to the location of the input file if not set.]")

    return parser.parse_args()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
