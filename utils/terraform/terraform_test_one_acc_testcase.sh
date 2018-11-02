#!/bin/bash

if [ $# -lt 1 ]; then
	echo -e "this util is used to test a acc testcase in a provider\n"
	echo -e "usage: $0 testcase [dest_cloud_alias]\n"
	exit 1
fi

get_config="$(dirname $(which $0))/$config_exec"

cur_dir=$(pwd)

dest_cloud_alias=$2
if [ -n "$dest_cloud_alias" ]; then
    dest_cloud=$($get_config name $dest_cloud_alias)
    test $? -ne 0 && echo "can not find cloud name: $dest_cloud_alias" && exit 1
else
    dest_cloud_alias=$($get_config guess_cloud_alias $(pwd))
    test $? -ne 0 && echo "Can not guess the cloud name, please input cloud name" && exit 1
    dest_cloud=$($get_config name $dest_cloud_alias)
fi

dest_dir=$($get_config code_dir $dest_cloud_alias)

cd $dest_dir
echo "run $dest_dir: $1"
rm $TF_LOG_PATH
TF_ACC=1 go test ./$dest_cloud/ -v -run=$1 -timeout 30m
cd $cur_dir
