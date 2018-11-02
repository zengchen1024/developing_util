#!/bin/bash

get_config="$(dirname $(which $0))/$config_exec"

cur_dir=$(pwd)

env=$($get_config where_am_i $cur_dir)
test $? -ne 0 && echo "Can not guess where am i. Go to your code dir and try again" && exit 1

cloud_sdk=$(echo $env | awk -F ':' '{print $1}')
path=$(echo $env | awk -F ':' '{print $3}')
cd $path

if [ "$cloud_sdk" = "cloud" ]; then
	echo -e "run make test"
	make test || exit 1

	echo -e "\n\nrun make vet"
	make vet || exit 1

	echo -e "\n\nrun make vendor-status"
	make vendor-status || exit 1
	
	echo -e "\n\nrun make build"
	make build
else
	echo -e "run ./script/format"
	./script/format

	echo -e "\n\nrun ./script/coverage"
	./script/coverage
	rm testing_*
	rm cover.out
fi
cd $cur_dir
