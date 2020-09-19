#!/usr/bin/env python3

import sys
sys.path.append('../src')

import argparse
import flp_utils


def add_common_args(p):
    p.add_argument('flps',
        nargs='+', type=str,
        help='Path to an .flp file or a directory containing them. Repeatable.')
    p.add_argument('-v', '--var',
        dest='variables', action='append', type=str,
        help='Variable name and value pair, e.g. '
             'USERDIRECTORY=/User/Example/Documents. Repeatable.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='cmd',
        help='sub-command help')
    subparsers.required = True

    delete_parser = subparsers.add_parser('delete',
        help='Deletes unreferenced audio files, moving them to trash.')
    add_common_args(delete_parser)
    delete_parser.add_argument('-f', '--force',
        dest='force', action='store_true',
        help='Permanently deletes unreferenced audio files instead of moving '
             'them to trash. Defaults to moving to trash.')

    move_parser = subparsers.add_parser('move',
        help='Moves unreferenced audio files.')
    move_parser.add_argument('destination',
        type=str,
        help='Directory to move unreferenced audio files to.')
    add_common_args(move_parser)

    args = parser.parse_args()

    # take flps
    # load each one
    # get what audio files it references
    # take audio dirs
    # any audio files not referenced
    # either delete or move to a specified location
    # to be deleted later for example
