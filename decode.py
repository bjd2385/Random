#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Decode our JSON compressed format.
"""

from typing import Dict, List, Optional, Any

import os
import re


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


class InvalidArrayFormat(SyntaxError):
    """
    Raised when the input "compressed" JSON format is invalid.
    """


def decodeJSON(key: str) -> Dict:
    """
    Decode our JSON with regex into something a little nicer. In Python 3.5, if
    I'm not mistaken, dictionaries don't necessarily keep their order, so I've
    decided to use lists instead to unpack all of the keyData into. Then a second
    pass converts this list of lists ... into a dictionary of dictionaries ...
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
            # Bite a piece at a time. Can't wait till assignment expressions!
            result = re.search(lexer, keyData)

            if not result:
                # Show what's left that it couldn't 'parse' so we can debug it
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
                _, _, value = re.split(colonStringSplit, substring)
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


def find(key: Any, nestedDicts: Dict) -> Any:
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


def findAll(key: Any, nestedDicts: Dict, byValue: bool =False) -> List:
    """
    Return all occurrences of values associated with `key`, if any. Again, O(n).
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


if __name__ == '__main__':
    print(decodeJSON('data.txt'))
    print(find('device', decodeJSON('data.txt')))
    print(findAll('device', decodeJSON('data.txt')))
    print(findAll(1, decodeJSON('data.txt'), byValue=True))