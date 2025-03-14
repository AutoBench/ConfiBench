"""
Description :   This is the TB syntactic checking stage in the autoline (previously named as TaskTBsim in autoline.py)
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/7/24 11:24:31
LastEdited  :   2025/2/24 21:32:19
"""

import os
import LLM_call as llm
import iverilog_call as iv
import python_call as py
import loader_saver as ls
from config import Config
from loader_saver import autologger as logger
from loader_saver import log_localprefix
from prompt_scripts import get_script, BaseScript
from utils.utils import Timer, get_time

IDENTIFIER = {
    "tb_start" : "```verilog",
    "tb_end" : "```"
}

TESTBENCH_TEMPLATE = """%s
`timescale 1ns / 1ps
(more verilog testbench code here...)
endmodule
%s""" % (IDENTIFIER["tb_start"], IDENTIFIER["tb_end"])

DEBUG_TEMPLATE = """please fix the verilog testbench code below according to the error message below. please directly give me the corrected verilog testbench codes.
Attention: never remove the irrelevant codes!!!
your verilog testbench should be like:
%s
please only reply the full code modified. NEVER remove other irrelevant codes!!!
The testbench I give you is the one with error. To be convienient, each of the line begins with a line number. The line number also appears at the error message. You should use the line number to locate the error with the help of error message.
""" % (TESTBENCH_TEMPLATE)

DEBUG_FINAL_INSTR = """ please directly give me the corrected verilog codes, no other words needed. Your verilog codes should start with [```verilog] and end with [```]."""

DEBUG_TEMPLATE_PY = """please fix the python code below according to the error message below. please directly give me the corrected python codes.
Attention: never remove the irrelevant codes!!!
please only reply the full code modified. NEVER remove other irrelevant codes!!!
The python code I give you is the one with error. To be convienient, each of the line begins with a line number. The line number also appears at the error message. You should use the line number to locate the error with the help of error message.
"""

DEBUG_FINAL_INSTR_PY = """ please directly give me the corrected python codes, no other words needed. Your python codes should start with [```python] and end with [```]."""

# will be discarded by 15/08/2024
# DEBUG_TEMPLATE_END = """
# VERY IMPORTANT: please ONLY reply the full code modified. NEVER remove other irrelevant codes!!!
# Your testbench SHOULD NOT have the line number at the beginning of each line!!!
# """

class TaskTBsim():
    """
    #### input:
    - ivcode_path:
        - the path of iverilog dir (xxx/TB_gen/), will contain all verilog files. generated .vvp will also be saved here
    #### output:
        - dict of the simulation result
            - "sim_pass" : bool (whether the simulation is successful. This is only the necessary condition of the correctness of the testbench)
            - "debug_iter" : int (the number of debug iterations)
            - "sim_out" : str (the output of the simulation)
            - "sim_err" : str (the error of the simulation)
            - "TB_gen_debugged" : str or None (the testbench code after debug)
    #### iverilog_path:
        - the path of iverilog dir, will contain all verilog files. generated .vvp will also be saved here
    #### task_id:
        - the name of the problem, will be used as the name of generated files
    file structure:
    - original
        - task_id.v
        - task_id_tb.v
        - task_id_vlist.txt
        - task_id.vvp
    - debug_1
        - task_id.v
        - task_id_tb.v
        - task_id_vlist.txt
        - task_id.vvp
    - debug_2
        - ...
    """
    def __init__(self, TBgen: BaseScript, TB_code: str, module_header: str, task_dir: str, task_id: str, config):
        self.TBgen = TBgen
        self.TB_code_now = TB_code
        self.module_header = module_header
        self.task_dir = task_dir if task_dir.endswith("/") else task_dir + "/" # for the compatibility with the old version
        self.task_id = task_id
        self.config = config
        self.working_dir = TBgen.TB_code_dir if TBgen.TB_code_dir.endswith("/") else TBgen.TB_code_dir + "/" # will change during the debug process
        self.DUT_code = module_header + "\n\nendmodule\n"
        self.debug_iter_max = config.autoline.debug.max
        self.debug_iter_to_reboot = config.autoline.debug.reboot
        self.proc_timeout = config.autoline.timeout
        # self.debug_iter_now = 0 # this is a counter for both iverilog and python so it is possible to be larger than debug_iter_max
        self.debug_iter_iv_now = 0 
        self.debug_iter_after_reboot_iv = 0 
        self.debug_iter_py_now = 0 
        self.debug_iter_after_reboot_py = 0 
        self.reboot_both = False
        # self.debug_iter_after_reboot = 0
        # pychecker related
        self.pychecker_en = self.TBgen.Pychecker_en
        self.PY_code_now = ""
        if self.pychecker_en:
            self.TBout_content = "" # will get after the last iverilog run
            self.PY_code_now = self.TBgen.Pychecker_code
            self.py_fail_reboot_both_iter = config.autoline.debug.py_rollback # will reboot both iv and py if python simulation failed xxx times
            self.py_debug_focus = self.TBgen.py_debug_focus 
        # infos
        self.sim_pass = False # this should be com_pass, but it is too late to change it now
        self.py_pass = False
        self.Eval0_pass = False
        self.iverilog_info = None
        self.reboot_both_times = 0
        self.iv_runing_time = 0.0 # the time of running the last iverilog
        self.py_runing_time = 0.0 # the time of running the last python
        self.tokens = {"prompt": 0, "completion": 0}
            
    def run(self):
        if not self.pychecker_en:
            self.run_iverilog()
            self.Eval0_pass = self.sim_pass
        else:
            exit_en = False
            while (not exit_en):
                self.run_iverilog()
                if self.sim_pass:
                    self.run_python()
                    # if (self.sim_pass and self.py_pass) or self.exceed_max_debug:
                    if not self.reboot_both:
                        exit_en = True
                else:
                    exit_en = True
                    self.Eval0_pass = False
                    raise ValueError("TBsim: iverilog failed, python simulation is not allowed.")
            self.Eval0_pass = self.sim_pass and self.py_pass
        logger.info("TBsim finished : %s!"%(self.Eval0_pass))

    def run_iverilog(self):
        """
        - the main function of TBsim
        """
        if not self.reboot_both:
            # this will only be called at the first time of runing run_iverilog
            self._save_code_run_iverilog()
            self.sim_pass = self.iverilog_info[0]
        while (self.debug_iter_iv_now < self.debug_iter_max) and (not self.sim_pass):
            self.debug_iter_iv_now += 1
            if self.debug_iter_after_reboot_iv < self.debug_iter_to_reboot:
                self.debug_iter_after_reboot_iv += 1
                self._debug_iv()
            else:
                self._reboot_iv()
            self.sim_pass = self.iverilog_info[0]
            self.reboot_both = False
        if self.reboot_both:
            # this means didn't enter the while, because debug_iter_max is already reached
            logger.info("iverilog compilation (reboot from python) : failed! iverilog exceeded max debug iteration (%s)"%(self.debug_iter_max))
        if self.sim_pass:
            logger.info("iverilog compilation : passed!")
        else:
            logger.info("iverilog compilation : failed! exceeded max debug iteration (%s)"%(self.debug_iter_max))
        # self.sim_out = self.iverilog_info[4]["out"] if self.iverilog_info[4] is not None else ""
        # self.sim_err = self.iverilog_info[-1]
        # clean .vcd wave files
        self.clean_vcd()
    
    def run_python(self):
        # read the TBout.txt into TBout_content in working_dir
        with open(self.TBout_path, "r") as f:
            self.TBout_content = f.read()
        self.debug_iter_after_reboot_py = 0
        py_rollback = 0 # local variable
        self._save_code_run_python()
        # self.debug_iter_py_now
        while (self.debug_iter_py_now < self.debug_iter_max) and (not self.python_info[0]):
            if (not self.python_info[0]) and (py_rollback >= self.py_fail_reboot_both_iter):
                # +1: debug py fail + [generated py fail]
                self.reboot_both = True
                break
            py_rollback += 1
            self.debug_iter_py_now += 1
            if self.debug_iter_after_reboot_py < self.debug_iter_to_reboot:
                self.debug_iter_after_reboot_py += 1
                self._debug_py()
            else:
                self._reboot_py()
            # self._reboot_py() # only reboot, no debugging because python debugging is much harder than verilog
            # currently debug_py doesn't support reboot
        if self.reboot_both:
            self.py_pass = False
            self.sim_pass = False
            self.debug_iter_after_reboot_iv = self.debug_iter_to_reboot
            logger.info("python simulation : failed! will reboot both iverilog and python")
        elif self.python_info[0]:
            self.py_pass = True
            logger.info("python simulation : passed!")
        else:
            self.py_pass = False
            logger.info("python simulation : failed! exceeded max debug iteration (%s)"%(self.debug_iter_max))
        self.py_out = self.python_info[1]["out"] if self.python_info[1] is not None else ""
        self.py_err = self.python_info[-1]

    def _debug_iv(self):
        with Timer(print_en=False) as debug_time:
            logger.info("iverilog simulation failed! Debuging... (debug_iter = %s)"%(self.debug_iter_iv_now))
            self.working_dir = self.task_dir + "debug_%s/" % (self.total_debug_iter_now)
            os.makedirs(self.working_dir, exist_ok=True)
            debug_prompt = self._debug_prompt_gen_iv()
            debug_message = [{"role": "user", "content": debug_prompt}]
            gpt_response, info = llm.llm_call(debug_message, self.config.gpt.model, self.config.gpt.key_path)
            debug_message = info["messages"]
            self.TB_code_now = llm.extract_code(gpt_response, "verilog")[-1]
            self.TB_code_now = self.del_linemark(self.TB_code_now)
            self._save_code_run_iverilog()
        logger.info("%s: verilog DEBUG finished (%ss used)" % (self.debug_iter_info("iv"), round(debug_time.interval, 2)))
        self.tokens["prompt"] += info["usage"]["prompt_tokens"]
        self.tokens["completion"] += info["usage"]["completion_tokens"]
        ls.save_messages_to_txt(debug_message, self.working_dir+"debug_messages.txt")

    def _reboot_iv(self):
        # change TBgen's code dir
        with Timer (print_en=False) as reboot_time:
            logger.info("iverilog simulation failed! Rebooting... (debug_iter = %s)"%(self.debug_iter_iv_now))
            self.working_dir = self.task_dir + "debug_%s_reboot/" % (self.total_debug_iter_now)
            os.makedirs(self.working_dir, exist_ok=True)
            self.TBgen.run_reboot(self.working_dir, reboot_mode="TB")
            self.TB_code_now = self.TBgen.TB_code
            self._save_code_run_iverilog()
        logger.info("%s: verilog REBOOT finished (%ss used)" % (self.debug_iter_info("iv"), round(reboot_time.interval, 2)))
        # the tookens will be added into TBgen's tokens count, we don't count it again here.
        # reset reboot counter
        self.debug_iter_after_reboot_iv = 0

    def _debug_py(self):
        with Timer(print_en=False) as debug_time:
            logger.info("python compilation failed! Debuging python... (debug_iter = %s)"%(self.debug_iter_py_now))
            self.working_dir = self.task_dir + "debug_%s/" % (self.total_debug_iter_now)
            os.makedirs(self.working_dir, exist_ok=True)
            # run gpt
            debug_prompt = self._debug_prompt_gen_py()
            debug_message = [{"role": "user", "content": debug_prompt}]
            gpt_response, info = llm.llm_call(debug_message, self.config.gpt.model, self.config.gpt.key_path)
            debug_message = info["messages"]
            self.PY_code_now = llm.extract_code(gpt_response, "python")[-1]
            self.PY_code_now = self.del_linemark(self.PY_code_now)
            if self.py_debug_focus: # currently only support pychecker SEQ mode
                self.PY_code_now = self._py_focus(self.PY_code_now, before=False)
            self._save_code_run_python()
        logger.info("%s: python DEBUG finished (%ss used)" % (self.debug_iter_info("py"), round(debug_time.interval, 2)))
        self.tokens["prompt"] += info["usage"]["prompt_tokens"]
        self.tokens["completion"] += info["usage"]["completion_tokens"]
        ls.save_messages_to_txt(debug_message, self.working_dir+"debug_messages.txt")

    def _reboot_py(self):
        # change TBgen's code dir
        with Timer (print_en=False) as reboot_time:
            logger.info("python compilation failed! Rebooting... (debug_iter = %s)"%(self.debug_iter_py_now))
            self.working_dir = self.task_dir + "debug_%s_reboot/" % (self.total_debug_iter_now)
            os.makedirs(self.working_dir, exist_ok=True)
            self.TBgen.run_reboot(self.working_dir, reboot_mode="PY")
            self.PY_code_now = self.TBgen.Pychecker_code
            self._save_code_run_python()
        logger.info("%s: python REBOOT finished (%ss used)" % (self.debug_iter_info("py"), round(reboot_time.interval, 2)))
        # the tookens will be added into TBgen's tokens count, we don't count it again here.
        # reset reboot counter
        self.debug_iter_after_reboot_py = 0 

    def _save_code_run_iverilog(self):
        with open(self.TB_path, "w") as f:
            f.write(self.TB_code_now)
        with open(self.DUT_path, "w") as f:
            f.write(self.DUT_code)
        with Timer(print_en=False) as iverilog_time:
            self.iverilog_info = iv.iverilog_call_and_save(self.working_dir, silent=True, timeout=self.proc_timeout)
        self.iv_runing_time = round(iverilog_time.interval, 2)
        self.error_message_now = self.iverilog_info[-1]
        if "program is timeout" in self.error_message_now:
            # if the error message is timeout, we will delete the TBout.txt
            # this is to avoid the situation that infinite loop produces a large TBout.txt
            if os.path.exists(self.TBout_path):
                os.remove(self.TBout_path)
            self.clean_vvp()
    
    def _save_code_run_python(self):
        with open(self.PY_path, "w") as f:
            f.write(self.PY_code_now)
        with open(self.TBout_path, "w") as f:
            f.write(self.TBout_content)
        with Timer(print_en=False) as python_time:
            self.python_info = py.python_call_and_save(pypath=self.PY_path, silent=True, timeout=self.proc_timeout)
        self.py_runing_time = round(python_time.interval, 2)
        self.error_message_now = self.python_info[-1]

    def _debug_prompt_gen_iv(self):
        debug_prompt = DEBUG_TEMPLATE + "\n previous testbench with error:\n" + self.add_linemark(self.TB_code_now) + "\n compiling error message:\n" + self.error_message_now
        return debug_prompt
    
    def _debug_prompt_gen_py(self):
        if self.py_debug_focus:
            py_code = self._py_focus(self.PY_code_now, before=True)
        else:
            py_code = self.PY_code_now
        if not ("program is timeout" in self.error_message_now):
            self.error_message_now = self._py_error_message_simplify(self.error_message_now)
        debug_prompt = DEBUG_TEMPLATE_PY + "\n previous python code with error:\n" + self.add_linemark(py_code) + "\n compiling error message:\n" + self.error_message_now + DEBUG_FINAL_INSTR_PY
        return debug_prompt
    
    def _py_focus(self, code:str, before:bool):
        """
        - code: the code under debug / after debug
        - before: True, if before debug, will split the code; False, if after debug, will restore the code
        """
        # KEY_WORD = "\ndef check_dut"
        KEY_WORDs_1 = "def check_dut(vectors_in):\n    golden_dut = GoldenDUT()\n    failed_scenarios = []"
        KEY_WORDs_2 = "\ndef SignalTxt_to_dictlist"
        if before:
            key_words = KEY_WORDs_1 if KEY_WORDs_1 in code else KEY_WORDs_2
            if key_words not in code:
                py_code_focus = code
                self.py_code_nofocus = ""
            else:
                py_code_focus = code.split(key_words)[0]
                self.py_code_nofocus = key_words + code.split(key_words)[1]
            return py_code_focus
        else:
            return code + self.py_code_nofocus

    @staticmethod
    def _py_error_message_simplify(error_message:str, error_depth:int=1):
        """
        - extract the key point of python error message
        - error_depth: how many (how deep, from bottom to top) error messages to extract
        """
        msg_lines = error_message.split("\n")
        msg_out = ""
        for line in reversed(msg_lines):
            msg_out = line + "\n" + msg_out
            if "File" in line:
                error_depth -= 1
                if error_depth == 0:
                    break
        return msg_out

    @property
    def exceed_max_debug(self):
        return (self.debug_iter_iv_now >= self.debug_iter_max) or (self.debug_iter_py_now >= self.debug_iter_max)

    @property
    def total_debug_iter_now(self):
        return self.debug_iter_iv_now + self.debug_iter_py_now

    @property
    def TB_path(self):
        return self.working_dir + self.task_id + "_tb.v"
    
    @property
    def DUT_path(self):
        return self.working_dir + self.task_id + ".v"
    
    @property
    def PY_path(self):
        return self.working_dir + self.task_id + "_tb.py"
    
    @property
    def TBout_path(self):
        return self.working_dir + "TBout.txt"
    
    def debug_iter_info(self, type):
        """return debug iter info string. Type: "iv" or "py" """
        if self.pychecker_en:
            if type == "iv":
                return "verilog iter - %d/%d, total - %d/%d"%(self.debug_iter_iv_now, self.debug_iter_max, self.total_debug_iter_now, self.debug_iter_max*2)
            elif type == "py":
                return "python tier - %d/%d, total - %d/%d"%(self.debug_iter_py_now, self.debug_iter_max, self.total_debug_iter_now, self.debug_iter_max*2)
            else:
                raise ValueError("TaskTBsim.debug_iter_info(type): type should be 'iv' or 'py'")
        else:
            # only iverilog
            return "debug iter %d/%d"%(self.debug_iter_iv_now, self.debug_iter_max)

    @staticmethod
    def add_linemark(code: str):
        """add the line mark (1., 2., ...) to the code at the beginning of each line"""
        code = code.split("\n")
        code = [str(i+1) + ". " + line for i, line in enumerate(code)]
        return "\n".join(code)
    
    @staticmethod
    def del_linemark(code: str):
        """delete the line mark at the begening of each line if line mark exists"""
        code = code.split("\n")
        if code[1].split(".")[0].isdigit(): # use code[1] in case the first line is empty
            code = [line.split(". ")[1:] for line in code]
            for i, line in enumerate(code):
                code[i] = ". ".join(line)
        return "\n".join(code)
    
    def clean_vcd(self):
        """clean the .vcd files in the task_dir"""
        clean_dir = self.task_dir[:-1] if self.task_dir.endswith("/") else self.task_dir
        for root, dirs, files in os.walk(clean_dir):
            for file in files:
                if file.endswith(".vcd"):
                    os.remove(os.path.join(root, file))
    
    def clean_vvp(self):
        """clean the .vvp files in the task_dir"""
        clean_dir = self.task_dir[:-1] if self.task_dir.endswith("/") else self.task_dir
        for root, dirs, files in os.walk(clean_dir):
            for file in files:
                if file.endswith(".vvp"):
                    os.remove(os.path.join(root, file))