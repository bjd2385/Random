#! /bin/bash
#
# work_git.sh
# Copyright (©) 2018 brandon <brandon@ideapad>
#
# Distributed under terms of the MIT license.

git --git-dir=/home/brandon/datto/error_codes/.git/ --work-tree=/home/brandon/datto/error_codes/ add $@
git --git-dir=/home/brandon/datto/error_codes/.git/ --work-tree=/home/brandon/datto/error_codes/ commit -m $@
git --git-dir=/home/brandon/datto/error_codes/.git/ --work-tree=/home/brandon/datto/error_codes/ push
