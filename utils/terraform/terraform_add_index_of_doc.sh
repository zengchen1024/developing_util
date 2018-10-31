#!/bin/bash

if [ $# -lt 1 ]; then
    echo -e "this util is used to add index for docs at website/docs/r or website/doces/d\n"
    echo "usage: $0"
    echo "      doc_files(splited by :)"
    echo "      [service_name], The value like Block Storage, Compute etc. If add a new service's doc index, it must be specified"
    echo "      [index_file_name]"
    echo "      [dest_cloud_name]"
    exit 1
fi

service_name=$2
doc_files=$1
doc_files=${doc_files//:/ }

common_funcs="$(dirname $(which $0))/common.sh"
. $common_funcs


get_config="$(dirname $(which $0))/../config/get_config.sh"

cur_dir=$(pwd)

dest_cloud_alias=$($get_config guess_cloud_alias $cur_dir)
if [ $? -ne 0 ]; then
    test $# -ne 4 && echo "Can not guess the cloud name, please input cloud alias" && exit 1
    dest_cloud_alias=$4
fi
dest_cloud=$($get_config name $dest_cloud_alias)
test $? -ne 0 && echo "can not find cloud name: $dest_cloud" && exit 1
dest_dir=$($get_config code_dir $dest_cloud_alias)

index_file=$(ls ${dest_dir}/website/*.erb)
if [ $(ls -l ${dest_dir}/website/*.erb | wc -l) -ne 1 ]; then
    test $# -lt 3 && echo "Can not guess the index file, please specify it" && exit 1
    index_file="${dest_dir}/website/$3"
    test !-f $index_file && "$3 is not a normal index file" && exit 1
fi

get_sidebar_prefix() {
    local f=$1
    local d_r=$(basename $(dirname $full_path_f))
    if [ "$d_r" = "d" ]; then
        echo "docs-${dest_cloud}-datasource" && return 0
    fi

    local s=$(grep "sidebar_current" $f | awk -F '"' '{print $2}' | awk -F '-' '{print $1,"-",$2,"-",$3,"-",$4}')
    echo ${s// /}
}

is_a_new_service() {
    local sdp=$(get_sidebar_prefix $1)
    local l=$(egrep "^ {8}<li<%= sidebar_current\(\"$sdp\"\) %>>$" -n $index_file | awk -F ':' '{print $1}')
    test -z "$l" && echo "yes" || echo "no"
}

find_a_new_service_start_pos() {
    local l=$(egrep "<li<%= sidebar_current\(\"docs-${dest_cloud}-resource-[a-z]+\"\) %>>" -n $index_file | tail -n 1 | awk -F ':' '{print $1}')
    test -z "$l" && echo "can not find service start position" && return 1

    local le=$(sed -n "$l,$""{=;p}" $index_file | egrep -A1 "^ {8}</li>$" | tail -n 1)
    test -z "$le" && echo "can not find service end position" && return 1

    echo $le
    return 0
}

find_resource_start_pos() {
    local sdp=$(get_sidebar_prefix $1)

    local l=$(egrep "^ {8}<li<%= sidebar_current\(\"$sdp\"\) %>>$" -n $index_file | awk -F ':' '{print $1}')
    test -z "$l" && echo "can not find service start position" && return 1

    local le=$(sed -n "$l,$""{=;p}" $index_file | egrep -A1 "^ {8}</li>$" | head -n 2 | tail -n 1)
    test -z "$le" && echo "can not find service end position" && return 1

    local rend=$(sed -n "$l,$le""{=;p}" $index_file | egrep -A1 "^ {12}</li>$" | tail -n 1)
    test -z "$rend" && echo "can not find resource end position" && return 1

    echo $rend
    return 0
}

generate_a_resource_index() {
    local markdown_f=$1

    local sd=$(grep sidebar_current $markdown_f | awk -F '"' '{print $2}')
    local d_r=$(basename $(dirname $markdown_f))
    local fname=$(basename $markdown_f)
    fname=$(echo ${fname%%.markdown})
    local rd=$(grep page_title $markdown_f | awk '{print $NF}' | awk -F '"' '{print $1}')

    local r=""
    r+="            <li<%= sidebar_current(\"${sd}\") %>>\n"
    r+="              <a href=\"/docs/providers/${dest_cloud}/${d_r}/${fname}\">${rd}</a>\n"
    r+="            </li>\n"
    echo -e "$r"
}

write_to_index_file() {
    local sp=$1
    local tmp_file=$2
    local service_start_line_tag="service_start_line_tag"

    sed -i "${sp} i ${service_start_line_tag}" $index_file

    IFS=''
    while read l
    do
        #echo "write line: $l"
        #test -n "$l" && echo "write line: $l" && sed -i "/$service_start_line_tag/i\\""$l" $index_file
        sed -i "/$service_start_line_tag/i\\""$l" $index_file
    done < $tmp_file

    sed -i "/${service_start_line_tag}/d" $index_file
}

add_a_new_service() {
    local ssp=$(find_a_new_service_start_pos)
    test -z "$ssp" && echo "add index for a new service failed: $ssp" && return 0

    local tmp_file="${dest_dir}/tmp_file"
    local sdp=$(get_sidebar_prefix $1)

    > $tmp_file

cat >> $tmp_file << EOF
        <li<%= sidebar_current("$sdp") %>>
          <a href="#">${service_name} Resources</a>
          <ul class="nav nav-visible">
EOF

    generate_a_resource_index $1 >> $tmp_file

cat >> $tmp_file << EOF
          </ul>
        </li>

EOF

    write_to_index_file $ssp $tmp_file

    sed -i "$ssp i\\\n" $index_file
    sed -i "${ssp}d" $index_file

    rm $tmp_file
}

append_an_resource_index() {
    local f=$1
    local rsp=""
    rsp=$(find_resource_start_pos $f)
    test $? -ne 0 && echo "append a resource index failed: $rsp" && return 1

    local tmp_file="${dest_dir}/tmp_file"
    generate_a_resource_index $f > $tmp_file

    local e=$(grep "$(head -n 1 $tmp_file)" $index_file)
    test -n "$e" && rm $tmp_file && return 0

    write_to_index_file $rsp $tmp_file

    rm $tmp_file
}

for f in ${doc_files[@]}
do
    full_path_f=$(get_file_absolute_path $f)
    d_r=$(basename $(dirname $full_path_f))
    if [ "$d_r" == "r" ]; then
        echo "--------- add a resource index for: $f ---------"

        if [ "$(is_a_new_service $full_path_f)" = "yes" ]; then
            echo "add index for a new service"
	    test $# -lt 2 && echo "add index for new service, it must specify the service name" && continue
	    add_a_new_service $full_path_f
        else
            echo "add index for an exist service"
            append_an_resource_index $full_path_f
        fi
    else
        echo "add a data source index of $f"
        append_an_resource_index $full_path_f
    fi
done
