#!/usr/bin/env python3

from sys import argv, exit, stderr
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass
from subprocess import run
from zipfile import ZipFile
from hashlib import sha1


@dataclass
class Config:
	target: Path
	output: Path
	include: list[str]
	dry_run: bool
	git_files: bool


def __main(raw_args: list[str]) -> None:
	config = parse_and_validate_args(raw_args)

	archivable_files = get_archivable_files(config)
	if len(archivable_files) == 0:
		raise Exception("No archivable files")

	archive_path = get_archive_path(config.output, config.target, archivable_files)

	create_archive(config.dry_run, archive_path, archivable_files)


def parse_and_validate_args(raw_args: list[str]) -> Config:
	parser = ArgumentParser(prog="archive")
	parser.add_argument("target", type=Path, default=Path.cwd(), nargs="?", help="The target directory to archive")
	parser.add_argument("-o", "--output", type=Path, default=Path.cwd(), nargs="?", help="Location to place the resulting archive")
	parser.add_argument("-n", "--dry-run", action="store_true", help="Prints the files which would be included, but doesn't create the actual archive")
	parser.add_argument("--git-files", action="store_true", help="Use git to create the file list, includes all non-ignored files and the .git subdirectory")
	parser.add_argument("-i", "--include", action="append", default=[], help="Specify a file to include, even if it is not tracked by git")
	parser.add_help = True
	pargs = parser.parse_args(raw_args)

	config = Config(target=pargs.target,
								  output=pargs.output,
									include=pargs.include,
									dry_run=pargs.dry_run,
									git_files=pargs.git_files)

	# validate target
	if not config.target.exists():
		raise Exception(f"specified target \"{config.target}\" doesn't exist")

	# validate output
	if not config.output.exists():
		raise Exception(f"specified output location \"{config.output}\" doesn't exist")
	elif config.output.is_file():
		raise Exception(f"specified output location \"{config.output}\" isn't a directory")

	# validate git_files flag
	if config.git_files and not is_git_directory(config.target):
		raise Exception(f"specified target \"{config.target}\" isn't a git repository")

	return config


def is_git_directory(dir: Path) -> bool:
	git_dir = dir / ".git"
	return git_dir.is_dir()


def get_archivable_files(config: Config) -> list[Path]:
	all_files = list(filter(lambda p: p.is_file(), config.target.rglob("*")))

	if config.git_files:
		git_files = get_git_files(git_dir=config.target)
		archivable_files = []
		for file in all_files:
			# is git tracked file
			is_tracked_by_git = file_list_contains(git_files, file)
			if is_tracked_by_git:
				archivable_files.append(file)
				continue
			# is in .git directory
			if ".git" in str(file):
				archivable_files.append(file)
				continue
			# is user-included
			for include in config.include:
				if file.match(include):
					archivable_files.append(file)
					break
		return archivable_files
	
	else:
		return all_files


def file_list_contains(file_list: list[Path], file: Path) -> bool:
	return any([ p == file for p in file_list ])


def get_git_files(git_dir: Path) -> list[Path]:
	# tracked files
	subproc = run(["git", "ls-files"], cwd=git_dir, capture_output=True)
	subproc_stdout = [ p.decode("utf-8") for p in subproc.stdout.splitlines() ]
	tracked_files = [ Path(p) for p in subproc_stdout ]

	# untracked files (not including ignored files)
	subproc = run(["git", "ls-files", "--others", "--exclude-standard"], cwd=git_dir, capture_output=True)
	subproc_stdout = [ p.decode("utf-8") for p in subproc.stdout.splitlines() ]
	untracked_files = [ Path(p) for p in subproc_stdout ]

	return tracked_files + untracked_files


def get_archive_path(output: Path, target: Path, files: list[Path]) -> Path:
	target_name = target.absolute().name

	archive_hash = sha1()
	for archive_file in sorted(files):
		archive_hash.update(archive_file.read_bytes())
	archive_sha = archive_hash.hexdigest()

	return output / f"{target_name}-{archive_sha}.zip"


def create_archive(dry_run: bool, archive_path: Path, files: list[Path]):
	if dry_run:
		print_dry_run_output(archive_path, files)
	else:
		with ZipFile(archive_path, mode="w") as archive:
			for file in files:
				archive.write(file)


def print_dry_run_output(archive_path: Path, files: list[Path]) -> None:
	print(f"Output at: {archive_path}")
	print()
	print("Writing files:")
	for file in files:
		print(f"\t{file}")


if __name__ == "__main__":
	try:
		__main(argv[1:])
	except Exception as err:
		print(f"Error: {err}", file=stderr)
		exit(1)
