#!/bin/bash

if [ $# -lt 2 ]; then
	echo "usage: $0 file dest_cloud_name [dest file]"
	exit 1
fi

cur_dir=$(pwd)
cd $(dirname $1)
src=$(pwd)/$(basename $1)
cd $cur_dir

get_config="$(dirname $(which $0))/$config_exec"

src_cloud_alias=$($get_config guess_cloud_alias $(dirname $src))
test $? -ne 0 && echo "$1 is not a file belonging to a cloud" && exit 1
src_cloud=$($get_config name $src_cloud_alias)

dest_cloud_alias=$2
dest_cloud=$($get_config name $dest_cloud_alias)
test $? -ne 0 && echo "can not find cloud name: $dest_cloud_alias" && exit 1

src_base_dir="$($get_config code_dir $src_cloud_alias)/"
src_relative_dir=${src#$src_base_dir}
dest=$($get_config code_dir $dest_cloud_alias)/${src_relative_dir//$src_cloud/$dest_cloud}
if [ $# -eq 3 ]; then
	dest=$($get_config code_dir $dest_cloud_alias)/$3
fi

test ! -f $dest && echo "$dest is not exist" && exit 1

echo $src
echo $dest
vimdiff $src $dest
