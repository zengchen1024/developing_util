#!/bin/bash

if [ $# -lt 3 ]; then
    echo -e "this util is used to generate sdk of a resource\n"
    echo "usage: $0"
    echo "    sdk_dir"
    echo "    resource name"
    echo "    api_doc_dir"
    echo "    [msg_prefix/success_codes":msg_prefix/success_codes":msg_prefix/success_codes":msg_prefix/success_codes"]"
    echo "    update_req_method[Post | Put], default is Put"
    echo "    how to do with the old go file[rm | new], default is new"
    exit 1
fi

tool_dir=$(dirname $(which $0))
. $tool_dir/common.sh

get_config="$(dirname $(which $0))/../config/get_config.sh"

code_dir=$1
mkdir -p $code_dir
test $? -ne 0 && echo "make dir failed for: $code_dir" && exit 1

package_name=$2
resource_name=$(capitalize $2)
api_doc_dir=$3
p4=$4

if [ $# -le 4 ]; then
    update_req_method="Put"
else
    update_req_method=$5
    if [ "$5" != "Put" ] && [ "$5" != "Post" ]; then
        echo "unknown update_req_method: $5"
        exit 1
    fi
fi

if [ $# -le 5 ]; then
    treat_old_file="new"
else
    treat_old_file=$6
    if [ "$6" != "new" ] && [ "$6" != "rm" ]; then
        echo "unknown treat_old_file: $6"
        exit 1
    fi
fi

#echo  $update_req_method $treat_old_file

req_go_file=$code_dir/requests.go
req_go_file=$(pre_treat_old_file $treat_old_file $req_go_file)

resp_go_file=$code_dir/results.go
resp_go_file=$(pre_treat_old_file $treat_old_file $resp_go_file)

#echo $req_go_file
#echo $resp_go_file

#echo $req_go_file $api_doc_dir/create.docx $resource_name "$success_codes"
#exit 0

struct_generator=$tool_dir/new_python_tools/generate_go_struct.py

msg_prefix=""
success_codes=""
get_msg_and_code() {
    local t=$1
    local ps="create:1update:2get:3delete:4"
    local i=${ps#*$t}
    i=${i:1:1}
    local mc=$(echo "$p4" | awk -F ':' -v n=$i '{print $n}')
    #echo $p4 $i $mc
    msg_prefix=${mc%/*}
    success_codes=${mc#*/}
}

#get_msg_and_code delete
#echo $success_codes $msg_prefix
#exit 0
# ------------------------------------------------------------ #
#                  generatte requests.go                       #
# ------------------------------------------------------------ #


# write the head
echo "package $package_name" > $req_go_file

# -----------------------------
# generate Create part of requests.go

err=$(python $struct_generator "req" $req_go_file $api_doc_dir/create.docx)
test $? -ne 0 && echo "generate requests.go of Create structs failed: $err" && exit 1

get_msg_and_code create

if [ -n "$success_codes" ]; then
    req_opt="reqOpt := &golangsdk.RequestOpts{OkCodes: []int{${success_codes}}}\n\t_, r.Err = c.Post(createURL(c), b, &r.Body, reqOpt)"
else
    req_opt="_, r.Err = c.Post(createURL(c), b, &r.Body, nil)"
fi

echo -e "

type CreateOptsBuilder interface {
\tTo${resource_name}CreateMap() (map[string]interface{}, error)
}

func (opts CreateOpts) To${resource_name}CreateMap() (map[string]interface{}, error) {
\treturn golangsdk.BuildRequestBody(opts, \"$msg_prefix\")
}

func Create(c *golangsdk.ServiceClient, opts CreateOptsBuilder) (r CreateResult) {
\tb, err := opts.To${resource_name}CreateMap()
\tif err != nil {
\t\tr.Err = err
\t\treturn
\t}
\tlog.Printf(\"[DEBUG] create url:%q, body=%#v\", createURL(c), b)
\t${req_opt}
\treturn
}
" >> $req_go_file

# -----------------------------
# generate Update part of requests.go

if [ -f $api_doc_dir/update.docx ]; then
    err=$(python $struct_generator "req" $req_go_file $api_doc_dir/update.docx)
    test $? -ne 0 && echo "generate requests.go of Update structs failed: $err" && exit 1

    get_msg_and_code update

    if [ -n "$success_codes" ]; then
        req_opt="reqOpt := &golangsdk.RequestOpts{OkCodes: []int{${success_codes}}}\n\t_, r.Err = c.${update_req_method}(updateURL(c, id), b, &r.Body, reqOpt)"
    else
        req_opt="_, r.Err = c.${update_req_method}(updateURL(c, id), b, &r.Body, nil)"
    fi

    echo -e "

type UpdateOptsBuilder interface {
\tTo${resource_name}UpdateMap() (map[string]interface{}, error)
}

func (opts UpdateOpts) To${resource_name}UpdateMap() (map[string]interface{}, error) {
\treturn golangsdk.BuildRequestBody(opts, \"$msg_prefix\")
}

func Update(c *golangsdk.ServiceClient, id string, opts UpdateOptsBuilder) (r UpdateResult) {
\tb, err := opts.To${resource_name}UpdateMap()
\tif err != nil {
\t\tr.Err = err
\t\treturn
\t}
\tlog.Printf(\"[DEBUG] update url:%%q, body=%%#v\", updateURL(c, id), b)
\t$req_opt
\treturn
}" >> $req_go_file
fi

# -----------------------------
# generate Get part of requests.go

cat >> $req_go_file << EOF

func Get(c *golangsdk.ServiceClient, id string) (r GetResult) {
    _, r.Err = c.Get(resourceURL(c, id), &r.Body, nil)
    return
}
EOF

# -----------------------------
# generate Delete part of requests.go

get_msg_and_code delete

if [ -n "$success_codes" ]; then
    req_opt="reqOpt := &golangsdk.RequestOpts{OkCodes: []int{${success_codes}}}\n\t_, r.Err = c.Delete(resourceURL(c, id), reqOpt)"
else
    req_opt="_, r.Err = c.Delete(resourceURL(c, id), nil)"
fi

echo -e "

func Delete(c *golangsdk.ServiceClient, id string) (r DeleteResult) {
\t$req_opt
\treturn
}
" >> $req_go_file

fmt_go_file $req_go_file

# ------------------------------------------------------------ #
#                  generatte results.go                        #
# ------------------------------------------------------------ #


default_result() {
    local sn=$1
    local op=${sn%_*}

    get_msg_and_code $op

    op=$(capitalize $op)
    if [ "$1" = "get_rsp" ]; then
        sn=$resource_name
    else
        sn=$(capitalize $sn)
    fi

    echo -e "

type ${op}Result struct {
\tgolangsdk.Result
}" >> $resp_go_file

    if [ -z "$msg_prefix" ]; then
        echo -e "

func (r ${op}Result) Extract() (*${sn}, error) {
    o := &${sn}{}
    return o, r.ExtractInto(o)
}" >> $resp_go_file
    else
        echo -e "

func (r ${op}Result) Extract() (*${sn}, error) {
    o := &${sn}{}
    return o, r.ExtractIntoStructPtr(o, \"${msg_prefix}\")
}" >> $resp_go_file
    fi

    if [ "$1" = "get_rsp" ]; then
        sed -i 's/GetRsp/'$sn'/g' $resp_go_file
    fi
}

# write the head
echo "package $package_name" > $resp_go_file

# generate CRUD method
fs=("get.docx:get_rsp" "create_rsp.docx:create_rsp" "update_rsp.docx:update_rsp")
for item in ${fs[@]}
do
    f=$api_doc_dir/${item%:*}
    if [ -f $f ]; then
        err=$(python $struct_generator "resp" $resp_go_file $f)
        test $? -ne 0 && echo "generate results.go of ${item#*:} structs failed: $err" && exit 1

        default_result ${item#*:}
    fi
done

# Delete
cat >> $resp_go_file << EOF
type DeleteResult struct {
    golangsdk.ErrResult
}
EOF

fmt_go_file $resp_go_file
