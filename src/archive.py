#!/usr/bin/env python3

from sys import argv, exit, stderr
from argparse import ArgumentParser


def main(args: list[str]) -> None:
	arg_parser = ArgumentParser(prog="archive", add_help=True)
	args = arg_parser.parse_args(args)
	return


if __name__ == "__main__":
	try:
		main(argv)
	except Exception as err:
		print("f{err}", file=stderr)
		exit(1)
