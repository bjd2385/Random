#! /bin/bash
#
# work_git.sh
# Copyright (©) 2018 brandon <brandon@ideapad>
#
# Distributed under terms of the MIT license.

DIR="/mnt/o/Random"

git --git-dir="$DIR/.git/" --work-tree="$DIR/" add $@
git --git-dir="$DIR/.git/" --work-tree="$DIR/" commit -m $@
git --git-dir="$DIR/.git/" --work-tree="$DIR/" push
