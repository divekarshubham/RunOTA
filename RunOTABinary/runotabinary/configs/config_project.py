from pprint import pformat
from pathlib import Path
from dataclasses import dataclass, asdict

from runotabinary.logger import logger



@dataclass
class OtaProject:
    """
    Representation of a project for OTA
    """

    # Data Protocol: Should be either "MQTT" or "HTTP" or "MIXED"
    data_protocol: str = "MQTT"#"'SETUP:protocol'"

    # AWS configuration
    s3_bucket_name: str = "'SETUP:s3_bucket_name'"
    ota_update_role_arn: str = "'SETUP:ota_update_role_arn'"
    ecdsa_signer_certificate_arn: str = "'SETUP:ecdsa_signer_certificate_arn'"
    signer_platform: str = "AmazonFreeRTOS-Default"
    signer_certificate_file_name: str = "ecdsa-sha256-signer.crt.pem"
    signer_oid: str = "sig-sha256-ecdsa"
    ota_timeout_sec: int = 600
    thing_name: str = 'adfada'#"'SETUP:thing_name'"

    # Source configuration
    repository_root: Path = Path('/home/ubuntu/dev/csdk/aws-iot-device-sdk-embedded-C')#Path("'SETUP:repository_root'")
    version_major: int = 0
    version_minor: int = 9
    version_build: int = 0
    client_cert_path: str = "ajfdakljfl"#None
    client_private_key_path: str = "ajfdakljfl"#None
    aws_iot_endpoint: str = "ajfdakljfl"#None


    # Monitor configuration
    device_firmware_file_name: str = "aws_demos.bin"
    print_monitor: bool = False

    def pretty(self):
        return f"OTA Project dataclass:\n{pformat(asdict(self), width=150)}"

    def check_setup(self):
        # TODO [C] may want to phrase it as "REQUIRED" instead of "SETUP"
        if "SETUP" in self.pretty():
            logger.error("Please configure OTA project properly:")
            logger.info(self.pretty())
            logger.error(
                "Fix any 'SETUP' strings by either adding to CLI or config_user.py"
            )
            exit(1)
