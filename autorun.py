"""
Description :   autorun - automatically run the main.py with different configs
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/4/11 23:55:49
LastEdited  :   2024/9/16 09:43:36
"""

import main as M
import sys
import os
import subprocess
from utils.utils import get_time
PYTHON_EXEC = sys.executable
SP_CWD_PATH = os.getcwd()
CUSTOM_PATH_DICT = {
    1: "config/configs/custom1.yaml",
    2: "config/configs/custom2.yaml",
    3: "config/configs/custom3.yaml",
    4: "config/configs/custom4.yaml",
    5: "config/configs/custom5.yaml",
    6: "config/configs/custom6.yaml",
    7: "config/configs/custom7.yaml",
    8: "config/configs/custom8.yaml",
    9: "config/configs/custom9.yaml",
    10: "config/configs/custom10.yaml",
    11: "config/configs/custom11.yaml",
    12: "config/configs/custom12.yaml",
    13: "config/configs/custom13.yaml",
    14: "config/configs/custom14.yaml",
    15: "config/configs/custom15.yaml",
    16: "config/configs/custom16.yaml",
    17: "config/configs/custom17.yaml",
    18: "config/configs/custom18.yaml",
    19: "config/configs/custom19.yaml",
    20: "config/configs/custom20.yaml",
    "bl": "config/configs/baseline.yaml",
    "ab": "config/configs/autobench.yaml",
    "4om_bl": "config/configs/4omini_baseline.yaml",
    "4om_ab": "config/configs/4omini_autobench.yaml",
    "4om_cb": "config/configs/4omini_correctbench.yaml",
    "cl_bl": "config/configs/claude_baseline.yaml",
    "cl_ab": "config/configs/claude_autobench.yaml",
    "cl_cb": "config/configs/claude_correctbench.yaml"
}

AUTORUN_LIST = [1, 2, 3]
RUNTIMES = 1
RUNORDER = 0  # mode 0(default): run one configs RUNTIMES times, and then run the next config; mode 1: run all configs once as an iteration, run RUNTIMES iterations 


def main(autorun_list=AUTORUN_LIST, runtimes=RUNTIMES, runorder=RUNORDER):
    start_time = get_time()
    error_msgs = []
    error_msgs_path = os.path.join("logs", "error_msgs_" + start_time + ".txt")
    print('\nstarting autorun.py')
    print('has %d custom config file(s) to run, each one run %d time(s)'%(len(autorun_list), runtimes))
    if runorder == 0:
        print('run order: run one configs %s times, and then run the next config'%(runtimes))
    elif runorder == 1:
        print('run order: run all configs once as an epoch; run %s epochs'%(runtimes))
    if runorder == 0:
        for i in autorun_list:
            for j in range(runtimes):
                # config_path = os.path.abspath(CUSTOM_PATH_DICT[i])
                config_path = CUSTOM_PATH_DICT[i]
                # cmd = f"{PYTHON_EXEC} main.py -c {config_path}"
                cmd = [PYTHON_EXEC, "main.py", "-c", config_path]
                error_msg = sub_proc_run(cmd)
                error_msgs.append(error_msg)
    elif runorder == 1:
        for j in range(runtimes):
            for i in autorun_list:
                # config_path = os.path.abspath(CUSTOM_PATH_DICT[i])
                config_path = CUSTOM_PATH_DICT[i]
                # cmd = f"{PYTHON_EXEC} main.py -c {config_path}"
                cmd = [PYTHON_EXEC, "main.py", "-c", config_path]
                error_msg = sub_proc_run(cmd)
                error_msgs.append(error_msg)
    else:
        raise Exception('no such run order mode named %d'%(runorder))
    os.makedirs(os.path.dirname(error_msgs_path), exist_ok=True)
    if not all([error_msg == "EMPTY" for error_msg in error_msgs]):
        with open(error_msgs_path, 'w') as f:
            f.write("start time: %s\n"%(start_time))
            f.write("autorun list: %s\n"%(str(autorun_list)))
            f.write("run times: %d\n"%(runtimes))
            f.write("run order: %d\n"%(runorder))
            f.write("error messages:\n")
            for error_msg in error_msgs:
                f.write(error_msg + '\n')
        print('error messages are saved to %s'%(error_msgs_path))

def sub_proc_run(command):
    error_msg = "EMPTY"
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=SP_CWD_PATH, text=True) as process:
        try:
            # read stdout and stderr in real-time
            for line in process.stdout:
                print(line, end='')
            for line in process.stderr:
                print(line, end='', file=sys.stderr)
            # if the process is still running, wait for it to complete
            retcode = process.wait()
            if retcode != 0:
                print(f"command '{command}' failed with return code {retcode}.")
                error_msg = f"command '{command}' failed with return code {retcode}."
        except Exception as e:
            print(f"An unexpected error occurred when running {command}: {e}")
            error_msg = f"An unexpected error occurred when running {command}: {e}"
    return error_msg

# if __name__ == "__main__":
#     args = len(sys.argv)
#     if args == 2:
#         if (sys.argv[1]).isdigit():
#             main(autorun_list=[int(sys.argv[1])], runtimes=1, runorder=0)
#         else:
#             raise Exception("invalid argument")
#     elif args == 1:
#         main()
#     elif args > 2:
#         auto_run_list = []
#         for i in range(1, args):
#             if (sys.argv[i]).isdigit():
#                 auto_run_list.append(int(sys.argv[i]))
#             else:
#                 raise Exception("invalid argument for the %d-th argument: %s"%(i, sys.argv[i]))
#         main(autorun_list=auto_run_list, runtimes=1, runorder=0)
#     else:
#         raise Exception("invalid arguments: %s"%(sys.argv))
if __name__ == "__main__":
    main()
    print("autorun.py finished at %s"%get_time())
    print("Done!\n\n")