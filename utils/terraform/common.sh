#!/bin/bash

pre_treat_old_file() {
    local f=$2

    if [ $1 = "rm" ]; then
        rm ${f}*
        echo $f
    else
        test ! -f $f && echo $f && return 0
        local fl=$(ls -l ${f}* | awk '{print $NF}' | sort | tail -n 1)
        echo ${fl}1
    fi
}

capitalize() {
    local w=$1
    local c=$(echo ${w:0:1})
    echo $(echo $c | tr [a-z] [A-Z])$(echo ${w:1})
}

has_prefix() {
    local r=$(echo $1 | egrep "^$2")
    test -n "$r" && echo "yes" || echo "no"
}

has_postfix() {
    local r=$(echo $1 | egrep "$2$")
    test -n "$r" && echo "yes" || echo "no"
}

get_file_absolute_path() {
    local cur_dir=$(pwd)
    cd $(dirname $1)
    echo "$(pwd)/$(basename $1)"
    cd $cur_dir
}

get_file_relative_path() {
    fp=$(get_file_absolute_path $1)
    echo ${fp#$2}
}

fmt_go_file() {
    local f=$1
    goimports -w $f
    gofmt -w $f
}
