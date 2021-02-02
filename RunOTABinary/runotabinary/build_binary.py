import traceback
import subprocess
import os
import re
import sys
import fileinput
import boto3
from subprocess import PIPE, STDOUT
from runotabinary.configs.config_project import OtaProject
from runotabinary.logger import logger
from pathlib import Path
from enum import Enum
from datetime import datetime

STATUS = Enum("STATUS", "PASS FAIL ERROR TIMEOUT")

class BuildBinary:
    def __init__(self, ota_project):
        self.project = ota_project
        #TODO self.project.check_setup()

        self.ota_targets = [
            'ota_demo_core_mqtt',
            'ota_demo_core_http'
        ]

        if "MQTT" in self.project.data_protocol:
            self.ota_firmware_path_used_in_job = self.ota_targets[0]
        else:
            self.ota_firmware_path_used_in_job = self.ota_targets[1]

        # OTA_TARGET should be replaced by real target name listed above when source
        # instrumentation is done.
        self.DEMO_CONFIG_PATH = Path(f'demos/ota/OTA_TARGET/demo_config.h')
        self.OTA_CONFIG_PATH = Path(f'demos/ota/OTA_TARGET/ota_config.h')
        self.OTA_CODESIGNER_CERTIFICATE_PATH = Path(f'platform/posix/ota_pal/source/ota_pal_posix.c')
        self.OTA_DEMO_PATH = Path(f'demos/ota/OTA_TARGET/OTA_TARGET.c')
        self.OTA_PAL_PATH = Path('platform/posix/ota_pal/source/ota_pal_posix.c')


        self.set_identifier_in_file(
            {
                '#define AWS_IOT_ENDPOINT': '\"' + self.project.aws_iot_endpoint + '\"',
                '#define CLIENT_CERT_PATH': '\"' + self.project.client_cert_path + '\"',
                '#define CLIENT_PRIVATE_KEY_PATH': '\"' + self.project.client_private_key_path + '\"',
                '#define CLIENT_IDENTIFIER': '\"' + self.project.thing_name + '\"'
            },
            os.path.join(self.project.repository_root, self.DEMO_CONFIG_PATH)
        )

        self.set_codesigner_certificate(self.get_code_signer_certificate_from_arn())
    
    def set_identifier_in_file(self, prefixToValue, filePath):
        """
        CSDK has multiple targets to be built for tests. They have different source
        files.  This call will change source files for all targets.
        """
        for target in self.ota_targets:
            target_path = Path(str(filePath).replace('OTA_TARGET', target))
            logger.debug(target_path)
            macros = "|".join(prefixToValue.keys())
            is_comment = False
            buffer = []
            ignore_list = []
            macros_regex = re.compile(macros)
            # for line in host_tools_afr._process_file(path):
            for line in fileinput.input(files=target_path, inplace=True):
                if "/*" in line:
                    is_comment = True
                if "*/" in line:
                    is_comment = False
                match = macros_regex.search(line)
                if match:
                    matched_macro = match.group()
                    if prefixToValue[matched_macro] is not None:
                        prefixToValue_line = '{} {}\n'.format(matched_macro, prefixToValue[matched_macro])
                        if matched_macro in ignore_list:
                            line = "____ignore_this__line_"
                        else:
                            ignore_list.append(matched_macro)
                            if is_comment:
                                buffer.append(prefixToValue_line)
                            else:
                                line = prefixToValue_line
                if line != "____ignore_this__line_":
                    sys.stdout.write(line)
                if not is_comment and buffer:
                    sys.stdout.write("".join(buffer))
                    buffer = []

    def build(self):
        logger.info("Building image")
        try:
            cmd = f'cmake -S . -B build && cmake --build build --target {self.ota_firmware_path_used_in_job}'
            with open (f'{self.ota_firmware_path_used_in_job}_{datetime.now().strftime("%m%d%H%S")}_build_log.txt', 'w') as buildlog :
                result = subprocess.run(
                    cmd, stdout=buildlog, stderr=STDOUT, shell=True, encoding="utf-8", cwd=str(self.project.repository_root), check=True
                )    

            file_path = f'{self.project.repository_root}/build/bin/'
            self.latest_build_firmware_path = f"{file_path}{self.ota_firmware_path_used_in_job}"

        except Exception as e:
            logger.error(f"Error occured: {e}")
            traceback.print_exc()
            return STATUS.ERROR, ''

        logger.info("Build completed")
        return STATUS.PASS, self.latest_build_firmware_path

    def set_application_version(self, major=None, minor=None, build=None):
        """Set aws_application_version.h with the input version.

        Initialization version is usually 0.9.0 unless given otherwise.
        OTA Canary uses non-default version to update.
        """
        if major == None:
            major = self.project.version_major

        if minor == None:
            minor = self.project.version_minor

        if build == None:
            build = self.project.version_build

        self.set_identifier_in_file(
            {
                '#define APP_VERSION_MAJOR': major,
                '#define APP_VERSION_MINOR': minor,
                '#define APP_VERSION_BUILD': build
            },
            os.path.join(self.project.repository_root, self.DEMO_CONFIG_PATH)
        )
        logger.debug(f'Setting version {major}.{minor}.{build} in {self.DEMO_CONFIG_PATH}')

    def increase_application_build_version(self):
        """Increase the build version and store it
        """
        self.project.version_build += 1
        self.set_application_version(build = self.project.version_build)
    
    def set_codesigner_certificate(self, certificate):
        """Set aws_ota_codesigner_certificate.h with the certificate specified.
        """
        codeSignerCertificatePath = os.path.join(self.project.repository_root, self.OTA_CODESIGNER_CERTIFICATE_PATH)
        signerCertificateTag = 'static const char signingcredentialSIGNING_CERTIFICATE_PEM[] = '
        for line in fileinput.input(files=codeSignerCertificatePath, inplace=True):
            if (signerCertificateTag in line):
                line = '{} {}\n'.format(signerCertificateTag, '\"' + certificate.replace('\n', '\\n') + '\";')
            sys.stdout.write(line)
    
    def get_code_signer_certificate_from_arn(self, certArn=None):
        """
        Get the certificate stored in ACM identified by the input ARN.
        If we are running in the beta stage, the certificate ARN for the designated region
        should have been configured the board configuration JSON.
        """
        if not certArn:
            certArn = self.project.ecdsa_signer_certificate_arn

        certificate = ''
        certificate = boto3.client('acm').get_certificate(CertificateArn=certArn)['Certificate']
        return certificate

def main():
    task = BuildBinary(OtaProject())
    task.increase_application_build_version()    
    task.build()

if __name__ == "__main__":
    main()