#!/bin/bash

if [ $# -lt 5 ]; then
	echo "usage: $0"
	echo "      dest_cloud_name"
	echo "      api_doc_dir"
	echo "      resource_name(the name's first character should be capital)"
	echo "      resource_go_file"
	echo "      doc_file_name"
	exit 1
fi

tool_dir=$(dirname $(which $0))
. $tool_dir/common.sh

get_config="$(dirname $(which $0))/../config/get_config.sh"

dest_cloud_alias=$1
dest_cloud=$($get_config name $dest_cloud_alias)
test $? -ne 0 && echo "can not find cloud name: $dest_cloud_alias" && exit 1
dest_cloud_u=$($get_config name_of_upper $dest_cloud_alias)
code_home_dir=$($get_config code_dir $dest_cloud_alias)

resouce_go_file_name=$(basename $4 | awk -F '.' '{print $1}')
resource=$(echo ${resouce_go_file_name#resource_})
resource1=$(echo ${resource#${dest_cloud}_})
resource1=$(echo ${resource1//_/-})
resource2=$(echo ${resource//_/\\_})

out_file=${code_home_dir}/website/docs/r/$5

cat > $out_file << EOF
layout: "$dest_cloud"
page_title: "$dest_cloud_u: $resource"
sidebar_current: "docs-${dest_cloud}-resource-$resource1"
description: |-
  Manages resource within
---

# $resource2

Manages resource within

## Example Usage

EOF

echo -e '```hcl\n```' >> $out_file

cat >> $out_file << EOF

## Argument Reference

The following arguments are supported:
EOF

python ${tool_dir}/new_python_tools/generate_parameter_doc.py $2 $out_file
test $? -ne 0 && echo "generate $out_file failed: $err" && exit 1
