import subprocess

def check_requirements(*args, **kwargs):
    def check_requirement(command, success_message, error_message):
        try:
            output = subprocess.check_output(command.split())
            print('%s: %s' % (success_message, output))
            return True
        except:
            print('%s\n' % error_message)
            return False
    requirements = {
        'docker': 'docker --version',
        'docker-compose': 'docker-compose --version',
        'nvidia-docker': 'nvidia-docker --version',
    }
    checks = [check_requirement(command, '%s is installed' % requirement, '%s is not installed' % requirement) for (requirement, command) in requirements.items()]
    if all(checks):
        print('on-premises requirements are installed')
        return True
    else:
        print('on-premises requirements are not matched')
        return False