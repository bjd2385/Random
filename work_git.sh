#! /bin/bash
#
# work_git.sh
# Copyright (©) 2018 brandon <brandon@ideapad>
#
# Distributed under terms of the MIT license.

git --git-dir=/home/brandon/datto/Random/.git/ --work-tree=/home/brandon/datto/Random/ add $@
git --git-dir=/home/brandon/datto/Random/.git/ --work-tree=/home/brandon/datto/Random/ commit -m $@
git --git-dir=/home/brandon/datto/Random/.git/ --work-tree=/home/brandon/datto/Random/ push
