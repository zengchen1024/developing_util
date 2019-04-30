#!/bin/bash - 
#===============================================================================
#
#          FILE: all_files_in_a_commit.sh
# 
#         USAGE: ./all_files_in_a_commit.sh 
# 
#   DESCRIPTION: 
# 
#       OPTIONS: ---
#  REQUIREMENTS: ---
#          BUGS: ---
#         NOTES: ---
#        AUTHOR: YOUR NAME (), 
#  ORGANIZATION: 
#       CREATED: 04/28/2019 03:28:54 PM
#      REVISION:  ---
#===============================================================================

if [ $# -ne 1 ]; then
	echo "usage: $(basename $0) commit_id"
	exit 1
fi

if [ ! -d $(pwd)/.git ]; then
	echo "current directory is not a git repository"
	exit 1
fi

commit_id=$1
fs=$(git show --pretty="" --name-only $commit_id)

test -d $(pwd)/old || mkdir $(pwd)/old

for f in ${fs[@]}
do
	git show $commit_id:$f > old/$(basename $f)
done
