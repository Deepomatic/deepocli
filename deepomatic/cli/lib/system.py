import os
import subprocess


class SystemManager(object):
    def check(self):
        print("=== Check git, deepomatic-cli installations")
        self.check_command(["git", "--version"], command_message="git")
        self.check_command(["deepo", "--version"], command_message="deepomatic-cli")

        print("=== Check docker, docker-compose and nvidia installation")
        self.check_command("docker", command_message="docker")
        self.check_command("nvidia-smi")
        self.check_command(["docker-compose", "--version"], command_message="docker-compose")
        self.check_command(["docker", "ps"], command_message="docker", success_message="is usable", error_message="is not usable")
        self.check_command(["docker", "run", "--gpus", "all", "nvidia/cuda:9.0-base", "nvidia-smi"], command_message="nvidia-docker")

        print("=== Check deepomatic api accessibility")
        self.check_command(["curl", "-Lf", "https://api.deepomatic.com"], command_message="Deepomatic API",
                           success_message="is reachable", error_message="is not reachable")

        print("=== Check deepomatic run docker images")
        self.check_command(["docker", "image", "inspect", "deepomatic/run-neural-worker:0.5.0-native"],
                           command_message="Neural worker image", success_message="is available", error_message="is not available")
        self.check_command(["docker", "image", "inspect", "deepomatic/run-workflow-server:0.5.0"],
                           command_message="Workflow server image", success_message="is available", error_message="is not available")
        self.check_command(["docker", "image", "inspect", "deepomatic/run-camera-server:0.5.0"],
                           command_message="Camera server image", success_message="is available", error_message="is not available")

    def check_command(self, command,
                      success_icon="\u2713", error_icon="\u2717",
                      command_message=None, success_message="is installed", error_message="is not installed"):
        try:
            if command_message is None:
                command_message = command if isinstance(command, str) else ' '.join(command)
            with open(os.devnull, "w") as null:
                result = subprocess.call(command, stdout=null, stderr=null)
            if result != 0:
                raise OSError
            print(success_icon, '\t', '\033[1m' + command_message + '\033[0m', success_message)
        except OSError:
            print(error_icon, '\t', '\033[1m' + command_message + '\033[0m', error_message)
