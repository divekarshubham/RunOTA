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
        build_task.set_application_version()
        status, build_path = build_task.build()
        print(build_path)

        if status != STATUS.PASS:
            return
        
        run_task = RunBinary(build_path)
        run_task.start()

        update_task = CreateUpdate()

        for counter in range(3):
            build_task.increase_application_build_version()
            status, build_path = build_task.build()
            if status != STATUS.PASS:
                return
            

            self.update_counter += 1
            fileToUpload = f'{basename(build_path)}_{self.update_counter}'
            update_task.setParams(fileToUpload,build_path)
            update_task.clear_pending_jobs()
            ota_update_id = update_task.create_ota_update()
            update_status, summary = update_task.get_ota_update_result(ota_update_id, 600)
            print(update_status)
            if update_status.status != "SUCCEEDED":
                break
        run_task.close()


def main():
    task = OtaCanary(OtaProject())
    task.start()

if __name__ == 'main':
    main()