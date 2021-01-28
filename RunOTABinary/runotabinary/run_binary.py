import os
import sys
import signal
import traceback
import subprocess
from pathlib import Path
from runotabinary.logger import logger, setup_logger

class RunBinary:
    def __init__(self):
        self.print_monitor = False # Set this to true to get output on CLI
        self._stop_read = False
        self._exit_run = False
        self.mlog = setup_logger(name='monitor', file=True, log_file='logfile.txt', format='raw', terminator='')


    def _read_simulator_output(self, outStream):
        for line in iter(outStream.readline, b''):
            try:
                line = line.decode()
                if self.print_monitor:
                        logger.info(line, end='')

                self.mlog.info(line)
                self._log += line
                if self._exit_run:
                    return
            except UnicodeDecodeError:
                logger.warn(f"Unable to debug line: {line}")
            except Exception:
                self._stop_read = True
                return

    def run(self):
        # Capture SIGINT (usually Ctrl+C is pressed) and SIGTERM, and exit gracefully.
        for _signal in (signal.SIGINT, signal.SIGTERM):
            signal.signal(_signal, lambda sig, frame: sys.exit())

        try:
            logger.info(f"Arguments count: {len(sys.argv)}")
            for i, arg in enumerate(sys.argv):
                logger.info(f"Argument {i:>6}: {arg}")
            
            executable = Path(sys.argv[1])

            proc = subprocess.Popen(executable, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=executable.parent)
            with proc.stdout:
                self._read_simulator_output(proc.stdout)
            exit_status = proc.wait()
            if exit_status in [0, -13]:
                logger.info(f'Application terminated with Exit code:{exit_status}')
            else:
                logger.error(f'Closing serial read')
                self.close()
                raise RuntimeError(f'Application stopped with Exit code:{exit_status}')

        except Exception as err:  # pylint: disable=broad-except
            logger.error("Unexpected exception: " + str(err))
            traceback.print_exc()
            sys.exit(1)
    
    def close(self):
        self._exit_run = True
        self._stop_read = True

def main():
    task = RunBinary()
    task.run()

if __name__ == "__main__":
    main()