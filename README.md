# RunOTA

## Requirements
1. Python 3.6+
2. Install poetry using `curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -`

## Getting Started

### Running the image with python
1. Clone the repo: `git clone git@github.com:divekarshubham/RunOTA.git && cd RunOTA/RunOTABinary`
2. Install the requirements using `poetry install`
3. Run the exe with the command `poetry run agent <filepath> <[Optional]logging file>` eg: `poetry run agent ~/ota/ota_demo_core_mqtt ~/ota/logs/logfile.txt`

### Building image with Python
1. Specify the configurations of the project like cert path in `config_project.py`
2. Specify the project to build in `repository_root` in `config_project.py` e.g. `Path('/home/ubuntu/dev/csdk/aws-iot-device-sdk-embedded-C')`
3. Build using the command `poetry run build`

### Creating an OTA update
1. Specify the configurations of the project like bucket_name and update_role_arn in `config_project.py`
2. Specify the project to build in `repository_root` in `config_project.py` e.g. `Path('/home/ubuntu/dev/csdk/aws-iot-device-sdk-embedded-C')`
3. Create an update with `poetry run update <filename> <filepath>`. <filename> is the name of the binary when it is downloaded and <filepath> contains the actual binary to upload. e.g. `poetry run update ota_demo_core_mqtt2 /home/ubuntu/dev/csdk/aws-iot-device-sdk-embedded-C/build/bin/ota_demo_core_mqtt`

### Interrupting an MQTT connection to the cloud
1. Update the certificate, private key and endpoint in the `config_project.py`
2. Establish a connection using `poetry run interrupt`
