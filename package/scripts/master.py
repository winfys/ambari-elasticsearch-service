#!/usr/bin/env python

"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sys
import os
import glob
import pwd
import grp
import signal
import time
from resource_management import *
from resource_management.core import sudo

class Master(Script):

    # Install Elasticsearch
    def install(self, env):
        # Import properties defined in -config.xml file from the params class
        import params

        # This allows us to access the params.elastic_pid_file property as
        # format('{elastic_pid_file}')
        env.set_params(params)

        # Install dependent packages
        self.install_packages(env)

        # Create user and group for Elasticsearch if they don't exist
        try: grp.getgrnam(params.elastic_group)
        except KeyError: Group(group_name=params.elastic_group)

        try: pwd.getpwnam(params.elastic_user)
        except KeyError: User(username=params.elastic_user,
                              gid=params.elastic_group,
                              groups=[params.elastic_group],
                              ignore_failures=True
                             )

        # Create Elasticsearch download tmp dir
        Directory([params.elastic_download_dir],
                  mode=0755,
                  cd_access='a',
                  owner=params.elastic_user,
                  group=params.elastic_group,
                  create_parents=True
                 )
        #Directory(params.elastic_download_dir, create_parents=True)

        # Create empty Elasticsearch install log
        File(params.elastic_install_log,
             mode=0644,
             owner=params.elastic_user,
             group=params.elastic_group,
             content=''
            )

        # Download Elasticsearch
        cmd = format("cd {elastic_download_dir}; wget {elastic_download} -O elasticsearch.rpm -a {elastic_install_log}")
        #cmd = "cd /var/www/html/;mv elasticsearch-5.4.1.rpm elasticsearch.rpm"
        Execute(cmd)

        # Install Elasticsearch
        #cmd = "cd /var/www/html/; rpm --install elasticsearch.rpm"
        cmd = format("cd {elastic_download_dir}; sudo rpm --install elasticsearch.rpm")
        Execute(cmd)

        cmd = "chkconfig --add elasticsearch"
        Execute(cmd)
        # Remove Elasticsearch installation file
        cmd = format("rm -rf {elastic_download_dir}")
        Execute(cmd, user=params.elastic_user) 
        
        #chown es config directory
        cmd = format("sudo chown -R elasticsearch {elastic_conf_dir}")
        Execute(cmd)
        #create data store directory
        Execute(format('echo   {path_data}'))
        Directory(params.path_data,
                  owner=params.elastic_user,
                  group=params.elastic_group,
                  create_parents=True
                 )

        Execute('echo "Install complete"')


    def configure(self, env):
        # Import properties defined in -config.xml file from the params class
        import params

        # This allows us to access the params.elastic_pid_file property as
        # format('{elastic_pid_file}')
        env.set_params(params)

        configurations = params.config['configurations']['elastic-config']

        File(format("{elastic_conf_dir}/elasticsearch.yml"),
             content=Template("elasticsearch.yml.j2",
                              configurations=configurations),
            owner=params.elastic_user,group=params.elastic_group
            )

        # Install HEAD and HQ puglins - these plugins are not currently supported by ES 5.x
        #cmd = format("{elastic_base_dir}/bin/elasticsearch-plugin install mobz/elasticserach-head")
        #Execute(cmd)

        #write /etc/sysconfig/elasticsearch
        sysconfig_content = InlineTemplate(params.elastic_sysconfig_content)
        File(params.elastic_sysconfig_file,content=sysconfig_content,owner=params.elastic_user,group=params.elastic_group)

        #write /etc/elasticsearch/jvm.options
        jvm_content = InlineTemplate(params.elastic_jvm_content)
        File(format("{elastic_conf_dir}/jvm.options"), content=jvm_content,owner=params.elastic_user,group=params.elastic_group)

        # write /etc/elasticsearch/log4j2.properties
        log4j_content = InlineTemplate(params.elastic_log4j_content)
        File(format("{elastic_conf_dir}/log4j2.properties"), content=log4j_content,owner=params.elastic_user,group=params.elastic_group)

        Execute('echo "Configuration complete"')

    def stop(self, env):
        # Import properties defined in -config.xml file from the params class
        import params

        # Import properties defined in -env.xml file from the status_params class
        import status_params

        # This allows us to access the params.elastic_pid_file property as
        #  format('{elastic_pid_file}')
        env.set_params(params)

        # Stop Elasticsearch

        Execute("sudo service elasticsearch stop")
        if os.path.isfile(status_params.elastic_pid_file):
           # kill_process(params.elastic_pid_file, params.elastic_user, params.elastic_log_dir)
           sudo.unlink(status_params.elastic_pid_file)
        #cmd = format("kill `cat {elastic_pid_file}`")
        #Execute(cmd, user=params.elastic_user, only_if=format("test -f {elastic_pid_file}"))


    def start(self, env):
        # Import properties defined in -config.xml file from the params class
        import params

        # This allows us to access the params.elastic_pid_file property as
        #  format('{elastic_pid_file}')
        env.set_params(params)

        # Configure Elasticsearch
        self.configure(env)

        # Start Elasticsearch
        cmd = 'sudo service elasticsearch start'
        Execute(cmd)


    def status(self, env):
        # Import properties defined in -env.xml file from the status_params class
        import status_params

        # This allows us to access the params.elastic_pid_file property as
        #  format('{elastic_pid_file}')
        env.set_params(status_params)

        #try:
        #    pid_file = glob.glob(status_params.elastic_pid_file)[0]
        #except IndexError:
        #    pid_file = ''

        # Use built-in method to check status using pidfile
        check_process_status(status_params.elastic_pid_file)

if __name__ == "__main__":
    Master().execute()
