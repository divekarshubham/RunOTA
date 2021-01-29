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
2. Build using the command `poetry agent build`
