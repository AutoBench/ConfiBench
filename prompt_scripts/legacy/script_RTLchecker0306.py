"""
Description :   original txt script: config/templates/script_template/DUT_stage_template_0306.txt
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/3/22 13:02:22
LastEdited  :   2024/7/24 19:53:29
"""

from ..base_script import BaseScript, BaseScriptStage
import json

class WF_RTLchecker0306(BaseScript):
    """
    stages: stage1, stage2, stage3, stage3b, stage4
    check: check "scenario list"(stage2) in stage 4
    """
    def __init__(self, prob_data:dict, task_dir:str, config:object):
        super().__init__(prob_data, task_dir, config)
        self.max_check_iter = self.config.autoline.checklist.max

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
        # stage3b
        self.stage3b = Stage3b(self.prob_data, self.stage1.response, self.stage3.response, **self.gptkwargs)
        self.stage_operation(self.stage3b)
        # stage4
        self.stage4 = Stage4(self.prob_data, self.stage1.response, self.stage2.response, self.stage3b.response, **self.gptkwargs)
        self.stage_operation(self.stage4)
        # stagechecklist
        self.stagecheck = StageChecklist(self.TB_code, self.stage2.response, self.max_check_iter, **self.gptkwargs)
        self.stage_operation(self.stagecheck)
        # add stage3b's golden DUT to the end of the final TB code
        # self.TB_code += "\n" + stage3b.response #now in stage 4

    def make_and_run_reboot_stages(self, debug_dir):
        # stage4
        stage4_reboot = Stage4(self.prob_data, self.stage1.response, self.stage2.response, self.stage3b.response, **self.gptkwargs)
        self.stage_operation(stage4_reboot, debug_dir, reboot_en=True)
        # stagechecklist
        stagecheck = StageChecklist(self.TB_code, self.stage2.response, self.max_check_iter, **self.gptkwargs)
        self.stage_operation(stagecheck, debug_dir, reboot_en=True)
        

STAGE1_TXT1="""1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The infomation we have is the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". Our target is to generate the verilog testbench for the DUT. This testbench can check if the DUT in verilog satisfies all technical requirements of the problem description.
2. You are in the first stage. In this stage, please summarize the technical details of the DUT and give me a technical specification of the testbench generation task, so we can use it to design its corresponding testbench.
3. The core of testbench is the testcases. It usually include two parts logically: the input signals to the DUT and the expected result signals from DUT. The testbench will send the input signals to DUT and check if the result signals are the same as the expected result signals. If they are the same, this means the DUT is passed. Otherwise the DUT fails.
4. Your technical specification should include these sections:
- section 1: specification of the DUT, including the module header of the RTL code. If table or other detailed data is provided in the original problem description, DO repeat them in your response. They are very important!!!
5. your response should be in the form of JSON.
6. below is the information including the problem description and the DUT header:"""
STAGE1_TXT2="""your response must be in JSON form. example:
{
  "circuit type": "...", # type: string. should be "CMB" for combinational circuit or "SEQ" for sequential circuit. you should only choose one from "CMB" and "SEQ".
  "important data": "...", # type: string. If no table, state transition or other direct data, leave this with ""
  "technical specifications": ["...", "...", ...] # each element of the list is one specification string, the starting of the string is its index 
}
"""
class Stage1(BaseScriptStage):
    def __init__(self, prob_data, **gptkwargs):
        gptkwargs["json_mode"] = True
        super().__init__("stage_1", **gptkwargs)
        self.prob_data = prob_data
        self.txt1 = STAGE1_TXT1
        self.txt2 = STAGE1_TXT2
    
    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line(self.txt1)
        # problem description
        self.add_prompt_line("RTL circuit problem description:")
        self.add_prompt_line(self.prob_data["description"])
        # DUT header
        self.add_prompt_line("DUT header:")
        self.add_prompt_line(self.prob_data["header"])
        # template
        self.add_prompt_line(self.txt2)

    # def postprocessing(self):
    #     self.spec_dict = json.loads(self.response)


STAGE2_TXT1="""1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The infomation we have is the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". Our target is to generate the verilog testbench for the DUT. This testbench can check if the DUT in verilog satisfies all technical requirements of the problem description.
2. you are in section 2. in this section, please give me the test scenarios. you only need to describe the stimulus in each test scenarios. If time is important, please inform the clock cycle information. we will use the stimulus description to generate the test vectors and send them to DUT. you must not tell the expected results even though you know that. 
3. your information is:"""
STAGE2_TXT2="""
you only need to describe the stimulus in each test scenarios. If time is important, please inform the clock cycle information. we will use the stimulus description to generate the test vectors and send them to DUT. you must not tell the expected results even though you know that. 

your response must be in JSON form. example:
{
  "scenario 1": "...", # each content is a string
  "scenario 2": "...",
  "scenario 3": "...",
  ...
}"""
class Stage2(BaseScriptStage):
    def __init__(self, prob_data, response_stage1, **gptkwargs) -> None:
        gptkwargs["json_mode"] = True
        super().__init__("stage_2", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.txt1 = STAGE2_TXT1
        self.txt2 = STAGE2_TXT2

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
        # template
        self.add_prompt_line(self.txt2)


STAGE3_TXT1="""1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The information we have is the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". Our target is to generate the verilog testbench for the DUT. This testbench can check if the DUT in verilog satisfies all technical requirements of the problem description.
2. you are in section 3; in this section, please give me the rules of an ideal DUT. you should give these rules in python. (For convenience, you can use binary or hexadecimal format in python, i.e. 0b0010 and 0x1a). Later we will use these ideal rules to generate expected values in each test scenario. currently you must only generate the rules. the input of these rules should be related to the test vectors from test scenario. the rule should give the expected values under test vectors. 
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

STAGE3B_TXT1="""1. background: Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The infomation we have is the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". Our target is to generate the verilog testbench for the DUT. This testbench can check if the DUT in verilog satisfies all technical requirements of the problem description.
2. Task: you are in section 3. in this section, please give me the golden RTL code that fullfill the description. This golden RTL code should have the same input and output ports as module header. The name of the module is "golden_DUT". The module will be the reference module in the final testbench. The final testbench will compare the golden RTL's output signals with DUT's output signals. If the same in all cases, the test passes. Your current task is to generate the golden RTL module.
3. Prior Knowledge: We already have the core rules expressed in python. You can use this infomation to help you design your golden RTL. You can use high level syntax and unsynthesizable syntax. Your golden module name is "golden_DUT" and ports are the same as DUT's ports.
4. your information is:"""
class Stage3b(BaseScriptStage):
    def __init__(self, prob_data, response_stage1, response_stage3, **gptkwargs) -> None:
        super().__init__("stage_3b", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage3 = response_stage3
        self.txt1 = STAGE3B_TXT1

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
        # rules
        self.add_prompt_line("IMPORTANT: THE RULES OF IDEAL DUT:")
        self.add_prompt_line(self.response_stage3)
        # end
        self.add_prompt_line("please generate the golden module code. please only generate the verilog codes, no other words.")

    def postprocessing(self):
        # verilog codes
        self.response = self.extract_code(self.response, "verilog")[-1]

STAGE4_TXT1="""1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The infomation we have is 
- 1.1. the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". 
- 1.2. the module header.
- 1.3. the technical specification of testbench
- 1.4. test scenarios which determines value and sequential information of test vectors
- 1.5. the golden RTL codes in verilog. In testbench you should compare the signals from golden RTL and DUT. If not the same, then this DUT fails in the test.
Our target is to generate the verilog testbench for the DUT. This testbench can check if the DUT in verilog satisfies all technical requirements from the problem description.
2. you are in section 4. in this section, you will be provided with test scenarios and golden DUT. please highly based on these information to generate the testbench.
3. There should be a reg "error". It is "0" at the beginning. In each scenario, if test fails, the error should become "1" permanently and testbench should print like "scenario ... failed, got ..., expected ...". At the end of the test, if the "error" is still "0", testbench should print "All test cases passed!". This is very important!
4. In the scenarios testing part, do not directly write the value of expected value, but generate expected value from golden RTL.
5. your information is:"""
class Stage4(BaseScriptStage):
    def __init__(self, prob_data, response_stage1, response_stage2, response_stage3b, **gptkwargs) -> None:
        super().__init__("stage_4", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage2 = response_stage2
        self.response_stage3b = response_stage3b
        self.txt1 = STAGE4_TXT1
        self.TB_code_out = ""

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
        # rules
        self.add_prompt_line("IMPORTANT - test scenario:")
        self.add_prompt_line(self.response_stage2)
        # rules
        self.add_prompt_line("IMPORTANT - golden RTL: (please instantiate it in your testbench. Your code should not contain the full code of golden RTL)")
        self.add_prompt_line(self.response_stage3b)
        # end
        self.add_prompt_line("please generate the golden module code. please only generate the verilog codes, no other words.")

    def postprocessing(self):
        # verilog codes
        self.response = self.extract_code(self.response, "verilog")[-1]
        self.TB_code_out = self.response + "\n" + self.response_stage3b


class StageChecklist(BaseScriptStage):
    def __init__(self, TB_code:str, checklist_str:str, max_iter:int, **gptkwargs) -> None:
        super().__init__("stage_checklist", **gptkwargs)
        self.checklist = checklist_str
        self.max_iter = max_iter
        self.TB_code_out = TB_code
        self.exit = False
        self.iter = 0
        self.TB_modified = False

    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line("please check the if the testbench code contains all the items in the checklist:")
        self.add_prompt_line("testbench code here...\n")
        self.add_prompt_line(self.TB_code_out + "\n")
        self.add_prompt_line("please check the if the testbench code above contains all the scenarios in the checklist:")
        self.add_prompt_line(self.checklist)
        self.add_prompt_line("please reply 'YES' if all the items are included. If some of the items are missed in testbench, please add the missing items and reply the modified testbench code (full code).")
        self.add_prompt_line("VERY IMPORTANT: please ONLY reply 'YES' or the full code modified. NEVER remove other irrelevant codes!!!")
    
    def postprocessing(self):
        self.iter += 1
        if "YES" in self.response:
            self.exit = True
        else:
            self.TB_modified = True
            self.TB_code_out = self.extract_code(self.response, "verilog")[-1]

    def run(self):
        self.TB_modified = False
        while (not self.exit) and (self.iter < self.max_iter):
            self.make_prompt()
            self.call_gpt()
            self.postprocessing()
            

########################################################################
def test():
    test_stage1 = Stage1(model = "gpt-3.5-turbo", gptkeypath = "gpt_key/gpt_key_0306.json")
    test_stage1.make_prompt()
    print(test_stage1.prompt)

