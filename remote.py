from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import shutil

import ansible.constants as C
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.module_utils.common.collections import ImmutableDict
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars.manager import VariableManager
from ansible import context
from ansible.executor.playbook_executor import PlaybookExecutor

# Create a callback plugin so we can capture the output
class ResultsCollectorJSONCallback(CallbackBase):

    def __init__(self, *args, **kwargs):
        super(ResultsCollectorJSONCallback, self).__init__(*args, **kwargs)
        # self.host_ok = {}
        # self.host_unreachable = {}
        # self.host_failed = {}
        self.host_ok = []
        self.host_unreachable = []
        self.host_failed = []
    def v2_runner_on_unreachable(self, result):
        host = result._host
        #self.host_unreachable[host.get_name()] = result
        self.host_unreachable.append(json.dumps({host.name: result._result}, indent=4))
    def v2_runner_on_ok(self, result, *args, **kwargs):
        """Print a json representation of the result.

        Also, store the result in an instance attribute for retrieval later
        """
        host = result._host
        # self.host_ok[host.get_name()] = result
        # print(json.dumps({host.name: result._result}, indent=4))
        self.host_ok.append(json.dumps({host.name: result._result}, indent=4))

    def v2_runner_on_failed(self, result, *args, **kwargs):
        host = result._host
        # self.host_failed[host.get_name()] = result
        self.host_failed.append(json.dumps({host.name: result._result}, indent=4))
class AnsExecuter():
    def __init__(self,inventory):
        self._loader = DataLoader()
        self._passwords = None
        context.CLIARGS = ImmutableDict(connection='smart', module_path=None, forks=1, become=None,  verbosity=5,
                                        sudo=None,sudo_user=None,ask_sudo_pass=None,
                                        become_method=None, become_user=None, check=False, diff=False,syntax=None,start_at_task=None)
        self._inventory = InventoryManager(loader=self._loader, sources=inventory)

        self._variable_manager = VariableManager(loader=self._loader, inventory=self._inventory)
        self.result_callback=ResultsCollectorJSONCallback()

    def run(self,hosts='localhost',module='ping',args='',timeout=0):
        tqm = TaskQueueManager(
            inventory=self._inventory,
            variable_manager=self._variable_manager,
            loader=self._loader,
            passwords=self._passwords,
            stdout_callback=self.result_callback,
        )
        play_source = dict(
            name='Ad-hoc',
            hosts=hosts,
            gather_facts='no',
            tasks=[
                dict(action=dict(module=module, args=args), register='shell_out'),
                #{'action':{'module':module,'args':args},'async':timeout,'poll':0},
                # dict(action=dict(module='debug', args=dict(msg='{{shell_out.stdout}}'))),
                # dict(action=dict(module='command', args=dict(cmd='/usr/bin/uptime'))),
            ]
        )
        play = Play().load(play_source, variable_manager=self._variable_manager, loader=self._loader)
        try:
            result = tqm.run(play)
        finally:
            tqm.cleanup()
            if self._loader:
                self._loader.cleanup_all_tmp_files()
        # Remove ansible tmpdir
        shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)

    def playbook(self,playbooks):
        """
        :param playbooks: list类型
        :return:
        """
        playbook=PlaybookExecutor(playbooks=playbooks,inventory=self._inventory,variable_manager=self._variable_manager,
                                  loader=self._loader,passwords=self._passwords)
        playbook._tqm._stdout_callback=self.result_callback
        result=playbook.run()

    def get_result(self):
        # print("UP ***********")
        # for host, result in self.result_callback.host_ok.items():
        #     print('{0} >>> {1}'.format(host, result._result['stdout']))
        #
        # print("FAILED *******")
        # for host, result in self.result_callback.host_failed.items():
        #     print('{0} >>> {1}'.format(host, result._result['msg']))
        #
        # print("DOWN *********")
        # for host, result in self.result_callback.host_unreachable.items():
        #     print('{0} >>> {1}'.format(host, result._result['msg']))

        result_raw = {"ok": {}, "failed": {}, "unreachable": {}, "skipped": {}, "status": {}}
        print("UP", "***********"*8)
        self.result_callback.host_ok.pop(0)
        for result in self.result_callback.host_ok:
            print(result)
        print("FAILED", "***********" * 8)
        for result in self.result_callback.host_failed:
            print(result)
        print("DOWN", "***********" * 8)
        for result in self.result_callback.host_unreachable:
            print(result)

        # for host, result in self._callback.task_skipped.items():
        #     result_raw["skipped"][host] = result._result
        #
        # for host, result in self._callback.task_status.items():
        #     result_raw["status"][host] = result._result


def main():
    host_list = ['/etc/ansible/hosts']
    playbook_list=['f1.yml']
    executer = AnsExecuter(host_list)
    # while True:
    #     print('input module:',end='')
    #     module=input()
    #     print('input args:',end='')
    #     args=input()
    #     executer.run(hosts='qzj',module=module,args=args)
    executer.playbook(playbooks=playbook_list)
    executer.get_result()

if __name__ == '__main__':
    main()