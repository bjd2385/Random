#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Estimate the amount of time it's going to take to complete offsite sync.

I've had a number of partners ask me whether they should order a RoundTrip.
I'd like to give them an estimate of how long it's going to take, given
current settings/bandwidth, to catch up, so that they can make that decision.

© Brandon Doyle, 2018
"""


from typing import List, Dict
from subprocess import PIPE, Popen
from functools import partial
from os.path import basename

import warnings
import argparse
import datetime
import re

# Regexes
spaces   = re.compile(r'[\s\t]+')
newlines = re.compile(r'\n+')
epoch    = re.compile(r'(?<=@)[0-9]+')
schedule = re.compile(r'\"0\";i:[0-9]{1,3};') # pluck out hours of backups

# Shell
ZFS_agent_list = 'zfs list -H -o name'
ZFS_list_snapshots = 'zfs list -t snapshot -Hrp -o name,written,compressratio'

# Key path and extensions
KEYS = '/datto/config/keys/'

LOCAL_RETENTION = '.retention'
OFFSITE_RETENTION = '.offsiteRetention'
BACKUP_SCHEDULE = '.schedule'
BACKUP_INTERVAL = '.interval'

NOW = datetime.datetime.now()

## Preflight checks; ensure all necessary reference files exist


## Collect data


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


def flatten(inList: List[List[str]]) -> List[str]:
    """
    Similar to Haskell's `concat :: [[a]] -> [a]`.
    """
    flatList = []
    for subList in inList:
        for string in subList:
            flatList.append(string)
    return flatList


def decode(str) -> Dict:
    """
    Decode our  
    """


def decodeRetention(agent: str, offsite: bool =False) -> List[int]:
    """
    Read the retention policy for an agent from file.
    """
    # There's offsite and local retention policies on our appliances.
    with open(KEYS + agent + (OFFSITE_RETENTION if offsite else LOCAL_RETENTION))\
            as cryptic_policy:
         policy = cryptic_policy.readline().split(':')

    # Now let's decode what's _really_ going to happen to this data
    intra, daily, total, local = list(map(lambda hrs: int(hrs) // 24, policy))

    # FIXME


def main(arguments: argparse.Namespace) -> None:
    # Get a list of ZFS datasets/agents
    datasets = list(getIO(ZFS_agent_list))
    agents = list(filter(lambda path: 'agents/' in path, datasets))

    # Check the requested agents against agents list
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

    # Get all the necessary data
    snaps = list(map(getSnapshots, arguments.agents))
    local_ret_policies = list(map(decodeRetention, arguments.agents))
    offsite_ret_policies = list(map(partial(decodeRetention, offsite=True),
                                             agent_identifiers))
    backup_schedule =


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)

    # It's okay to list arguments following `-a`, or use multiple `-a`'s.
    parser.add_argument('-a', '--agents', type=str, action='append', 
        nargs='+', help='Specific agents to test offsite sync for.'
    )

    args = parser.parse_args()
    main(args)