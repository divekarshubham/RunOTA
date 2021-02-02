import os
import sys
import signal
import traceback
import subprocess
from pathlib import Path
from datetime import datetime
from threading import Thread
from runotabinary.logger import logger, setup_logger

class RunBinary(Thread):
    def __init__(self, filename, logfilename=None):
        Thread.__init__(self)

        self.print_monitor = False # Set this to true to get output on CLI
        self._stop_read = False
        self._exit_run = False
        self.executable = Path(filename)
        self.initial_exe = filename
        self.run_indefinitely = True # Set this to false for 1 run
        self.file_version = 2
        if logfilename:
            self.log_output = logfilename
        else:
            self.log_output = f'{datetime.now().strftime("%m%d%H%S")}_logfile.txt'

        self.clear_file(self.log_output)
        logger.info(f'Logging the run to {self.log_output}')
        self.mlog = setup_logger(name='monitor', file=True, log_file=self.log_output, format='raw', terminator='')

    def clear_file(self, filename):
        """
        Create directory if not exist. Clear the file in filename if file exist.
        :param filename:
        :return:
        """
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        open(filename, "w").close()

    def _read_simulator_output(self, outStream):
        for line in iter(outStream.readline, b''):
            try:
                line = line.decode()
                if self.print_monitor:
                        logger.info(line)
                self.mlog.info(line)
                if self._exit_run:
                    return
            except UnicodeDecodeError:
                logger.warn(f"Unable to debug line: {line}")
            except Exception as e:
                logger.error(f"Exception in binary: {e}")
                self._stop_read = True
                return

    def run(self):
        try:
            while self._stop_read == False:
                logger.info(f'Running binary: {self.executable}')

                proc = subprocess.Popen(self.executable, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.executable.parent)
                with proc.stdout:
                    self._read_simulator_output(proc.stdout)
                exit_status = proc.wait()
                if exit_status in [0, -13]:
                    logger.info(f'Application terminated with Exit code:{exit_status}')
                else:
                    logger.error(f'Closing serial read')
                    self.close()
                    raise RuntimeError(f'Application stopped with Exit code:{exit_status}')
                
                if self.run_indefinitely:
                    self.executable = Path(f'{self.initial_exe}_{self.file_version}')
                    self.file_version += 1
                    cmd = f'sudo chmod 777 {self.executable}'.split()
                    result = subprocess.run(cmd, cwd=self.executable.parent, capture_output=True)
                    print(result.stdout)
        except Exception as err:  # pylint: disable=broad-except
            logger.error("Unexpected exception: " + str(err))
            traceback.print_exc()
            sys.exit(1)
    
    def close(self):
        self._exit_run = True
        self._stop_read = True

def main():
    # Capture SIGINT (usually Ctrl+C is pressed) and SIGTERM, and exit gracefully.
    for _signal in (signal.SIGINT, signal.SIGTERM):
        signal.signal(_signal, lambda sig, frame: sys.exit())

    log_output = None
    file_name = sys.argv[1]
    if len(sys.argv) == 3:
        log_output = sys.argv[2]
    task = RunBinary(file_name, log_output)
    task.start()

if __name__ == "__main__":
    main()