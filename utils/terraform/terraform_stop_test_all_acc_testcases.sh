#!/bin/bash

pid=$(ps -ef | grep terraform_test_all_acc_testcases.sh | grep -v "grep" | awk '{print $2}')
test -z "$pid" && echo "no process exist" && exit 1
kill $pid
