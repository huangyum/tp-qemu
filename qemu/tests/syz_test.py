import re
import time
import logging

from avocado.utils import cpu
from avocado.utils import process
from virttest import env_process
from virttest import error_context


@error_context.context_aware
def run(test, params, env):
    """
    :param test: QEMU test object
    :param params: Dictionary with the test parameters
    :param env: Dictionary with test environment.
    """
    
    def install_syz(cmd):
        output = process.getoutput(cmd)
        print("yuhuang-----output:", output)
    
    def run_syz(config):
        cmd = "rm -rf /usr/bin/qemu-system-x86_64 && cp /usr/libexec/qemu-kvm /usr/bin/qemu-system-x86_64"
        process.system(cmd, shell=True)
        cmd = "cd /home/syz_test/gopath/src/github.com/google/syzkaller/bin"
        cmd += " && ./syz-manager -config=%s" % config
        print("yuhuang--------Run syzkaller...")
        process.system(cmd, shell=True, timeout=3600*24*14)
    
    vm = env.get_vm(params["main_vm"])
    vm.verify_alive()
    session = vm.wait_for_login()
    guest_ip = vm.get_address()
    try:
        session.cmd_status_output("yum install -y kernel-debug",timeout=360)
        ker_ver = session.cmd_output("uname -r").strip()
        session.cmd_output("grubby --default-kernel")
        session.cmd_output("grubby --set-default=/boot/vmlinuz-%s+debug" % ker_ver)
        session.cmd_output("grubby --default-kernel")
        process.system("yes | ssh-keygen -t rsa -N \"\" -f ~/.ssh/id_rsa", shell=True)
        process.system("yum install -y sshpass")
        process.system('sshpass -p kvmautotest ssh-copy-id -o "StrictHostKeyChecking no" -i /root/.ssh/id_rsa.pub root@%s' % guest_ip)
        vm.destroy()
        #time.sleep(300)
        install_syz(params["install_syz"])
        config = "/home/syz_test/test.config"
        run_syz(config)
    except Exception as details:
        print("yuhuang-----except:", details)
    finally:
        print("yuhuang-----sleep600")
        status = process.system("ls /home/syz_test/workdir/crashes/")
        if status:
            test.fail("Crashed...")
