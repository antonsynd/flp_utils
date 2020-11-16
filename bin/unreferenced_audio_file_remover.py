#!/usr/bin/env python3

import sys
sys.path.append('../src')

import argparse
import collections
import flp_utils
import glob
import logging
import os
import re
import sys

from pathlib import Path

_logger = logging.getLogger('flp')
_stdout_handler = logging.StreamHandler(sys.stdout)
_logger.addHandler(_stdout_handler)

_default_audio_file_types = 'wav,mp3,aiff'
_audio_file_type_pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9]*$')


def get_flp_paths(flp_args: list) -> list:
    flp_paths = []

    for flp_arg in flp_args:
        flp_paths.extend(glob.glob(flp_arg, recursive=True))

    return [Path(x) for x in flp_paths if os.path.isfile(x)]


def get_audio_file_types(s: str) -> list:
    audio_file_types = s.strip().split(',')
    valid_file_types = []

    for audio_file_type in audio_file_types:
        if _audio_file_type_pattern.match(audio_file_type):
            valid_file_types.append(audio_file_type)

    if not valid_file_types:
        return _default_audio_file_types.split(',')

    return valid_file_types


def parse_variable_definition(s: str, d: dict) -> None:
        var_name, var_val = s.split('=')
        var_path = Path(var_val)

        if not var_path.exists():
            _logger.warning(f'path in variable {var_name} does not exist: '
                            f'{var_val}')

        d[var_name.rstrip()] = Path(var_val)


def read_configuration_file(config_path: str) -> dict:
    config_vars = {}

    if not config_path:
        return config_vars

    with open(config_path, mode='r') as config_file:
        for i, line in enumerate(config_file, start=1):
            line = line.strip()
            try:
                parse_variable_definition(line, config_vars)
            except ValueError:
                _logger.warning(f'invalid variable definition at '
                                f'line {i}: {line}')

    return config_vars


def parse_path_variables(var_list: list) -> dict:
    option_vars = {}

    if not var_list:
        return option_vars

    for var_def in var_list:
        var_def = var_def.strip()
        try:
            parse_variable_definition(var_def, option_vars)
        except ValueError:
            _logger.warning(f'invalid variable definition: {var_def}')

    return option_vars


def get_audio_file_paths_from_flps(flp_paths: list, path_vars: dict) -> list:
    audio_file_paths = []

    for flp_path in flp_paths:
        with open(flp_path, mode='rb') as flp_file:
            flp_data = flp_file.read()

            # FIXME: There may be relative paths here
            audio_file_paths.extend(
                flp_utils.dump_audio_files(flp_data, path_vars))

    return audio_file_paths


def verify_audio_files(audio_files: list) -> tuple:
    verified_audio_files = []
    unresolved_vars = collections.OrderedDict()

    var_pattern = re.compile(r'%([^%\s]+)%')

    for audio_file in audio_files:
        res = var_pattern.match(audio_file, 0)

        if res:
            unresolved_vars[res.group(1)] = None

        p = Path(audio_file)

        try:
            if not p.exists():
                _logger.debug(f'audio file does not exist {p}')
                continue
        except OSError as e:
            _logger.debug(f'encountered error while verifying {p}: {e}')
            continue

        verified_audio_files.append(p)

    return verified_audio_files, unresolved_vars


def get_audio_file_paths_from_audio_dirs(audio_dirs: list, audio_file_types: list) -> list:
    audio_file_paths = []

    for audio_dir in audio_dirs:
        for audio_file_type in audio_file_types:
            audio_file_paths.extend(Path(audio_dir).glob(
                f'*.{audio_file_type}'))

    return audio_file_paths


def get_files_to_process(flp_audio_files: list, all_audio_files: list) -> list:
    # FIXME: Maybe want to double check that we have absolute paths?
    flp_audio_file_set = set(flp_audio_files)
    all_audio_file_set = set(all_audio_files)

    return sorted(all_audio_file_set - flp_audio_file_set)


def delete_files(audio_files: list, dry_run: bool) -> None:
    for audio_file in audio_files:
        # Make sure we are not doing any weird relative path stuff
        # or raising errors by removing directories
        if os.path.isabs(audio_file) and os.path.isfile(audio_file):
            if dry_run:
                print(f'DRY RUN: Deleting {audio_file}')
            else:
                _logger.info(f'deleting {audio_file}')
                os.remove(audio_file)


def move_files(audio_files: list, destination: Path, dry_run: bool) -> None:
    destination = destination.absolute()

    if not destination.exists():
        if dry_run:
            print(f'DRY RUN: Creating destination directory {destination}')
        else:
            destination.mkdir(parents=True, exists_ok=True)

    for audio_file in audio_files:
        # Make sure we are not doing any weird relative path stuff
        # or raising errors by removing directories
        if audio_file.is_file() and audio_file.is_absolute():
            file_name = audio_file.name
            new_file_path = destination / file_name

            if new_file_path.is_file():
                if dry_run:
                    print(f'DRY RUN: Destination file already exists. '
                          f'Cannot move {audio_file} to {new_file_path}',
                          file=sys.stderr)
                else:
                    print(f'Destination file already exists. '
                          f'Cannot move {audio_file} to {new_file_path}',
                          file=sys.stderr)
                continue

            if dry_run:
                print(f'DRY RUN: Moving {audio_file} to {new_file_path}')
            else:
                _logger.info(f'moving {audio_file} to {new_file_path}')
                audio_file.rename(new_file_path)


def dir_path(s: str) -> str:
    p = Path(s)

    if p.exists() and p.is_dir():
        return s

    raise argparse.ArgumentTypeError(f'{s} is not a valid directory')


def add_common_args(p: argparse.ArgumentParser) -> None:
    cmd = p.prog.split()[-1]

    p.add_argument('flps',
        nargs='+', type=str,
        help='Path to an .flp file or a directory containing them. '
             'Supports recursive globbing. Repeatable.')
    p.add_argument('-a', '--audio-dir',
        dest='audio_dirs', action='append', type=dir_path, required=True,
        help=f'Directory containing audio files to {cmd} if they are '
             f'unreferenced. Does not go into subdirectories. '
             f'Repeatable.')
    p.add_argument('-t', '--audio-file-types',
        dest='audio_file_types', type=str, default=_default_audio_file_types,
        help=f'Comma-delimited list of audio file extensions to {cmd}. '
             f'Defaults to {_default_audio_file_types}.')
    p.add_argument('-v', '--var',
        dest='variables', action='append', type=str,
        help='Variable name and value pair, e.g. '
             'USERDIRECTORY=/User/Example/Documents. Repeatable.')
    p.add_argument('-c', '--config',
        dest='config_path', type=str, default=None,
        help='Path to configuration file containing a variable '
             'definition per line, in the same format as -v/--var.')
    p.add_argument('--dry-run',
        dest='dry_run', action='store_true',
        help='Performs a dry run, printing out what actions would be taken '
             'without actually performing them.')
    p.add_argument('--verbose',
        dest='verbose_mode', action='store_true',
        help='Output verbose information.')
    p.add_argument('--debug',
        dest='debug_mode', action='store_true',
        help='Outputs debug information. Implies --verbose.')
    p.add_argument('-x', '--experimental',
        dest='experimental_mode', action='store_true',
        help='Enables untested features.')


_DELETE_COMMAND = 'delete'
_DELETE_DESCRIPTION = 'Deletes unreferenced audio files, moving them to trash.' 
_MOVE_COMMAND = 'move'
_MOVE_DESCRIPTION = 'Moves unreferenced audio files.'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='cmd',
        help='sub-command help')
    subparsers.required = True

    delete_parser = subparsers.add_parser(_DELETE_COMMAND,
        description=_DELETE_DESCRIPTION,
        help=_DELETE_DESCRIPTION)
    # TODO: Make delete move items to trash/recycle bin by default and require
    # -f/--force to permanently delete the files
#    delete_parser.add_argument('-f', '--force',
#        dest='force', action='store_true',
#        help='Permanently deletes unreferenced audio files instead of moving '
#             'them to trash. Defaults to moving to trash.')
    add_common_args(delete_parser)

    move_parser = subparsers.add_parser(_MOVE_COMMAND,
        description=_MOVE_DESCRIPTION,
        help=_MOVE_DESCRIPTION)
    move_parser.add_argument('destination',
        type=dir_path,
        help='Directory to move unreferenced audio files to.')
    add_common_args(move_parser)

    args = parser.parse_args()

    if args.verbose_mode:
        _logger.setLevel(logging.INFO)

    if args.debug_mode:
        _logger.setLevel(logging.DEBUG)

    flp_paths = get_flp_paths(args.flps)

    audio_file_types = get_audio_file_types(args.audio_file_types)

    path_vars = {}
    path_vars.update(read_configuration_file(args.config_path))
    path_vars.update(parse_path_variables(args.variables))

    _logger.info('Using the following path variables:')

    for var_name, var_val in path_vars.items():
        _logger.info(f'\t{var_name}={var_val}')

    flp_audio_files = get_audio_file_paths_from_flps(flp_paths, path_vars)
    flp_audio_files, unresolved_vars = verify_audio_files(flp_audio_files)

    if unresolved_vars:
        _logger.warning('The following variables are not defined:')

        for k in unresolved_vars.keys():
            _logger.warning(f'\t{k}')

    audio_dir_files = get_audio_file_paths_from_audio_dirs(
        args.audio_dirs,
        audio_file_types)

    files_to_process = get_files_to_process(flp_audio_files, audio_dir_files)

    cmd = args.cmd

    # TODO: Experimental mode required to run anything for real
    # (otherwise dry-run)
    if args.experimental_mode:
        _logger.warning('experimental mode enabled. '
                        'untested functionality will be used')
    else:
        _logger.info('experimental model is not enabled. assuming dry run')
        args.dry_run = True

    if cmd == _DELETE_COMMAND:
        delete_files(files_to_process, args.dry_run)
    elif cmd == _MOVE_COMMAND:
        move_files(files_to_process, Path(args.destination), args.dry_run)
