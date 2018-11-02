#!/bin/bash

if [ $# -lt 1 ]; then
    echo -e "this util is used to show all acc testcase in a provider or specified test files\n"
    echo "usage: $0"
    echo "  test_files:"
    echo "    if it test all test cases in the code repository, input: *"
    echo "    or use wildcard * to sepcify a batch of files: resource_huaweicloud_elb*"
    echo "    or specify the test files explicitly in the format: \"file1 file2 ..\""
    echo "  [cloud name alias]"
    exit 1
fi

dest_cloud_alias=$2

. "$(dirname $(which $0))/common.sh"

get_config="$(dirname $(which $0))/$config_exec"

if [ -n "$dest_cloud_alias" ]; then
    dest_cloud=$($get_config name $dest_cloud_alias)
    test $? -ne 0 && echo "can not find cloud name: $dest_cloud_alias" && exit 1
else
    dest_cloud_alias=$($get_config guess_cloud_alias $(pwd))
    test $? -ne 0 && echo "Can not guess the cloud name, please input cloud name" && exit 1
    dest_cloud=$($get_config name $dest_cloud_alias)
fi

source_dir="$($get_config code_dir $dest_cloud_alias)/$dest_cloud"

test_files=$1
test -z "$test_files" && test_files="${source_dir}/*.go"
egrep "\(t \*testing.T\) {" $test_files | awk -F 'func' '{print $2}' | awk -F '(' '{print $1}' | sort

