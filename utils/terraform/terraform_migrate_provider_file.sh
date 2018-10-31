#!/bin/bash

if [ $# -ne 2 ]; then
	echo -e "this util is used to migrate file for one provider to another\n"
	echo "usage: $0 src_file dest_cloud_alias"
	exit 1
fi

cur_dir=$(pwd)
cd $(dirname $1)
src=$(pwd)/$(basename $1)
cd $cur_dir

get_config="$(dirname $(which $0))/../config/get_config.sh"

src_cloud_alias=$($get_config guess_cloud_alias $(dirname $src))
test $? -ne 0 && echo "$1 is not a file belonging to a cloud" && exit 1
src_cloud=$($get_config name $src_cloud_alias)
src_cloud_u=$($get_config name_of_upper $src_cloud_alias)

dest_cloud_alias=$2
dest_cloud=$($get_config name $dest_cloud_alias)
test $? -ne 0 && echo "can not find cloud name: $dest_cloud_alias" && exit 1
dest_cloud_u=$($get_config name_of_upper $dest_cloud_alias)

src_base_dir="$($get_config code_dir $src_cloud_alias)/"
src_relative_dir=${src#$src_base_dir}
dest=$($get_config code_dir $dest_cloud_alias)/${src_relative_dir//$src_cloud/$dest_cloud}

mkdir -p $(dirname $dest)

cp $src $dest

sed -i "s/$src_cloud_u/$dest_cloud_u/g" $dest

sed -i 's/'"$src_cloud"'/'"$dest_cloud"'/g' $dest

sed -i "s/$($get_config name_of_long $src_cloud_alias)/$($get_config name_of_long $dest_cloud_alias)/g" $dest

#vimdiff $dest $src
