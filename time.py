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

import warnings
import argparse
import re

# Regexes
spaces   = re.compile(r'[\s\t]+')
newlines = re.compile(r'[(\r\n)\r\n]+')
epoch    = re.compile(r'(?<=@)[0-9]+')

# Shell
ZFS_agent_list = 'zfs list -H -o name'
ZFS_list_snapshots = 'zfs list -t snapshot -Hrp -o name,written,compressratio'

# Key variables
KEYS = '/datto/config/keys/'

RETENTION = '.retention'



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


def acquireRetentionPolicy(agent: str) -> str:
    """
    Read the retention policy for an agent from file.
    """
    with open(KEYS + agent + '.retention')


def main(arguments: argparse.Namespace) -> None:
    # Get a list of ZFS datasets/agents
    datasets = getIO(ZFS_agent_list)
    agents = list(filter(lambda path: 'agents/' in path, datasets))

    # Check the requested agents against agents list
    if arguments.agents:
        arguments.agents = flatten(arguments.agents)
        for uuid in arguments.agents:
            if uuid not in agents:
                warnings.warn(uuid + ' is not in the dataset, excluding',
                              stacklevel=2, category=RuntimeWarning)
                arguments.agents.remove(uuid)
    else:
        arguments.agents = agents

    # Get snapshot epochs and written size for these agents
    snaps = list(map(getSnapshots, arguments.agents))




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)

    # It's okay to list arguments following `-a`, or use multiple `-a`'s.
    parser.add_argument('-a', '--agents', type=str, action='append', 
        nargs='+', help='Specific agents to test offsite sync for.'
    )

    args = parser.parse_args()
    main(args)