"""
Description :   The prompt script for pychecker workflow
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/3/22 10:40:43
LastEdited  :   2024/7/24 19:59:51
"""

from ..base_script import BaseScript, BaseScriptStage
from . import script_RTLchecker0306
from .script_RTLchecker0306 import StageChecklist
from ..utils import given_TB
from .. import utils

class WF_pychecker_CMB(BaseScript):
    """
    stages: stage1, stage2, stage3, stage3b, stage4
    check: check "scenario list"(stage2) in stage 4
    """
    def __init__(self, prob_data:dict, task_dir:str, config:object):
        super().__init__(prob_data, task_dir, config)
        self.max_check_iter = self.config.autoline.checklist.max
        self.py_code = ""

    def make_and_run_stages(self):
        # stage1
        self.stage1 = Stage1(self.prob_data, **self.gptkwargs)
        self.stage_operation(self.stage1)
        # stage2
        self.stage2 = Stage2(self.prob_data, self.stage1.response, **self.gptkwargs)
        self.stage_operation(self.stage2)
        # stage3
        self.stage3 = Stage3(self.prob_data, self.stage1.response, self.stage2.response, **self.gptkwargs)
        self.stage_operation(self.stage3)
        # stage4
        self.stage4 = Stage4(self.prob_data, self.stage1.response, self.stage2.response, **self.gptkwargs)
        self.stage_operation(self.stage4)
        # stagechecklist
        self.stagecheck = StageChecklist(self.TB_code, self.stage2.response, self.max_check_iter, **self.gptkwargs)
        self.stage_operation(self.stagecheck)
        # stage5
        self.stage5 = Stage5(self.prob_data, self.stage1.response, self.stage3.response, **self.gptkwargs)
        self.stage_operation(self.stage5)
        # self.TB_code += "\n" + stage3b.response   

    def make_and_run_reboot_stages(self, debug_dir):
        if self.reboot_mode == "TB":
            # stage4
            self.stage4 = Stage4(self.prob_data, self.stage1.response, self.stage2.response, **self.gptkwargs)
            self.stage_operation(self.stage4, debug_dir, reboot_en=True)
            # stagechecklist
            self.stagecheck = StageChecklist(self.TB_code, self.stage2.response, self.max_check_iter, **self.gptkwargs)
            self.stage_operation(self.stagecheck, debug_dir, reboot_en=True)
        elif self.reboot_mode == "PY":
            # stage5
            self.stage5 = Stage5(self.prob_data, self.stage1.response, self.stage3.response, **self.gptkwargs)
            self.stage_operation(self.stage5, debug_dir, reboot_en=True)
        else:
            raise ValueError("invalid reboot_mode in WF_pychecker script (circuit type: CMB)")

class Stage1(script_RTLchecker0306.Stage1):
    """
    stage1 for pychecker, the same as RTLchecker0306.Stage1
    """
    def __init__(self, prob_data:dict, **gptkwargs):
        super().__init__(prob_data, **gptkwargs)

class Stage2(script_RTLchecker0306.Stage2):
    """
    stage2 for pychecker, the same as RTLchecker0306.Stage2
    """
    def __init__(self, prob_data:dict, response_stage1:str, **gptkwargs):
        super().__init__(prob_data, response_stage1, **gptkwargs)

class Stage3(script_RTLchecker0306.Stage3):
    """
    stage3 for pychecker, the same as RTLchecker0306.Stage3
    """
    def __init__(self, prob_data:dict, response_stage1:str, response_stage2:str, **gptkwargs):
        super().__init__(prob_data, response_stage1, response_stage2, **gptkwargs)

SIGNALTEMP_PLACEHOLDER_1 = "/* SIGNAL TEMPLATE 1 */"
SIGNALTEMP_PLACEHOLDER_1A = "/* SIGNAL TEMPLATE 1A */"
SIGNALTEMP_PLACEHOLDER_1B = "/* SIGNAL TEMPLATE 1B */"

# STAGE4_TXT1 = """
# 1. Your task is to complete a given verilog testbench code. This testbench is for a verilog RTL module code (we call it as "DUT", device under test). This circuit is a combinational circuit. The infomation we have is 
# - 1.1. the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". 
# - 1.2. the module header.
# - 1.3. test scenarios which determines values of test vectors
# - 1.4. the testbench structure
# - 1.5. the instruction of writing our testbench

# 2. you are in section 4. in this section, our target is to generate the verilog testbench for the DUT. This testbench can export the input and output signals of DUT at the important time points. The exported data will be send to a python script to check the correctness of DUT. 
# ATTENTION: The testbench does not need to check the DUT's output but only export the signals of DUT.
# Instruction of saving signals to file: 
# (1) you should use $fopen and $fdisplay to export the important signals in testbench. the file name is "TBout.txt".
# (2) In each scenario, 
# (3) Attention: before $fdisplay, you should always have a delay statement to make sure the signals are stable.
# (4) the signals you save is the input and output of DUT, you should determine the signals according to DUT's header:
# """%(SIGNALTEMP_PLACEHOLDER_1, SIGNALTEMP_PLACEHOLDER_1A, SIGNALTEMP_PLACEHOLDER_1B)

# STAGE4_TXT2 = """
# The testbench does not need to check the DUT's output but only export the signals of DUT.
# Instruction of saving signals to file: 
# (1) you should use $fopen and $fdisplay to export the important signals in testbench. the file name is "TBout.txt". 
# (2) When running testbench, for one time point, you should export 1 line. the example of the printed line is "%s"; If one scenario has multiple test cases, use letter suffix to represent different test cases, like "%s", "%s".
# (3) Attention: before $fdisplay, you should always have a delay statement to make sure the signals are stable.
# (4) the signals you save is the input and output of DUT, you should determine the signals according to DUT's header.
# please only generate the verilog codes, no other words.
# """%(SIGNALTEMP_PLACEHOLDER_1, SIGNALTEMP_PLACEHOLDER_1A, SIGNALTEMP_PLACEHOLDER_1B)
STAGE4_TXT1 = """
1. Your task is to complete a given verilog testbench code. This testbench is for a verilog RTL module code (we call it as "DUT", device under test). This circuit is a combinational circuit. The infomation we have is 
- 1.1. the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". 
- 1.2. the module header.
- 1.3. test scenarios which determines values of test vectors
- 1.4. the testbench structure
- 1.5. the instruction of writing our testbench
"""

STAGE4_TXT2 = """
The testbench does not need to check the DUT's output but only export the signals of DUT. Please export the signals of DUT to a file named "TBout.txt" at the end of each scenario. The template is given below:
%s
If you need a loop in a scenario to check multiple time points, use "repeat" loop. for exmaple:
```
// scenario x
scenario = x;
signal_1 = 1;
repeat(5) begin
    %s
    #10;
end
```
Please determine the input signal's exact values according to given test scenarios. 
Note: please complete the last initial code part (marked in the given testbench template). You should give me the completed full code. The testbench template above is to help you generate the code. You must use %%d when exporting values.
please generate the full testbench code. please only reply verilog codes, no other words. 
"""%(SIGNALTEMP_PLACEHOLDER_1, SIGNALTEMP_PLACEHOLDER_1)

class Stage4(BaseScriptStage):
    """stage 4: generate the testbench that export the signals of DUT to a file"""
    def __init__(self, prob_data, response_stage1, response_stage2, **gptkwargs) -> None:
        super().__init__("stage_4", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage2 = response_stage2
        self.fdisplay_template = utils.fdisplay_code_gen(prob_data["header"], False)
        self.TB_code_object = given_TB(prob_data["header"])
        self.txt1 = STAGE4_TXT1
        self.txt2 = STAGE4_TXT2.replace(SIGNALTEMP_PLACEHOLDER_1, self.fdisplay_template)

    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line(self.txt1)
        # DUT header
        self.add_prompt_line("DUT header:")
        self.add_prompt_line(self.prob_data["header"])
        # other information:
        self.add_prompt_line("Your other information:")
        # problem description
        self.add_prompt_line("DUT circuit problem description:")
        self.add_prompt_line(self.prob_data["description"])
        # # specification
        # self.add_prompt_line("testbench specification:")
        # self.add_prompt_line(self.response_stage1)
        # rules
        self.add_prompt_line("IMPORTANT - test scenario (Please determine the values of input signals according to these test scenarios.):")
        self.add_prompt_line(self.response_stage2)
        # given codes
        self.add_prompt_line("below is the given testbench codes:")
        self.add_prompt_line(self.TB_code_object.gen_template())
        # end
        self.add_prompt_line(self.txt2)

    def postprocessing(self):
        # verilog codes
        self.response = self.extract_code(self.response, "verilog")[-1]
        self.TB_code_out = self.response
        self.TB_code_out = utils.verilog_patch(self.TB_code_out)

STAGE5_CMB_TXT1 = """
1. background: Your task is to verify the functional correctness of a verilog RTL module code (we call it as "DUT", device under test). This module is a combinational circuit. Our plan is to first export the signals (input and output) of the DUT under test scenarios. Then, we will use a python script to check the correctness of DUT.
2. You are in stage 5. In this stage, we already exported the signals of DUT. The signals are like below: (the signal names are real, but the values are just for example)
%s
, where The "scenario" is not DUT's signal but to tell you the current scenario index. 
3. Your current task is to write a python script to check the correctness of DUT. The main function is "check(vector: dict) -> bool". Your function "check" should return True if the DUT is correct under the input signals, otherwise return False. The input "vector" is a dictionary containing the signals of DUT. The keys are signal name and the values are the signal values (int or "x"). "x" means the signal is unknown (not important). the function "check" will be called by other codes later.
4. You can write other functions to help you check the correctness of DUT. You can use binary (like 0b1011), hexadeciaml (like 0x1a) or normal number format in python for convenience.
5. Hints:
- You can use binary (like 0x1101), hexadecimal (like 0x1a) or normal number format in python.
- if the bit width of one variable is limited, use bit mask to assure the correctness of the value.
- you can import numpy, math, scipy or other python libraries to help you write the python class.
6. You have the information below to help you check the correctness of DUT:
"""%(SIGNALTEMP_PLACEHOLDER_1)

STAGE5_CMB_TXT2 = """
[IMPORTANT]
I will repeat the important information here:
3. Your current task is to write a python script to check the correctness of DUT. The main function is "check(vector: dict) -> bool". Your function "check" should return True if the DUT is correct under the input signals, otherwise return False. The input "vector" is a dictionary containing the signals of DUT. The keys are signal name and the values are the signal values (int or "x"). "x" means the signal is unknown (not important). the function "check" will be called by other codes later.
4. You can write other functions to help you check the correctness of DUT. You can use binary (like 0b1011), hexadeciaml (like 0x1a) or normal number format in python for convenience.
5. Hints:
- You can use binary (like 0x1101), hexadecimal (like 0x1a) or normal number format in python.
- if the bit width of one variable is limited, use bit mask to assure the correctness of the value.
- you can import numpy, math, scipy or other python libraries to help you write the python class.

please only generate the function "check" and other functions you need. example:
```python
def check(vector: dict) -> bool:
    # your code here

def function1(signals1):
    # your code here

def function2(signals2):
    # your code here
#finish
```
We only need python functions, no other codes.
"""

STAGE5_CMB_CODE1 = """
def check_dut(vectors_in):
    failed_scenarios = []
    for vector in vectors_in:
        check_pass = check(vector)
        if check_pass:
            print(f"Passed; vector: {vector}")
        else:
            print(f"Failed; vector: {vector}")
            failed_scenarios.append(vector["scenario"])
    return failed_scenarios
"""

STAGE5_CMB_CODE2 = """
def SignalTxt_to_dictlist(txt:str):
    signals = []
    lines = txt.strip().split("\\n")
    for line in lines:
        signal = {}
        line = line.strip().split(", ")
        for item in line:
            if "scenario" in item:
                item = item.split(": ")
                signal["scenario"] = item[1].replace(" ", "")
            else:
                item = item.split(" = ")
                key = item[0]
                value = item[1]
                if ("x" not in value) and ("X" not in value) and ("z" not in value):
                    signal[key] = int(value)
                else:
                    if ("x" in value) or ("X" in value):
                        signal[key] = 0 # used to be "x"
                    else:
                        signal[key] = 0 # used to be "z"
        signals.append(signal)
    return signals
with open("TBout.txt", "r") as f:
    txt = f.read()
vectors_in = SignalTxt_to_dictlist(txt)
tb_pass = check_dut(vectors_in)
print(tb_pass)
"""
class Stage5(BaseScriptStage):
    """stage 5: generate the pychecker that receive the signals from testbench and check the correctness of DUT"""
    def __init__(self, prob_data, response_stage1, response_stage3, **gptkwargs) -> None:
        super().__init__("stage_5", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage3 = response_stage3 # currently not used
        self.txt1 = STAGE5_CMB_TXT1.replace(SIGNALTEMP_PLACEHOLDER_1, utils.signal_dictlist_template(prob_data["header"], exclude_clk=True))
        self.txt2 = STAGE5_CMB_TXT2
        self.pycode_tail = STAGE5_CMB_CODE1 + STAGE5_CMB_CODE2

    def make_prompt(self):
        self.prompt = ""
        # introduction
        self.add_prompt_line(self.txt1)
        # problem description
        self.add_prompt_line("DUT circuit problem description:")
        self.add_prompt_line(self.prob_data["description"])
        # header
        self.add_prompt_line("DUT header:")
        self.add_prompt_line(self.prob_data["header"])
        # specification
        self.add_prompt_line("Checker specification:")
        self.add_prompt_line(self.response_stage1)
        # python rules (optional)
        self.add_prompt_line("Here is the basic rules in python for the module. It is generated in previous stage. You can use it as a reference, but you should write your own python script. This is just for your better understanding:")
        self.add_prompt_line(self.response_stage3)
        # end
        self.add_prompt_line(self.txt2)

    def postprocessing(self):
        # python codes
        self.response = self.extract_code(self.response, "python")[0]
        self.Pychecker_code_out = self.response + self.pycode_tail