#!/bin/bash

if [ $# -lt 4 ]; then
    echo -e "this util is used to migrate all files of a resource from one provider to another\n"
    echo -e "the files include resource file, test file, sdk, doc\n"
    echo -e "before run this util, it needs to change to the directory of source provider\n"
    echo "usage: $(basename $0)"
    echo "       dest_cloud_alias: value is like huawei, opente, telef, flexi"
    echo "       service_name: its value will be used as the index of the resource doc, for virtual machine its value can be 'Compute'"
    echo "       resource_file"
    echo "       resouece_doc_file"
    echo "       [data_resource_file data_resouece_doc_file or other files]"
    echo "            note: if there are multiple files, input them in the format of 'file1 file2 file3'"
    exit 1
fi

cur_dir=$(pwd)

get_config="$(dirname $(which $0))/../config/get_config.sh"

. $(dirname $(which $0))/common.sh

src_cloud_alias=$($get_config guess_cloud_alias $cur_dir)
test $? -ne 0 && echo "change to the provider directory first" && exit 1
src_cloud=$($get_config name $src_cloud_alias)
src_cloud_u=$($get_config name_of_upper $src_cloud_alias)
src_dir=$($get_config code_dir $src_cloud_alias)

dest_cloud_alias=$1
dest_cloud=$($get_config name $dest_cloud_alias)
test $? -ne 0 && echo "can not find cloud name: $dest_cloud_alias" && exit 1
dest_cloud_u=$($get_config name_of_upper $dest_cloud_alias)
dest_dir=$($get_config code_dir $dest_cloud_alias)

go_file=$(get_file_absolute_path $3)
go_test_file="${go_file%.go}_test.go"
doc_file=$(get_file_absolute_path $4)

p5=""
if [ -n "$5" ]; then
    files=($5)
    for f in ${files[@]}
    do
        p5="$p5 $(ls $f)"
    done
fi
files=($p5)
for f in ${files[@]}
do
    f=$(get_file_absolute_path $f)
    if [ "$(has_postfix $f 'html.markdown')" = "yes" ]; then
        doc_file="$doc_file $f"
    elif [ "$(has_postfix $f '_test.go')" = "yes" ]; then
        go_test_file="$go_test_file $f"
    elif [ "$(has_postfix $f '.go')" = "yes" ]; then
        go_file="$go_file $f"
    else
        echo "unknown file: $f" && exit 1
    fi
done

# -----------------------------------------------

echo -e "\nstep0: clear last update"

cd $dest_dir
git reset --hard

files=($(git status | sed -n '/to include in what will be committed/,/nothing added to commit but untracked files present/p' | sed '1d;$d'))
for d in ${files[@]}
do
    test -f $d || test -d $d && rm -fr $d
done
cd $cur_dir

# -----------------------------------------------

echo -e "\nstep1: sync sdk"

sdks=$(grep "huaweicloud/golangsdk/openstack" $go_file $go_test_file | awk -F '"' '{print $2}' | sort | uniq)
sdks=("github.com/huaweicloud/golangsdk/openstack github.com/huaweicloud/golangsdk $sdks")
cd $dest_dir
for d in ${sdks[@]}
do
    govendor fetch $d
    test $? -ne 0 && echo "update lib of $d failed"
done
cd $cur_dir

# -----------------------------------------------

echo -e "\nstep2: sync data/resource files and doc"

replace_cloud() {
    local p=$2
    sed -i "${p}s/$src_cloud_u/$dest_cloud_u/g" $1

    sed -i "${p}s/$src_cloud/$dest_cloud/g" $1

    sed -i "${p}s/$($get_config name_of_long $src_cloud_alias)/$($get_config name_of_long $dest_cloud_alias)/g" $1
}

files=($go_file $go_test_file $doc_file)
for f in ${files[@]}
do
    test -f $f || continue

    d_f=$dest_dir/$(get_file_relative_path $f $src_dir)
    d_f=${d_f//$src_cloud/$dest_cloud}

    mkdir -p $(dirname $d_f)

    cp $f $d_f

    if [ "$(has_postfix $d_f '.go')" == "no" ]; then
        replace_cloud $d_f
    else
        ps=""
        h=$(sed -n '/import (/, /)/=' $d_f | head -n 1)
        t=$(sed -n '/import (/, /)/=' $d_f | tail -n 1)

        test -n "$h" && ps="1,$h"
        test -n "$t" && ps="$ps $t,\$"

        if [ -z "$ps" ]; then
            replace_cloud $d_f
        else
            ps=($ps)
            for p in ${ps[@]}
            do
                replace_cloud $d_f "$p"
            done
        fi
    fi
done

# -----------------------------------------------

echo -e "\nstep3: add index of doc"

files=($doc_file)
cd $dest_dir
docs=""
for f in ${files[@]}
do
    f=$dest_dir/$(get_file_relative_path $f $src_dir)
    docs="$docs:$f"
done
terraform_add_index_of_doc.sh "$docs" "$2"
cd $cur_dir

# -----------------------------------------------

echo -e "\nstep4: register resource to provider"

dp="$dest_dir/$dest_cloud/provider.go"
sp="$src_dir/$src_cloud/provider.go"
files=($go_file)
flags=("ResourcesMap:resource_" "DataSourcesMap:data_source_")
for f in ${flags[@]}
do
    prefix=${f##*:}
    f=${f%:*}
    for f1 in ${files[@]}
    do
        f1=$(basename $f1)
        rn=${f1##${prefix}}
        rn=${rn%.go}
        if [ -n "$(sed -n '/'$f'/, /}/p' $dp | grep ${rn//$src_cloud/$dest_cloud})" ]; then
            continue
        fi

        rg=$(sed -n '/'$f'/, /}/p' $sp | grep $rn)
        if [ -n "$rg" ]; then
            rg=${rg//$src_cloud/$dest_cloud}
            if [[ ! $rg =~ ',' ]]; then
                rg="$rg,"
            fi
            ln=$(sed -n '/'$f'/, /}/=' $dp | tail -n 1)
            sed -i $ln'i\'"$rg" $dp
        fi
    done
done
gofmt -w $dp

# -----------------------------------------------

echo -e "\nstep5: compare the following files manually"

files=($go_file)
for f in ${files[@]}
do
    python $(dirname $(which $0))/python_tools/retrive_funcs_of_terraform_resource_go_file.py $f
done
