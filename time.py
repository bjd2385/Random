#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Estimate the amount of time it's going to take to complete offsite sync.

I've had a number of partners ask me whether they should order a RoundTrip.
I'd like to give them an estimate of how long it's going to take, given
current settings/bandwidth, to catch up, so that they can make that decision.

© Brandon Doyle, 2018
"""

# TODO: Take modifications of retention and backups into account
# TODO: Implement EWMA to upload series

import sys

major = sys.version_info.major
minor = sys.version_info.minor
if major < 3:
    raise Exception('Must use Python 3, you\'re using Python {}'.format(major))
elif minor < 5:
    # Function type annotations
    raise Exception('Must use Python 3.5+, you\'re using Python 3.{}'\
            .format(minor))

from typing import List, Dict, Optional, Any
from subprocess import PIPE, Popen
from functools import partial
from os.path import basename

import warnings
import argparse
import datetime
import os
import re

# Regexes
spaces   = re.compile(r'[\s\t]+')
newlines = re.compile(r'\n+')
epoch    = re.compile(r'(?<=@)[0-9]+')
schedule = re.compile(r'\"0\";i:[0-9]{1,3};') # pluck out hours of backups
transfer = re.compile(r'[0-9]+(?=:)')
pauses   = re.compile(r'pause')

# Shell
ZFS_agent_list = 'zfs list -H -o name'
ZFS_list_snapshots = 'zfs list -t snapshot -Hrp -o name,written,compressratio'
SS_Options = 'speedsync options'

# Key path and extensions
KEYS = '/datto/config/keys/'
SPEEDSYNC_OPTIONS = '/datto/config/sync/*+{}+agent/options'

# local
LOCAL_RETENTION   = '.retention'        # split(':')
LOCAL_SCHEDULE    = '.schedule'         # `schedule`
BACKUP_INTERVAL   = '.interval'         # Just a number, minutes

# offsite
OFFSITE_RETENTION = '.offsiteRetention' # split(':')
OFFSITE_SCHEDULE  = '.offsiteSchedule'  # `schedule`
OFFSITE_POINTS    = '.offSitePoints'    # Just numbers
TRANSFERS_DONE    = '.transfers'        # `transfer`

# Other configs
SPEED_LIMIT = '/datto/config/local/speedLimit' # Upload speed limit

NOW = datetime.datetime.now()


def getIO(command: str) -> List[str]:
    """
    Get results from terminal commands as lists of lines of text.
    """
    with Popen(re.split(spaces, command), stdin=PIPE, stdout=PIPE) as proc:
        stdout, stderr = proc.communicate()
    
    if stderr:
        raise ValueError('Command exited with errors: {}'.format(stderr))

    # Further processing
    if stdout:
        stdout = re.split(newlines, stdout.decode())
    
    return stdout


def getSnapshots(agent: str) -> Dict[int, str]:
    """
    Get a list of snapshots from a particular agent.
    """
    snapshots = getIO(ZFS_list_snapshots + ' ' + agent)[:-1]

    for i, snapshot in enumerate(snapshots):
        snapshots[i] = re.split(spaces, snapshot)
        
        # Pull out relevant data for readability
        epochInt = int(re.search(epoch, snapshot).group())
        compressRatio = float(snapshots[i][2][:-1])
        epochSize = int(snapshots[i][1])

        # Reorganize this list as [epoch, transfer size]
        snapshots[i] = [epochInt, int(epochSize * compressRatio)]

    return dict(snapshots)


def flatten(inList: List[List]) -> List:
    """
    Similar to Haskell's `concat :: [[a]] -> [a]`.
    """
    flatList = []
    for subList in inList:
        for string in subList:
            flatList.append(string)
    return flatList


class InvalidArrayFormat(SyntaxError):
    """
    Raised when the input "compressed" JSON format is invalid.
    """


class ConvertJSON:
    """
    Methods for working on our (*ahem* horrid) JSON.
    """

    # Match these 'tokens'
    integer = r'^i:[0-9]+;?'
    string  = r'^s:[0-9]+:\"[^\"]*\";?'
    array   = r'^a:[0-9]+:{'
    boolean = r'^b:[01];?'
    endArr  = r'^}'

    lexer = re.compile('({}|{}|{}|{}|{})'.format(integer, string, array, endArr,
                                                 boolean))

    # `:' between parentheses will break unpacking if we just `.split(':')`
    colonStringSplit = re.compile(r'(?<=s):|:(?=")')

    def decode(self, key: str) -> Dict:
        """
        Decode our JSON with regex into something a little nicer. In Python 3.5,
        if I'm not mistaken, dictionaries don't necessarily keep their order, so
        I've decided to use lists instead to unpack all of the keyData into.
        Then a second pass converts this list of lists ... into a dictionary of
        dictionaries ...
        """
        if not os.path.isfile(key):
            raise FileNotFoundError('File {} does not exist'.format(key))

        with open(key, 'r') as keykeyData:
            keyData = keykeyData.readline().rstrip()

        def nestLevel(currentList: Optional[List] =None) -> List:
            """
            Allow the traversal of all nested levels.
            """
            nonlocal keyData

            if currentList is None:
                currentList = []

            while keyData:
                # Can't wait till assignment expressions!
                result = re.search(self.lexer, keyData)

                if not result:
                    # Show what it's stuck on so we can debug it
                    raise InvalidArrayFormat(keyData)

                start, end = result.span()
                substring = keyData[:end]
                keyData = keyData[end:]

                if substring.endswith(';'):
                    substring = substring[:-1]

                # Parse. Everything comes in 2's
                if substring.startswith('a'):
                    currentList.append(nestLevel([]))
                elif substring.startswith('i'):
                    _, value = substring.split(':')
                    currentList.append(int(value))
                elif substring.startswith('s'):
                    _, _, value = re.split(self.colonStringSplit, substring)
                    value = value[1:len(value) - 1]
                    currentList.append(value)
                elif substring.startswith('b'):
                    _, value = substring.split(':')
                    currentList.append(bool(value))
                elif substring.startswith('}'):
                    return currentList
            return currentList

        def convert(multiLevelArray: List) -> Dict:
            """
            Convert our multi-level list to a dictionary of dictionaries ...
            """
            length = len(multiLevelArray)
            currentDict = {}

            for i, j in zip(range(0, length - 1, 2), range(1, length, 2)):
                key, val = multiLevelArray[i], multiLevelArray[j]
                if type(val) is list:
                    currentDict[key] = convert(val)
                else:
                    currentDict[key] = val

            return currentDict

        return convert(nestLevel()[0])

    @staticmethod
    def find(nestedDicts: Dict, key: Any) -> Any:
        """
        Return the first occurrence of value associated with `key`. O(n) for `n`
        items in the flattened data.
        """

        def traverse(nested: Dict) -> Any:
            nonlocal key
            for ky, value in list(nested.items()):
                if ky == key:
                    return value
                if type(value) is dict:
                    res = traverse(value)
                    if res:
                        return res

        return traverse(nestedDicts)

    @staticmethod
    def findAll(nestedDicts: Dict, key: Any, byValue: bool = False) -> List:
        """
        Return all occurrences of values associated with `key`, if any. Again,
        O(n). If `byValue`, searches by value and returns the associated keys.
        (Essentially a reverse lookup.)
        """
        occurrences = []

        def traverse(nested: Dict) -> None:
            nonlocal key, occurrences
            for ky, value in list(nested.items()):
                if byValue:
                    if value == key:
                        occurrences.append(ky)
                else:
                    if ky == key:
                        occurrences.append(value)
                if type(value) is dict:
                    traverse(value)

        traverse(nestedDicts)
        return occurrences


def decodeRetention(agent: str, offsite: bool =False) -> List[int]:
    """
    Read the retention policy for an agent from file.
    """
    # There's offsite and local retention policies on our appliances.
    with open(KEYS + agent + (OFFSITE_RETENTION if offsite
                              else LOCAL_RETENTION)) as cryptic_policy:
         policy = cryptic_policy.readline().split(':')

    # Now let's decode what's _really_ going to happen to this data. Everything
    # is dependent upon the last number in the 4-tuple.
    intra, daily, weekly, total = policy

    # intra: 1d - 31d
    # daily: 1w - 26w
    # weekly: 1m - 24m, or up to ~27 years (maxes out at 240000hrs)
    # total: 1w - 7y, or up to ~27 years, again

    return [intra, daily, weekly, total]


def main(arguments: argparse.Namespace) -> None:
    # Get a list of ZFS datasets/agents. Basically the same as
    # zfs list | awk '/(agents\/)/'
    datasets = list(getIO(ZFS_agent_list))
    agents = list(filter(lambda path: 'agents/' in path, datasets))

    # Check the requested agents against absolute list of agents
    if arguments.agents:
        arguments.agents = flatten(arguments.agents)
        for uuid in arguments.agents:
            if uuid not in agents:
                warnings.warn(uuid + ' is not in the dataset, excluding',
                              stacklevel=2, category=RuntimeWarning)
                arguments.agents.remove(uuid)
        if not arguments.agents:
            warnings.warn('Defaulting to complete dataset')
            arguments.agents = agents
    else:
        arguments.agents = agents

    agent_identifiers = list(map(basename, arguments.agents))

    # Grab data about snapshots and retention policies
    snaps = list(map(getSnapshots, arguments.agents))
    for snap in snaps:
        if not len(snap):
            warnings.warn(uuid + ' has no snapshots, excluding',
                          stacklevel=2, category=RuntimeWarning)
    local_ret_policies = list(map(decodeRetention, agent_identifiers))
    offsite_ret_policies = list(map(partial(decodeRetention, offsite=True),
                                             agent_identifiers))

    # Decode schedules and store them in a list.
    JSONdecoder = ConvertJSON()
    schedules = []
    for agent in agent_identifiers:
        schedules.append(JSONdecoder.decode(KEYS + agent + LOCAL_SCHEDULE))

    # Map these schedules to a function that'll find all the hours we're
    # taking backups. This is the same as
    # cat /datto/config/keys/*.schedule | grep -oP "[0-9]+(?=;s:1:\"0\")"
    backupHours = list(map(partial(JSONdecoder.findAll, key='0', byValue=True),
                           schedules))

    # Collect interval of backups.
    intervals = []
    for agent in agent_identifiers:
        intervalPath = KEYS + agent + BACKUP_INTERVAL
        with open(intervalPath, 'r') as intervalFile:
            intervals.append(int(intervalFile.readline().rstrip()))

    # Determine if any agents have offsite paused (or even if offsite is
    # paused in general).
    for agent in agent_identifiers:
        with open(SPEEDSYNC_OPTIONS.format(agent), 'r') as options:
            # Valid Python dictionary format (immutable : value)
            options = dict(options.readline().rstrip())
            for key, value in options.items():
                if (key == 'pauseZfs'      and value == 1) or \
                   (key == 'pauseTransfer' and value == 1):
                   warnings.warn(agent + ' is paused, excluding',
                                 stacklevel=2, category=RuntimeWarning)


    # Now we've collected the following information:
    #   . Interval of backups
    #   . Local and offsite backup schedules (list of each hour)
    #   . A list of agents to work with that are
    #       . not paused,
    #       . exist,
    #       . have snapshots,


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Estimate the amount of time it\'s going to take to '
                    'complete offsite sync.'
    )

    # It's okay to list arguments following `-a`, or use multiple `-a`'s.
    # They'll be `flattened` into the same list anyway.
    parser.add_argument('-a', '--agents', type=str, action='append', 
        nargs='+', help='Specific agents to test offsite sync.'
    )

    args = parser.parse_args()
    main(args)