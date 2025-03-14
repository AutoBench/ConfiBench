"""
Description :   The prompt script for pychecker workflow
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/3/22 10:40:43
LastEdited  :   2024/7/24 19:59:05
"""

from ..base_script import BaseScript, BaseScriptStage
from . import script_RTLchecker0306
from . import script_RTLmulticheckers
from .script_RTLchecker0306 import StageChecklist


class WF_pychecker(BaseScript):
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
        self.stage1 = script_RTLchecker0306.Stage1(self.prob_data, **self.gptkwargs)
        self.stage_operation(self.stage1)
        self.circuit_type = self.stage1.spec_dict.get("circuit type", "CMB")
        # stage2
        self.stage2 = script_RTLchecker0306.Stage2(self.prob_data, self.stage1.response, **self.gptkwargs)
        self.stage_operation(self.stage2)
        # stage3
        self.stage3 = Stage3(self.prob_data, self.stage1.response, self.stage2.response, **self.gptkwargs)
        self.stage_operation(self.stage3)
        # decide according to circuit type
        if self.circuit_type == "SEQ":
            # stage4
            self.stage4 = Stage4_SEQ(self.prob_data, self.stage1.response, self.stage2.response, **self.gptkwargs)
            self.stage_operation(self.stage4)
            # stagechecklist
            self.stagecheck = StageChecklist(self.TB_code, self.stage2.response, self.max_check_iter, **self.gptkwargs)
            self.stage_operation(self.stagecheck)
            self.stage4b = Stage4b_SEQ(self.prob_data, self.TB_code, **self.gptkwargs)
            self.stage_operation(self.stage4b)
            # # stage4b
            # stage4b = Stage4b_SEQ(self.prob_data, stage4.TB_code_out, **self.gptkwargs)
            # self.stage_operation(stage4b)
            # stage5
            self.stage5 = Stage5_SEQ(self.prob_data, self.stage1.response, self.stage3.response, **self.gptkwargs)
            self.stage_operation(self.stage5) 
        else:
            # stage4
            self.stage4 = Stage4_CMB(self.prob_data, self.stage1.response, self.stage2.response, **self.gptkwargs)
            self.stage_operation(self.stage4)
            # stagechecklist
            self.stagecheck = StageChecklist(self.TB_code, self.stage2.response, self.max_check_iter, **self.gptkwargs)
            self.stage_operation(self.stagecheck)
            # stage5
            self.stage5 = Stage5_CMB(self.prob_data, self.stage1.response, self.stage3.response, **self.gptkwargs)
            self.stage_operation(self.stage5)
            # self.TB_code += "\n" + stage3b.response  

    def make_and_run_reboot_stages(self, debug_dir):
        if self.circuit_type == "SEQ":
            if self.reboot_mode == "TB":
                # stage4
                self.stage4 = Stage4_SEQ(self.prob_data, self.stage1.response, self.stage2.response, **self.gptkwargs)
                self.stage_operation(self.stage4, debug_dir, reboot_en=True)
                # stagechecklist
                self.stagecheck = StageChecklist(self.TB_code, self.stage2.response, self.max_check_iter, **self.gptkwargs)
                self.stage_operation(self.stagecheck, debug_dir, reboot_en=True)
                # stage4b
                self.stage4b = Stage4b_SEQ(self.prob_data, self.TB_code, **self.gptkwargs)
                self.stage_operation(self.stage4b, debug_dir, reboot_en=True)
            elif self.reboot_mode == "PY":
                # stage5
                self.stage5 = Stage5_SEQ(self.prob_data, self.stage1.response, self.stage3.response, **self.gptkwargs)
                self.stage_operation(self.stage5, debug_dir, reboot_en=True)
            else:
                raise ValueError("invalid reboot_mode in WF_pychecker script (circuit type: SEQ)")
        else: 
            if self.reboot_mode == "TB":
                # stage4
                self.stage4 = Stage4_CMB(self.prob_data, self.stage1.response, self.stage2.response, **self.gptkwargs)
                self.stage_operation(self.stage4, debug_dir, reboot_en=True)
                # stagechecklist
                self.stagecheck = StageChecklist(self.TB_code, self.stage2.response, self.max_check_iter, **self.gptkwargs)
                self.stage_operation(self.stagecheck, debug_dir, reboot_en=True)
            elif self.reboot_mode == "PY":
                # stage5
                self.stage5 = Stage5_CMB(self.prob_data, self.stage1.response, self.stage3.response, **self.gptkwargs)
                self.stage_operation(self.stage5, debug_dir, reboot_en=True)
            else:
                raise ValueError("invalid reboot_mode in WF_pychecker script (circuit type: CMB)")


SIGNALTEMP_PLACEHOLDER_1 = "/* SIGNAL TEMPLATE 1 */"
SIGNALTEMP_PLACEHOLDER_1A = "/* SIGNAL TEMPLATE 1A */"
SIGNALTEMP_PLACEHOLDER_1B = "/* SIGNAL TEMPLATE 1B */"

STAGE3_TXT1="""1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The infomation we have is the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". Our target is to generate the verilog testbench for the DUT. This testbench can check if the DUT in verilog satisfies all technical requirements of the problem description.
2. you are in section 3; in this section, please give me the core rules of an ideal DUT. you should give these rules in python. (For convenience, you can use binary or hexadecimal format in python, i.e. 0b0010 and 0x1a). Later we will use these ideal rules to generate expected values in each test scenario. currently you must only generate the rules. the input of these rules should be related to the test vectors from test scenario. the rule should give the expected values under test vectors. You can use numpy, scipy or other third party libraries to help you write the rules. Please import them if you need. 
3. your information is:"""

class Stage3(BaseScriptStage):
    def __init__(self, prob_data, response_stage1, response_stage2, **gptkwargs) -> None:
        super().__init__("stage_3", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage2 = response_stage2
        self.txt1 = STAGE3_TXT1

    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line(self.txt1)
        # problem description
        self.add_prompt_line("RTL circuit problem description:")
        self.add_prompt_line(self.prob_data["description"])
        # specification
        self.add_prompt_line("RTL testbench specification:")
        self.add_prompt_line(self.response_stage1)
        # DUT header
        self.add_prompt_line("DUT header:")
        self.add_prompt_line(self.prob_data["header"])
        # test scenarios
        self.add_prompt_line("test scenario: (please note the test vectors below, it will help you determine the input parameters of the rules)")
        self.add_prompt_line(self.response_stage2)
        # end
        self.add_prompt_line("your response should only contain python code. For convenience, you can use binary or hexadecimal format in python. For example: 0b0010 and 0x1a")

    def postprocessing(self):
        # extract python codes; codes may be more than one
        python_codes = self.extract_code(self.response, "python")
        response = ""
        for python_code in python_codes:
            response += python_code + "\n"
        self.response = response

STAGE4_CMB_TXT1 = """
1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The infomation we have is 
- 1.1. the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". 
- 1.2. the module header.
- 1.3. the technical specification of testbench
- 1.4. test scenarios which determines value and sequential information of test vectors

2. you are in section 4. in this section, our target is to generate the verilog testbench for the DUT. This testbench can export the input and output signals of DUT at the important time points. The exported data will be send to a python script to check the correctness of DUT. 
ATTENTION: The testbench does not need to check the DUT's output but only export the signals of DUT.
Instruction of saving signals to file: 
(1) you should use $fopen and $fdisplay to export the important signals in testbench. the file name is "TBout.txt".
(2) When running testbench, for one time point, you should export 1 line. the example of the printed line is "%s"; If one scenario has multiple test cases, use letter suffix to represent different test cases, like "%s", "%s".
(3) Attention: before $fdisplay, you should always have a delay statement to make sure the signals are stable.
(4) the signals you save is the input and output of DUT, you should determine the signals according to DUT's header:
"""%(SIGNALTEMP_PLACEHOLDER_1, SIGNALTEMP_PLACEHOLDER_1A, SIGNALTEMP_PLACEHOLDER_1B)

STAGE4_CMB_TXT2 = """
The testbench does not need to check the DUT's output but only export the signals of DUT.
Instruction of saving signals to file: 
(1) you should use $fopen and $fdisplay to export the important signals in testbench. the file name is "TBout.txt". 
(2) When running testbench, for one time point, you should export 1 line. the example of the printed line is "%s"; If one scenario has multiple test cases, use letter suffix to represent different test cases, like "%s", "%s".
(3) Attention: before $fdisplay, you should always have a delay statement to make sure the signals are stable.
(4) the signals you save is the input and output of DUT, you should determine the signals according to DUT's header.
please only generate the verilog codes, no other words.
"""%(SIGNALTEMP_PLACEHOLDER_1, SIGNALTEMP_PLACEHOLDER_1A, SIGNALTEMP_PLACEHOLDER_1B)

class Stage4_CMB(BaseScriptStage):
    """stage 4 (CMB): generate the testbench that export the signals of DUT to a file"""
    def __init__(self, prob_data, response_stage1, response_stage2, **gptkwargs) -> None:
        super().__init__("stage_4", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage2 = response_stage2
        self.txt1 = STAGE4_CMB_TXT1
        self.txt2 = STAGE4_CMB_TXT2
        self.txt1 = self.txt1.replace(SIGNALTEMP_PLACEHOLDER_1, header_to_SignalTxt_template(prob_data["header"], signal_value=r"%d"))
        self.txt1 = self.txt1.replace(SIGNALTEMP_PLACEHOLDER_1A, header_to_SignalTxt_template(prob_data["header"], "1a", signal_value=r"%d"))
        self.txt1 = self.txt1.replace(SIGNALTEMP_PLACEHOLDER_1B, header_to_SignalTxt_template(prob_data["header"], "1b", signal_value=r"%d"))
        self.txt2 = self.txt2.replace(SIGNALTEMP_PLACEHOLDER_1, header_to_SignalTxt_template(prob_data["header"], signal_value=r"%d"))
        self.txt2 = self.txt2.replace(SIGNALTEMP_PLACEHOLDER_1A, header_to_SignalTxt_template(prob_data["header"], "1a", signal_value=r"%d"))
        self.txt2 = self.txt2.replace(SIGNALTEMP_PLACEHOLDER_1B, header_to_SignalTxt_template(prob_data["header"], "1b", signal_value=r"%d"))

    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line(self.txt1)
        # DUT header
        self.add_prompt_line(self.prob_data["header"])
        # other information:
        self.add_prompt_line("Your other information:")
        # problem description
        self.add_prompt_line("RTL circuit problem description:")
        self.add_prompt_line(self.prob_data["description"])
        # specification
        self.add_prompt_line("RTL testbench specification:")
        self.add_prompt_line(self.response_stage1)
        # rules
        self.add_prompt_line("IMPORTANT - test scenario:")
        self.add_prompt_line(self.response_stage2)
        # end
        self.add_prompt_line(self.txt2)

    def postprocessing(self):
        # verilog codes
        self.response = self.extract_code(self.response, "verilog")[-1]
        self.TB_code_out = self.response


STAGEPYGEN_PYFORMAT = """Your python scritp should contain a function "check_dut", its header is "def check_dut(test_vectors:list) -> bool:". It can also call other functions you write in this script. If all test scenarios passed, function "check_dut" should return an empty list [], otherwise it should return the list of failed scenarios indexes. You can use binary (like 0x1101), hexadecimal (like 0x1a) or normal number format in python.""" # TODO: later this function will also show the failed scenario idx

STAGEPYGEN_TXT1 = """
1. background: Your task is to verify the functional correctness of a verilog RTL module code (we call it as "DUT", device under test). Our plan is to first export the signals (input and output) of the DUT under test scenarios. Then, we will use a python script to check the correctness of DUT.
2. You are in the last stage. In this stage, we already export the signals of DUT. Your task is to write a python script. The python script contains one main function "check_dut" and other functions to be called by "check_dut" (this is optional). The input of "check_dut" is the signals of DUT in the format below: (the signal names are real, but the values are just for example)
%s
The main function "check_dut" should check the correctness according to the input signals. The input signals are all in decimal format. It will be called by other codes later.
3. %s 
4. You have the information below to help you check the correctness of DUT:
"""%(SIGNALTEMP_PLACEHOLDER_1, STAGEPYGEN_PYFORMAT)

STAGEPYGEN_TXT2 = """
[IMPORTANT] %s
Optional: You can also use functions from numpy and scipy to help you check the correctness of DUT.
you can use binary (like 0b1011), hexadeciaml (like 0x1a) or normal number format in python for convenience. 
please only generate the python codes, no other words.
"""%(STAGEPYGEN_PYFORMAT)

STAGEPYGEN_TAIL = """
def SignalTxt_to_dictlist(txt:str):
    lines = txt.strip().split("\\n")
    signals = []
    for line in lines:
        signal = {}
        line = line.strip().split(", ")
        for item in line:
            if "scenario" in item:
                item = item.split(": ")
                signal["scenario"] = item[1]
            else:
                item = item.split(" = ")
                key = item[0]
                value = item[1]
                if "x" not in value and "z" not in value:
                    signal[key] = int(value)
                else:
                    signal[key] = value 
        signals.append(signal)
    return signals
with open("TBout.txt", "r") as f:
    txt = f.read()
vectors_in = SignalTxt_to_dictlist(txt)
tb_pass = check_dut(vectors_in)
print(tb_pass)
"""
class Stage5_CMB(BaseScriptStage):
    """stage 5 (CMB): generate the pychecker that receive the signals from testbench and check the correctness of DUT"""
    def __init__(self, prob_data, response_stage1, response_stage3, **gptkwargs) -> None:
        super().__init__("stage_5", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage3 = response_stage3 # currently not used
        self.txt1 = STAGEPYGEN_TXT1.replace(SIGNALTEMP_PLACEHOLDER_1, self.signal_dictlist_template(prob_data["header"]))
        self.txt2 = STAGEPYGEN_TXT2
        self.pycode_tail = STAGEPYGEN_TAIL

    def make_prompt(self):
        self.prompt = ""
        # introduction
        self.add_prompt_line(self.txt1)
        # problem description
        self.add_prompt_line("RTL circuit problem description:")
        self.add_prompt_line(self.prob_data["description"])
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
        self.response = self.extract_code(self.response, "python")[-1]
        self.Pychecker_code_out = self.response + self.pycode_tail

    @staticmethod
    def signal_dictlist_template(header:str) -> str:
        """
        for the automatic generation of signals in testbench
        target: given the DUT header, generate the signal output template
        eg: if we have a DUT header like "module DUT(input a, b, c, output d, e);", the signal output template should be like "[{"scenario": "1", "a": 1, "b": 0, "c":1, "d": 0, "e": 0}, {"scenario": "2", "a": 0, "b": 0, "c":1, "d": 0, "e": 0}]"
        """
        signals1 = header_to_SignalTxt_template(header, "1")
        signals2 = header_to_SignalTxt_template(header, "2")
        signals_dictlist1 = SignalTxt_to_dictlist(signals1)
        signals_dictlist2 = SignalTxt_to_dictlist(signals2)
        signals_dictlist = signals_dictlist1 + signals_dictlist2
        return str(signals_dictlist)

    
def header_to_SignalTxt_template(header:str, template_scenario_idx:str="1", signal_value:str="0"):
    """
    - header: the header of DUT
    - template_scenario_idx: the scenario index in the template
    - signal_value: the value of the signal in the template
    - only: None: both input signal and output signal; "input": only input signal; "output": only output signal
    - from header to signals in txt
    - for the automatic generation of signals in testbench
    - target: given the DUT header, generate the signal output template
    - eg: if we have a DUT header like "module DUT(input a, b, c, output d, e);", the signal output template should be like "scenario: 1, a = 1, b = 0, c = 1, d = 0, e = 0"
    """
    signals = header.split("(")[1].split(")")[0].split(",")
    # remove the "input" and "output" keywords
    signals = [signal.strip().split(" ")[-1] for signal in signals]
    # generate the signal output template
    signal_out = "scenario: " + template_scenario_idx
    for signal in signals:
        signal_out += f", {signal} = {signal_value}"
    return signal_out

def SignalTxt_to_dictlist(txt:str) -> list:
    """
    - from txt to list of dicts
    - this function is used to extract signals and scenario information from a out.txt file. 
    - the TBout.txt file is generated by testbench, which is in the pychecker workflow
    - the format of each line in TBout.txt is like:
    - "scenario: x, a = x, b = x, c = x, d = x, e = x"
    - we want: [{"scenario": x, "a": x, ...}, {...}]
    """
    lines = txt.strip().split("\n")
    signals = []
    for line in lines:
        signal = {}
        line = line.strip().split(", ")
        for item in line:
            if "scenario" in item:
                item = item.split(": ")
                signal["scenario"] = item[1]
            else:
                item = item.split(" = ")
                key = item[0]
                value = item[1]
                if "x" not in value and "z" not in value:
                    signal[key] = int(value)
                else:
                    signal[key] = value 
        signals.append(signal)
    return signals

# STAGE4_SEQ_TXT1 = """
# 1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). This circuit is a sequential circuit. The infomation we have is 
# - 1.1. the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". 
# - 1.2. the module header.
# - 1.3. test scenarios which determines value and sequential information of test vectors
# - 1.4. the testbench structure
# - 1.5. the instruction of writing our testbench

# 2. you are in section 4. in this section, our target is to generate the verilog testbench for the DUT. Your task is to complement the given testbench code. This testbench can export the input and output signals of DUT at the important time periods. The exported data will be send to a python script to check the correctness of DUT. 
# ATTENTION: The testbench does not need to check the DUT's output but only export the signals of DUT.
# """

# STAGE4_SEQ_INSTR = """
# The design Instruction is:
# (0) the clock period is 10 ns. the clock signal will flip every 5 ns.
# (1) you should use $fopen and $fdisplay to export the important signals in testbench. the file name is "TBout.txt".
# (2) [IMPORTANT] In each scenario, you need to export signal lines every clock cycle (10 ns) like this:
# // scenario x begins:
# //codes here to set input signals; %s #10;
# //codes here to set input signals (optional); %s #10
# ...
# // finally, check the value:
# #10; %s
# // scenario x ends
# Attention: you should display the signals every clock cycle. When it is time to check the output value of DUT, add [check] at the beginning of the output line
# There is a example testbench for a DFF circuit:
# ```
# // the input of DFF is "d", the output of DFF is "q", the clock signal is "clk"
# // scenario 1: test the function of DUT:
# d = 1; $fdisplay(file, "scenario: 1, clk = %%d, d = %%d, q = %%d", clk, d, q); #10; // set the input signal, display
# $fdisplay(file, "[check]scenario: 1, clk = %%d, d = %%d, q = %%d", clk, d, q); #10; // check the output signal, display
# // scenario 2
# d = 0; $fdisplay(file, "scenario: 2, clk = %%d, d = %%d, q = %%d", clk, d, q); #10;
# $fdisplay(file, "[check]scenario: 2, clk = %%d, d = %%d, q = %%d", clk, d, q); #10;
# ...
# ```
# In one scenario, every clock cycle you should display the signals. When it is time to check the output value of DUT, add [check] at the beginning of the output line
# (3) the signals you save is the input and output of DUT, you should determine the signals according to DUT's header
# """%(SIGNALTEMP_PLACEHOLDER_1, SIGNALTEMP_PLACEHOLDER_1, SIGNALTEMP_PLACEHOLDER_1A)

# STAGE4_GIVEN_CODES = """

# """

# STAGE4_SEQ_TXT2 = r"""
# The testbench does not need to check the DUT's output but only export the signals of DUT. Please determine the input signal's exact values according to given test scenarios. please only complement the last initial code part. your code should begin from the "initial begin..." part to "end". You must use %d when exporting values.
# """
# class Stage4_SEQ(BaseScriptStage):
#     """stage 4 (SEQ): generate the testbench that export the signals of DUT to a file"""
#     def __init__(self, prob_data, response_stage1, response_stage2, **gptkwargs) -> None:
#         super().__init__("stage_4", **gptkwargs)
#         self.prob_data = prob_data
#         self.response_stage1 = response_stage1
#         self.response_stage2 = response_stage2
#         signals_input_template = self.header_to_SignalTxt_template(prob_data["header"], check_en=False)
#         signals_output_template = self.header_to_SignalTxt_template(prob_data["header"], check_en=True)
#         self.txt_instruction = STAGE4_SEQ_INSTR.replace(SIGNALTEMP_PLACEHOLDER_1, signals_input_template).replace(SIGNALTEMP_PLACEHOLDER_1A, signals_output_template)
#         self.txt1 = STAGE4_SEQ_TXT1
#         self.txt2 = self.txt_instruction + STAGE4_SEQ_TXT2
#         self.TB_code_object = given_TB(prob_data["header"])
#         # signal_template_scenario = signals_input_template + "\n" + signals_input_template + "\n" + signals_input_template + "\n" + signals_output_template

#     def make_prompt(self):
#         self.prompt = ""
#         self.add_prompt_line(self.txt1)
#         # DUT header
#         self.add_prompt_line(self.prob_data["header"])
#         # other information:
#         self.add_prompt_line("Your other information:")
#         # problem description
#         self.add_prompt_line("RTL circuit problem description:")
#         self.add_prompt_line(self.prob_data["description"])

#         # rules
#         self.add_prompt_line("IMPORTANT - test scenario:")
#         self.add_prompt_line(self.response_stage2)
#         # design instruction
#         self.add_prompt_line(self.txt_instruction)
#         # given codes
#         self.add_prompt_line("below is the given testbench codes:")
#         self.add_prompt_line(self.TB_code_object.gen_template())
#         # end
#         self.add_prompt_line(self.txt2)

#     def postprocessing(self):
#         # verilog codes
#         self.response = self.extract_code(self.response, "verilog")[-1]
#         self.TB_code_object.TB_code_test = self.response
#         self.TB_code_out = self.TB_code_object.gen_template()

#     @staticmethod
#     def extract_signals(header):
#         def get_width_ifhave(signal):
#             if len(signal) > 2 and "[" in signal[1] and "]" in signal[1]:
#                 # remove other parts except the [x:x]
#                 width = signal[1]
#                 width = width.split("[")[1].split("]")[0]
#                 width = "[" + width + "]"
#                 return width
#             else:
#                 return ""
#         signals = header.split("(")[1].split(")")[0].split(",")
#         signals = [signal.strip().split(" ") for signal in signals]
#         signals = [{"name": signal[-1], "width": get_width_ifhave(signal), "type": signal[0]} for signal in signals]
#         return signals

#     @staticmethod
#     def header_to_SignalTxt_template(header:str, check_en = False):
#         """
#         - header: the header of DUT
#         - template_scenario_idx: the scenario index in the template
#         - signal_value: the value of the signal in the template
#         - only: None: both input signal and output signal; "input": only input signal; "output": only output signal
#         - from header to signals in txt
#         - for the automatic generation of signals in testbench
#         - target: given the DUT header, generate the signal output template
#         - eg: if we have a DUT header like "module DUT(input clk, load, data, output q);", the signal output template should be like "$fdisplay(file, "scenario: %d, clk = %d, load = %d, data = %d, q = %d", scenario, clk, load, data, q);"
#         """
#         signals = Stage4_SEQ.extract_signals(header)
#         # generate ", clk = %d, load = %d, data = %d, q = %d"
#         signal_form1 = ""
#         signal_form2 = ""
#         for signal in signals:
#             signal_form1 += f", {signal['name']} = %d"
#             signal_form2 += f", {signal['name']}"
#         if check_en:
#             txt = r'$fdisplay(file, "[check]scenario: %d' + signal_form1 + r'", scenario' + signal_form2 + r');'
#         else:
#             txt = r'$fdisplay(file, "scenario: %d' + signal_form1 + r'", scenario' + signal_form2 + r');'
#         return txt

STAGE4_SEQ_TXT1 = """
1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). This circuit is a sequential circuit. The infomation we have is 
- 1.1. the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". 
- 1.2. the module header.
- 1.3. test scenarios which determines value and sequential information of test vectors
- 1.4. the testbench structure
- 1.5. the instruction of writing our testbench
"""

STAGE4_SEQ_INSTR = """
The design Instruction is:
(0) the clock period is 10 ns. the clock signal will flip every 5 ns.
(1) you should use $fopen and $fdisplay to export the important signals in testbench. the file name is "TBout.txt".
(2) [IMPORTANT] In each scenario, you need to export signal lines every clock cycle (10 ns) like this:
// scenario x begins:
//codes here to set input signals; %s #10;
//codes here to set input signals (optional); %s #10
...
// finally, check the value:
#10; %s
// scenario x ends
Attention: you should display the signals every clock cycle. When it is time to check the output value of DUT, add [check] at the beginning of the output line
There is a example testbench for a DFF circuit:
```
// the input of DFF is "d", the output of DFF is "q", the clock signal is "clk"
// scenario 1: test the function of DUT:
d = 1; $fdisplay(file, "scenario: 1, clk = %%d, d = %%d, q = %%d", clk, d, q); #10; // set the input signal, display
$fdisplay(file, "[check]scenario: 1, clk = %%d, d = %%d, q = %%d", clk, d, q); #10; // check the output signal, display
// scenario 2
d = 0; $fdisplay(file, "scenario: 2, clk = %%d, d = %%d, q = %%d", clk, d, q); #10;
$fdisplay(file, "[check]scenario: 2, clk = %%d, d = %%d, q = %%d", clk, d, q); #10;
...
```
In one scenario, every clock cycle you should display the signals. When it is time to check the output value of DUT, add [check] at the beginning of the output line
(3) the signals you save is the input and output of DUT, you should determine the signals according to DUT's header
"""%(SIGNALTEMP_PLACEHOLDER_1, SIGNALTEMP_PLACEHOLDER_1, SIGNALTEMP_PLACEHOLDER_1A)


# STAGE4_SEQ_TXT2 = r"""
# The testbench does not need to check the DUT's output but only export the signals of DUT. Please determine the input signal's exact values according to given test scenarios. please only complement the last initial code part. your code should begin from the "initial begin..." part to "end". You must use %d when exporting values.
# """
STAGE4_SEQ_TXT2 = """
The testbench does not need to check the DUT's output but only export the signals of DUT. Please export the signals of DUT to a file named "TBout.txt" at the end of each scenario. The template is given below:
%s
This output will be used to check the correctness of the DUT's output later.
please use #10 as the delay when you need. If you need longer delay, you can use multiple #10.
Please determine the input signal's exact values according to given test scenarios. please only complement the last initial code part. your code should begin from the "initial begin..." part to "end". You must use %%d when exporting values. Don't use meaningless long delay in your code.
"""%(SIGNALTEMP_PLACEHOLDER_1)
class Stage4_SEQ(BaseScriptStage):
    """stage 4 (SEQ): generate the testbench that export the signals of DUT to a file"""
    def __init__(self, prob_data, response_stage1, response_stage2, **gptkwargs) -> None:
        super().__init__("stage_4", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage2 = response_stage2
        signals_output_template = self.header_to_SignalTxt_template(prob_data["header"], check_en=True)
        # self.txt_instruction = STAGE4_SEQ_INSTR.replace(SIGNALTEMP_PLACEHOLDER_1, signals_input_template).replace(SIGNALTEMP_PLACEHOLDER_1A, signals_output_template)
        self.txt1 = STAGE4_SEQ_TXT1
        self.txt2 = STAGE4_SEQ_TXT2.replace(SIGNALTEMP_PLACEHOLDER_1, signals_output_template)
        self.TB_code_object = given_TB(prob_data["header"])
        # signal_template_scenario = signals_input_template + "\n" + signals_input_template + "\n" + signals_input_template + "\n" + signals_output_template

    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line(self.txt1)
        # DUT header
        self.add_prompt_line("DUT header:")
        self.add_prompt_line(self.prob_data["header"])
        # other information:
        self.add_prompt_line("Your other information:")
        # problem description
        self.add_prompt_line("RTL circuit problem description:")
        self.add_prompt_line(self.prob_data["description"])

        # rules
        self.add_prompt_line("IMPORTANT - test scenario:")
        self.add_prompt_line(self.response_stage2)
        # given codes
        self.add_prompt_line("below is the given testbench codes:")
        self.add_prompt_line(self.TB_code_object.gen_template())
        # end
        self.add_prompt_line(self.txt2)

    def postprocessing(self):
        # verilog codes
        self.response = self.extract_code(self.response, "verilog")[-1]
        self.TB_code_object.TB_code_test = self.response
        self.TB_code_out = self.TB_code_object.gen_template()

    @staticmethod
    def extract_signals(header):
        def get_width_ifhave(signal):
            if len(signal) > 2 and "[" in signal[-2] and "]" in signal[-2]:
                # remove other parts except the [x:x]
                width = signal[-2]
                width = width.split("[")[1].split("]")[0]
                width = "[" + width + "]"
                return width
            else:
                return ""
        signals = header.split("(")[1].split(")")[0].split(",")
        signals = [signal.strip().split(" ") for signal in signals]
        signals = [{"name": signal[-1], "width": get_width_ifhave(signal), "type": signal[0]} for signal in signals]
        return signals

    @staticmethod
    def header_to_SignalTxt_template(header:str, check_en = False):
        """
        - header: the header of DUT
        - template_scenario_idx: the scenario index in the template
        - signal_value: the value of the signal in the template
        - only: None: both input signal and output signal; "input": only input signal; "output": only output signal
        - from header to signals in txt
        - for the automatic generation of signals in testbench
        - target: given the DUT header, generate the signal output template
        - eg: if we have a DUT header like "module DUT(input clk, load, data, output q);", the signal output template should be like "$fdisplay(file, "scenario: %d, clk = %d, load = %d, data = %d, q = %d", scenario, clk, load, data, q);"
        """
        signals = Stage4_SEQ.extract_signals(header)
        # generate ", clk = %d, load = %d, data = %d, q = %d"
        signal_form1 = ""
        signal_form2 = ""
        for signal in signals:
            signal_form1 += f", {signal['name']} = %d"
            signal_form2 += f", {signal['name']}"
        if check_en:
            txt = r'$fdisplay(file, "[check]scenario: %d' + signal_form1 + r'", scenario' + signal_form2 + r');'
        else:
            txt = r'$fdisplay(file, "scenario: %d' + signal_form1 + r'", scenario' + signal_form2 + r');'
        return txt

class given_TB(script_RTLmulticheckers.testbench_template):
    def __init__(self, header) -> None:
        super().__init__(header)
        """
        1. initialize sim time, module testbench and signals
        2. initialize "integer file, scenario;"
        3. instantiate the DUT
        4. clock generation (if have)
        5. scenario based test
        6. endmodule
        """
        self.TB_code_head = ""
        self.TB_code_head += "`timescale 1ns / 1ps\nmodule testbench;\n"
        self.TB_code_head += self.initial_signals(self.signals) + "\n"
        self.TB_code_head += "integer file, scenario;\n"
        self.TB_code_head += "// DUT instantiation\n"
        self.TB_code_head += self.instantiate_module_by_signals("top_module", "DUT", self.signals) + "\n"
        self.TB_code_head += self.clock_generation()
        self.TB_code_head += '\ninitial begin\n    file = $fopen("TBout.txt", "w");\nend\n'
        # self.TB_code_test = '// Test scenarios\ninitial begin\n    file = $fopen("TBout.txt", "w");\n\n    // write your codes here\n\n    $fclose(file);\n    $finish;\nend\n'
        self.TB_code_test = '// Test scenarios\ninitial begin\n\n    // write your scenario checking codes here, according to scenario information\n\n    $fclose(file);\n    $finish;\nend\n'
        self.TB_code_tail = "\nendmodule\n"
    
    def gen_template(self):
        return self.TB_code_head + self.TB_code_test + self.TB_code_tail

    def clock_generation(self):
        clk_en = False
        for signal in self.signals:
            if signal["name"] == "clk":
                clk_en = True
                break
        if not clk_en:
            return ""
        else:
            return "// Clock generation\ninitial begin\n    clk = 0;\n    forever #5 clk = ~clk;\nend\n"

Stage4b_SEQ_TXT1 = """given the scenario based verilog testbench code below:"""
Stage4b_SEQ_TXT2 = """
please help me to export the input of DUT module by using code below:

[IMPORTANT]:
%s

you should insert the code above into scenario checking part. In each scenario, you should insert the code above after the input of DUT module changed. Don't delete the existing $display codes.

For example:
original code:
signal_1 = 1; #10; // insert $fdisplay here
signal_2 = 1; #10; // insert $fdisplay here
$fdisplay(file, "[check]scenario: %%d, signal_1 = %%d, signal_2 = %%d", scenario, signal_1, signal_2); // this should be reserved.
after insertion:
signal_1 = 1;  $fdisplay(file, "scenario: %%d, signal_1 = %%d, signal_2 = %%d", scenario, signal_1, signal_2); #10;
signal_2 = 1;  $fdisplay(file, "scenario: %%d, signal_1 = %%d, signal_2 = %%d", scenario, signal_1, signal_2); #10;
$fdisplay(file, "[check]scenario: %%d, signal_1 = %%d, signal_2 = %%d", scenario, signal_1, signal_2);

please insert codes according to the rules above. please reply the modified full codes. please only reply verilog codes, no other words."""%(SIGNALTEMP_PLACEHOLDER_1)
class Stage4b_SEQ(BaseScriptStage):
    def __init__(self, prob_data, TB_code, **gptkwargs) -> None:
        super().__init__("stage_4b", **gptkwargs)
        self.header = prob_data["header"]
        signals_input_template = Stage4_SEQ.header_to_SignalTxt_template(prob_data["header"], check_en=False)
        self.TB_code = TB_code
        self.txt1 = Stage4b_SEQ_TXT1
        self.txt2 = Stage4b_SEQ_TXT2.replace(SIGNALTEMP_PLACEHOLDER_1, signals_input_template)
        self.TB_code_out = self.TB_code

    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line(self.txt1)
        self.add_prompt_line(self.TB_code)
        self.add_prompt_line(self.txt2)
        
    def postprocessing(self):
        self.TB_code_out = self.extract_code(self.response, "verilog")[-1]



STAGEPYGEN_SEQ_PYFORMAT = """Your python scritp should contain a function "check_dut", its header is "def check_dut(test_vectors:list) -> bool:". It can also call other functions you write in this script. If all test scenarios passed, function "check_dut" should return an empty list [], otherwise it should return the list of failed scenarios indexes. You can use binary (like 0x1101), hexadecimal (like 0x1a) or normal number format in python.""" # TODO: later this function will also show the failed scenario idx

STAGEPYGEN_SEQ_TXT1 = """
1. background: Your task is to verify the functional correctness of a verilog RTL module code (we call it as "DUT", device under test). This module is a sequential circuit. Our plan is to first export the signals (input and output) of the DUT under test scenarios. Then, we will use a python script to check the correctness of DUT.
2. You are in the last stage. In this stage, we already exported the signals of DUT. The DUT is a digital sequential circuit. Your task is to write a python script. The python script contains one main function "check_dut" and other functions to be called by "check_dut" (this is optional). The input of "check_dut" is the signals of DUT and other information in the format below: (the signal names are real, but the values are just for example)
%s
The "scenario" is not DUT's signal but to tell you the current scenario index. The "check_en" signal is not from the DUT. "Check_en" is a bool value to tell you this is the time to check the output of DUT. If "check_en" is False, it means this is the time to load the input signals. Therefore, your python script should have two modes: "load" and "check". After checking the output, a new scenario will begin.
The main function "check_dut" should check the correctness according to the input signals. The input signals are all in decimal format. It will be called by other codes later.
3. %s 
4. You have the information below to help you check the correctness of DUT:
"""%(SIGNALTEMP_PLACEHOLDER_1, STAGEPYGEN_SEQ_PYFORMAT)

STAGEPYGEN_SEQ_TXT2 = """
[IMPORTANT] %s
Optional: You can also use functions from numpy and scipy to help you check the correctness of DUT.
you can use binary (like 0b1011), hexadeciaml (like 0x1a) or normal number format in python for convenience. 
please only generate the python codes, no other words.
"""%(STAGEPYGEN_SEQ_PYFORMAT)

STAGEPYGEN_SEQ_TAIL = """
def SignalTxt_to_dictlist(txt:str):
    signals = []
    lines = txt.strip().split("\\n")
    for line in lines:
        signal = {}
        if line.startswith("[check]"):
            signal["check_en"] = True
            line = line[7:]
        else:
            signal["check_en"] = False
        line = line.strip().split(", ")
        for item in line:
            if "scenario" in item:
                item = item.split(": ")
                signal["scenario"] = item[1]
            else:
                item = item.split(" = ")
                key = item[0]
                value = item[1]
                if "x" not in value and "z" not in value:
                    signal[key] = int(value)
                else:
                    signal[key] = value 
        signals.append(signal)
    return signals
with open("TBout.txt", "r") as f:
    txt = f.read()
vectors_in = SignalTxt_to_dictlist(txt)
tb_pass = check_dut(vectors_in)
print(tb_pass)
"""
class Stage5_SEQ(BaseScriptStage):
    """stage 5 (SEQ): generate the pychecker that receive the signals from testbench and check the correctness of DUT"""
    def __init__(self, prob_data, response_stage1, response_stage3, **gptkwargs) -> None:
        super().__init__("stage_5", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage3 = response_stage3 # currently not used
        self.txt1 = STAGEPYGEN_SEQ_TXT1.replace(SIGNALTEMP_PLACEHOLDER_1, self.signal_dictlist_template(prob_data["header"]))
        self.txt2 = STAGEPYGEN_SEQ_TXT2
        self.pycode_tail = STAGEPYGEN_SEQ_TAIL

    def make_prompt(self):
        self.prompt = ""
        # introduction
        self.add_prompt_line(self.txt1)
        # problem description
        self.add_prompt_line("RTL circuit problem description:")
        self.add_prompt_line(self.prob_data["description"])
        # # specification
        # self.add_prompt_line("Checker specification:")
        # self.add_prompt_line(self.response_stage1)
        # python rules (optional)
        self.add_prompt_line("Here is the basic rules in python for the module. It is generated in previous stage. You can use it as a reference, but you should write your own python script. This is just for your better understanding:")
        self.add_prompt_line(self.response_stage3)
        # end
        self.add_prompt_line(self.txt2)

    def postprocessing(self):
        # python codes
        self.response = self.extract_code(self.response, "python")[-1]
        self.Pychecker_code_out = self.response + self.pycode_tail

    @staticmethod
    def signal_dictlist_template(header:str) -> str:
        """
        for the automatic generation of signals in testbench
        target: given the DUT header, generate the signal output template
        eg: if we have a DUT header like "module DUT(input a, b, c, output d, e);", the signal output template should be like "[{"check_en": 0, "scenario": 1, "a": 1, "b": 0, "c":1, "d": 0, "e": 0}, {"check_en": 1, "scenario": 1, "a": 0, "b": 0, "c":1, "d": 0, "e": 0}]"
        """
        signals_dictlist1 = Stage5_SEQ.header_to_dictlist(header)
        signals_dictlist2 = Stage5_SEQ.header_to_dictlist(header)
        signals_dictlist3 = Stage5_SEQ.header_to_dictlist(header, check_en=True)
        signals_dictlist = signals_dictlist1 + signals_dictlist2 + signals_dictlist3
        
        return str(signals_dictlist)
    
    @staticmethod
    def header_to_dictlist(header:str, value=1, scenario_idx=1, check_en = False) -> str:
        """
        - header: the header of DUT
        - template_scenario_idx: the scenario index in the template
        - signal_value: the value of the signal in the template
        - only: None: both input signal and output signal; "input": only input signal; "output": only output signal
        - from header to signals in txt
        - for the automatic generation of signals in testbench
        - target: given the DUT header, generate the signal output template
        - eg: if we have a DUT header like "module DUT(input clk, load, data, output q);", the signal output template should be like "$fdisplay(file, "scenario: %d, clk = %d, load = %d, data = %d, q = %d", scenario, clk, load, data, q);"
        """
        signals = Stage4_SEQ.extract_signals(header)
        dict_out = {}
        dict_list_out = [dict_out]
        dict_out["check_en"] = check_en
        dict_out["scenario"] = scenario_idx
        for signal in signals:
            dict_out[signal["name"]] = value
        return dict_list_out


