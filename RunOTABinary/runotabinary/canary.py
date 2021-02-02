from os.path import basename
from pathlib import Path
from runotabinary.configs.config_project import OtaProject
from runotabinary.logger import logger
from runotabinary.build_binary import BuildBinary, STATUS
from runotabinary.run_binary import RunBinary
from runotabinary.create_update import CreateUpdate



class OtaCanary:
    def __init__(self, ota_project):
        self.project = ota_project
        self.update_counter = 1
    
    def start(self):
        build_task = BuildBinary(self.project)
        status, build_path = build_task.build()
        print(build_path)
        if status == STATUS.PASS:
            run_task = RunBinary(build_path)
            run_task.start()

            build_task.increase_application_build_version()
            status, build_path = build_task.build()
            print(build_path)

            self.update_counter += 1
            fileToUpload = f'{basename(build_path)}_{self.update_counter}'
            update_task = CreateUpdate(fileToUpload, build_path)
            update_task.clear_pending_jobs()
            ota_update_id = update_task.create_ota_update()
            update_status = update_task.get_ota_update_result(ota_update_id, 600)
            print(update_status)


def main():
    task = OtaCanary(OtaProject())
    task.start()

if __name__ == 'main':
    main()