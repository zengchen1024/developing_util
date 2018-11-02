#!/bin/bash

if [ $# -ne 1 ]; then
    echo "usage: $0 dest_cloud_name"
    exit 1
fi

. "$(dirname $(which $0))/common.sh"

get_config="$(dirname $(which $0))/$config_exec"

dest_cloud_alias=$1
name=$($get_config name $dest_cloud_alias)
test $? -ne 0 && echo "can not find cloud name: $dest_cloud_alias" && exit 1

acctest_env_dir=""
if [ "$name" = "huaweicloud" ]; then
    acctest_env_dir=huawei

elif [ "$name" = "telefonicaopencloud" ]; then
    acctest_env_dir=telef

elif [ "$name" = "opentelekomcloud" ]; then
    acctest_env_dir=otc

elif [ "$name" = "flexibleengine" ]; then
    acctest_env_dir=orange

else
    echo "not supported cloud: $name"
    exit 1
fi

test -z "$TERRAFORM_BIN" && echo "config env of 'TERRAFORM_BIN' first" && exit 0

echo ""
cat $TERRAFORM_BIN/$acctest_env_dir/acc_test_env/acc_test_env
echo ""
