## on Linux platform

### Install ansible
1. curl https://raw.githubusercontent.com/zengchen1024/developing_util/master/utils/ansible/ansible_build_env.sh -o ansible_build_env.sh
2. chmod +x ansible_build_env.sh
3. mkdir ansible
4. ./ansible_build_env.sh ./ansible otc
5. cd ansbile
6. . hacking/env-setup

### Usage

#### Create a virtual machine on Opentelekom cloud
1. cd ./ansible/lib/ansible/modules/cloud/opentelekom
2. touch vm.yaml
3. append the following configurations to vm.yaml and replace all the placeholders
```yaml
- name: create a vm
  connection: local
  hosts: localhost
  tasks:
    - name: create a new vm
      otc_compute_instance:
        identity_endpoint: "https://iam.eu-de.otc.t-systems.com/v3"
        user_name: "{{ user_name }}"
        password: "{{ password }}"
        domain_name: "{{ domain_name }}"
        project_name: "{{ project_name }}"
        region: "{{ region }}"
        log_file: "/tmp/vm.log"

        name: "{{ vm_name }}"
        image: "{{ image_id }}"
        flavor: "{{ flavor_id }}"
        networks:
          - uuid: "{{ network_id }}"
      register: vm 
    - name: dump the output
      debug:
        msg: '{{ vm }}'
```

3. ansible-playbook vm.yaml
4. after ansible-playbook finished, a virtual machine will be created,
   and it will show the details about this vm.

#### Other examples
1. you can find all the official modules at [link](https://docs.ansible.com/ansible/latest/modules/modules_by_category.html)
2. you can see the document of a module to use it. for example, [create a vm on openstack platform](https://docs.ansible.com/ansible/latest/modules/os_server_module.html#os-server-module)
