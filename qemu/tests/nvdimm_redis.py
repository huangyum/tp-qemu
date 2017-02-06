import logging

from autotest.client.shared import error

from qemu.tests.nvdimm import NvdimmTest


class NvdimmRedisTest(NvdimmTest):
    """
    Class for redis test with nvdimm
    """
    def download_src(self, src_dir, uri):
        """
        Download the src code

        :param src_dir: The directory to store src code
        :param uri: The git address of the src code
        """
        print "yuhuang====download dir:", src_dir
        download_cmd = "cd %s && git clone %s" % (src_dir, uri)
        self.run_guest_cmd(download_cmd, timeout=300)

    def install_nvml(self, src_dir):
        """
        Install nvml

        :param src_dir: The src code directory
        """
        uri = self.params["nvml_uri"]
        self.download_src(src_dir, uri)
        install_cmd = "cd %s/nvml && make && make install" % src_dir
        self.run_guest_cmd(install_cmd, timeout=300)

    def redis_test(self, src_dir):
        """
        Run redis test

        :param src_dir: The src code directory
        """
        uri = self.params["redis_uri"]
        print "yuhuang=======redis uri:", uri
        print "yuhuang=====redis src_dir:", src_dir
        self.download_src(src_dir, uri)
        nvml_dir = "%s/redis/deps" % src_dir
        print "yuhuang======nvml_dir:",nvml_dir
        self.install_nvml(nvml_dir)
        make_cmd = "cd %s/redis && make USE_NVML=yes STD=-std=gnu99" % src_dir
        self.run_guest_cmd(make_cmd, timeout=300)
        test_cmd = "cd /home/redis && make test"
        self.run_guest_cmd(test_cmd, timeout=300)

    def clean(self, src_dir):
        """
        Clean guest src code

        :param src_dir: The src code directory
        """
        clean_nvml = "cd %s/redis/deps/nvml && make uninstall"
        self.run_guest_cmd(clean_nvml, check_status=False)
        clean_redis = "rm -rf %s/redis" % src_dir
        self.run_guest_cmd(clean_redis, check_status=False)


@error.context_aware
def run(test, params, env):
    """
    Run redis test with nvdimm:
    1) Boot guest with nvdimm device backed by a host file
    2) Login to the guest
    3) Check nvdimm in monitor and guest
    4) Format and mount nvdimm device in guest
    5) Install nvml and run redis test
    6) Check Calltrace in guest

    :param test: QEMU test object
    :param params: Dictionary with the test parameters
    :param env: Dictionary with test environment
    """
    nvdimm_test = NvdimmRedisTest(params, env)
    vm = env.get_vm(params["main_vm"])
    vm.verify_alive()
    src_dir = params.get("src_dir", "/home")

    try:
        error.context("Login to the guest", logging.info)
        login_timeout = int(params.get("login_timeout", 360))
        nvdimm_test.session = vm.wait_for_login(timeout=login_timeout)
        error.context("Verify nvdimm in monitor and guest", logging.info)
        nvdimm_test.verify_nvdimm(vm)
        error.context("Format and mount nvdimm in guest", logging.info)
        nvdimm_test.mount_nvdimm()
        error.context("Run redis test in guest", logging.info)
        nvdimm_test.redis_test(src_dir)
        nvdimm_test.umount_nvdimm()
        error.context("Check if error and calltrace in guest", logging.info)
        vm.verify_kernel_crash()

    finally:
        nvdimm_test.clean(src_dir)
        if nvdimm_test.session:
            nvdimm_test.session.close()
        vm.destroy()
