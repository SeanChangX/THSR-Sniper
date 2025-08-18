#!/usr/bin/env python3

from thsr_py.cli import parse_args
from thsr_py.flows import run, show_station, show_time_table


def main() -> None:
    args = parse_args()

    if args.times:
        show_time_table()
        return

    if args.stations:
        show_station()
        return

    run(args)


if __name__ == "__main__":
    main()
