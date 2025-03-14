"""
Description :   original txt script: config/templates/script_template/DUT_stage_template_0306.txt
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/3/22 13:02:22
LastEdited  :   2024/7/24 19:58:03
"""

from ..base_script import BaseScript, BaseScriptStage
from . import script_RTLchecker0306 as RTLchecker0306 
import json

PLACE_HOLDER_1 = "/* PLACE HOLDER ONE */"
PLACE_HOLDER_2 = "/* PLACE HOLDER TWO */"

class WF_RTLmulticheckers(BaseScript):
    """
    stages: stage1, stage2, stage3, stage3b, stage4
    check: check "scenario list"(stage2) in stage 4
    """
    def __init__(self, prob_data:dict, task_dir:str, config:object):
        super().__init__(prob_data, task_dir, config)
        self.max_check_iter = self.config.autoline.checklist.max

    def make_and_run_stages(self):
        # stage1
        self.stage1 = RTLchecker0306.Stage1(self.prob_data, **self.gptkwargs)
        self.stage_operation(self.stage1)
        # stage2
        # if self.stage1.spec_dict.get("circuit type", "CMB") == "SEQ":
        #     print("SEQ")
        #     self.stage2 = Stage2SEQ(self.prob_data, self.stage1.response, **self.gptkwargs)
        # else:
        #     print("CMB")
        #     self.stage2 = Stage2CMB(self.prob_data, self.stage1.response, **self.gptkwargs)
        self.stage2 = Stage2SEQ(self.prob_data, self.stage1.response, **self.gptkwargs)
        self.stage_operation(self.stage2)
        # stage3
        self.stage3 = Stage3(self.prob_data, self.stage1.response, self.stage2.response, **self.gptkwargs)
        self.stage_operation(self.stage3)
        # stage3b
        self.stage3b = Stage3b(self.prob_data, self.stage2.response, self.stage3.scenario_py_codes, **self.gptkwargs)
        self.stage_operation(self.stage3b)
        # stage4
        self.stage4 = Stage4(self.prob_data, self.stage1.response, self.stage2.response, self.stage3b.scenario_tb_codes, **self.gptkwargs)
        self.stage_operation(self.stage4)
        # stagechecklist
        self.stagecheck = StageChecklist(self.TB_code, self.stage2.response, self.max_check_iter, **self.gptkwargs)
        self.stage_operation(self.stagecheck)
        # add stage3b's golden DUT to the end of the final TB code

    def make_and_run_reboot_stages(self, reboot_dir):
        # stage4
        stage4_reboot = Stage4(self.prob_data, self.stage1.response, self.stage2.response, self.stage3b.scenario_tb_codes, **self.gptkwargs)
        self.stage_operation(stage4_reboot, conversation_dir=reboot_dir, reboot_en=True)
        # stagechecklist
        stagecheck_reboot = StageChecklist(self.TB_code, self.stage2.response, self.max_check_iter, **self.gptkwargs)
        self.stage_operation(stagecheck_reboot, conversation_dir=reboot_dir, reboot_en=True)

    def postprocessing(self):
        # the self.TB_code is just the middle part of testbench, now we need to add the initial part and the end part.
        initial_part_testbench = self.stage4.provided_codes.replace("endmodule", "")
        # add "    " to each line of the TB code
        self.TB_code = "    " + self.TB_code.replace("\n", "\n    ")
        self.TB_code = initial_part_testbench + self.TB_code + "\nendmodule\n"
        scenarios_dict = json.loads(self.stage2.response)
        all_scenario_tb_codes_in_one_str = "\n".join([self.stage3b.scenario_tb_codes["scenario %d" % (i+1)] for i in range(len(scenarios_dict.keys()))])
        self.TB_code += "\n" + all_scenario_tb_codes_in_one_str

Stage2CMB = RTLchecker0306.Stage2

STAGE2_TXT1="""1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The infomation we have is the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". Our target is to generate the verilog testbench for the DUT. This testbench can check if the DUT in verilog satisfies all technical requirements of the problem description.
2. you are in section 2. in this section, please give me the test scenarios. each scenario should be a simplified subset of input stimulus. For example. for a 16*16 multiplier, one possible scenario is one input equal to 0. you only need to describe the stimulus character in each test scenarios. If time is important, please inform the clock cycle information. we will use the stimulus description to generate the test vectors and send them to DUT. you must not tell the expected results even though you know that. 
3. your information is:"""
STAGE2_TXT2="""

Instruction: Each scenario should be a simplified subset of input stimulus. For example. for a 16*16 multiplier, one possible scenario is one input equal to 0. you only need to describe the stimulus character in each test scenarios. If time is important, please inform the clock cycle information. we will use the stimulus description to generate the test vectors and send them to DUT. you must not tell the expected results even though you know that. Your scenarios should not be more than 10. You should avoid that one scenario only contains one test case. Your scenarios should cover the most important or special cases. For example, for a 16*16 multiplier, one possible scenario is one input equal to 0. 

your response must be in JSON form. example:
{
  "scenario 1": "...", # each content is a string
  "scenario 2": "...",
  "scenario 3": "...",
  ...
}"""
class Stage2SEQ(BaseScriptStage):
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


STAGE3_TXT1="""1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The infomation we have is the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". Our target is to generate the verilog testbench for the DUT. This testbench can check if the DUT in verilog satisfies all technical requirements of the problem description.
2. you are in section 3. in this section, we already have the test scenario. please give me a python rule of the expected DUT. Attention, you code will only work under this test scenario so please consider the test scenario and give me the simplest rule under this scenario. (For convenience, you can use binary or hexadecimal format in python, i.e. 0b0010 and 0x1a). Later we will use these ideal rules to generate expected values to check the DUT's output under THIS SCENARIO. Your code don't need to fully simulate the DUT, just simulate the expected output under this limited scenario.
3. your information is:"""

class Stage3(BaseScriptStage):
    def __init__(self, prob_data, response_stage1, response_stage2, **gptkwargs) -> None:
        super().__init__("stage_3", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage2 = response_stage2
        self.txt1 = STAGE3_TXT1
        self.scenario_idx = 0
        self.scenario_dict = json.loads(response_stage2)
        self.scenario_len = len(self.scenario_dict.keys())
        self.scenario_py_codes = {}

    def run(self):
        while self.scenario_idx < self.scenario_len:
            self.scenario_idx += 1
            self.make_prompt()
            self.call_gpt()
            self.postprocessing()

    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line(self.txt1)
        # problem description
        self.add_prompt_line("RTL circuit problem description:")
        self.add_prompt_line(self.prob_data["description"])
        # # specification
        # self.add_prompt_line("RTL testbench specification:")
        # self.add_prompt_line(self.response_stage1)
        # DUT header
        self.add_prompt_line("DUT header:")
        self.add_prompt_line(self.prob_data["header"])
        # test scenarios
        self.add_prompt_line("test scenario: (please note the test vectors below, it will help you determine the input parameters of the rules. Your code don't need to fully simulate the function of DUT, just simulate the imperfect DUT under this limited scenario.)")
        self.add_prompt_line(self.scenario + ": " + self.scenario_dict[self.scenario])
        # end
        self.add_prompt_line("your response should only contain python code. Your code don't need to fully simulate the DUT, just simulate the expected output under this limited scenario.")

    def postprocessing(self):
        # extract python codes; codes may be more than one
        python_codes = self.extract_code(self.response, "python")
        response = ""
        for python_code in python_codes:
            response += python_code + "\n"
        self.scenario_py_codes[self.scenario] = response
        
    @property
    def scenario(self):
        return "scenario %d" % (self.scenario_idx)

STAGE3B_TXT1="""1. background: Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The infomation we have is the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". Our target is to generate the verilog testbench for the DUT. This testbench can check if the DUT in verilog satisfies all technical requirements of the problem description.
2. Task: you are in section 3. in this section, please give me the golden RTL code that fullfill the description under the corresponding scenario. This golden RTL code should have the same input and output ports as module header. The name of the module is "golden_RTL_%s". The module will be the reference module under "test scenario_%s" in the final testbench. The final testbench will compare the golden RTL's output signals with DUT's output signals under "test scenario_%s". If the same in all cases, the test passes. Your current task is to generate the golden_RTL_%s module.
3. Prior Knowledge: We already have the core rules expressed in python. You can use this infomation to help you design your golden RTL. You can use high level syntax and unsynthesizable syntax. Your golden module name is "golden_RTL_%s" and ports are the same as DUT's ports.
4. your information is:"""%(PLACE_HOLDER_1, PLACE_HOLDER_1, PLACE_HOLDER_1, PLACE_HOLDER_1, PLACE_HOLDER_1)
class Stage3b(BaseScriptStage):
    def __init__(self, prob_data, response_stage2, scenario_py_codes, **gptkwargs) -> None:
        super().__init__("stage_3b", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage2 = response_stage2
        self.scenario_idx = 0
        self.scenario_dict = json.loads(response_stage2)
        self.scenario_len = len(self.scenario_dict.keys())
        self.scenario_py_codes = scenario_py_codes
        self.scenario_tb_codes = {}

    def run(self):
        while self.scenario_idx < self.scenario_len:
            self.scenario_idx += 1
            self.make_prompt()
            self.call_gpt()
            self.postprocessing()

    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line(self.txt1)
        # problem description
        self.add_prompt_line("RTL circuit problem description:")
        self.add_prompt_line(self.prob_data["description"])
        # # specification
        # self.add_prompt_line("RTL testbench specification:")
        # self.add_prompt_line(self.response_stage1)
        # scenario
        self.add_prompt_line("you are in test %s. Its content is:" % (self.scenario))
        self.add_prompt_line(self.scenario_dict[self.scenario])
        # DUT header
        self.add_prompt_line("DUT header:")
        self.add_prompt_line(self.prob_data["header"])
        # rules
        self.add_prompt_line("IMPORTANT: THE RULES OF IDEAL DUT:")
        self.add_prompt_line(self.scenario_py_codes[self.scenario])
        # end
        self.add_prompt_line("please generate the golden module code. please only generate the verilog codes, no other words.")

    def postprocessing(self):
        # verilog codes
        self.response = self.extract_code(self.response, "verilog")[-1]
        self.scenario_tb_codes[self.scenario] = self.response

    @property
    def txt1(self):
        return STAGE3B_TXT1.replace(PLACE_HOLDER_1, str(self.scenario_idx))
    
    @property
    def scenario(self):
        return "scenario %d" % (self.scenario_idx)
    

STAGE4_TXT1="""1. Your task is to write a verilog testbench for an verilog RTL module code (we call it as "DUT", device under test). The infomation we have is 
- 1.1. the problem description that guides student to write the RTL code (DUT) and the header of the "DUT". 
- 1.2. the module header.
- 1.3. the technical specification of testbench
- 1.4. test scenarios which determines value and sequential information of test vectors
- 1.5. the golden RTL codes in verilog. They are corresponding to scenarios. In testbench, under each scenario, you should compare the signals from DUT with the corresponding golden RTL. If scenario 1, use golden_RTL_1. If not the same, then this DUT fails in the test.
Our target is to generate the verilog testbench for the DUT. This testbench can check if the DUT in verilog satisfies all technical requirements from the problem description.
2. you are in section 4. in this section, you will be provided with test scenarios and their corresponding golden RTLs. please highly based on these information to generate the testbench. The beginning of the testbench is already provided. You should complete the testbench. The part to be comlpemented is about testing the DUT under scenarios. 
3. There is a reg signal "error". It is "0" at the beginning. In each scenario, if test fails, the error should become "1" permanently and testbench should print like "scenario ... failed, got ..., expected ...". At the end of the test, if the "error" is still "0", testbench should print "All test cases passed!". This is very important!
4. In the scenarios testing part, do not directly write the value of expected value, but generate expected value from golden RTL. Please using the corresponding golden RTL to generate the expected value. for example, in scenario 1, you should compare DUT with golden RTL 1, in scenario 2, you should compare DUT with golden RTL 2, and so on.
5. the input and output ports of golden RTLs are the same as DUT's ports. For example, under scenario 1, its golden RTL's header should be:
%s
6. your information is:"""%(PLACE_HOLDER_1)
class Stage4(BaseScriptStage):
    def __init__(self, prob_data, response_stage1, response_stage2, scenario_tb_codes, **gptkwargs) -> None:
        super().__init__("stage_4", **gptkwargs)
        self.prob_data = prob_data
        self.response_stage1 = response_stage1
        self.response_stage2 = response_stage2
        self.scenarios_dict = json.loads(response_stage2)
        self.scenario_tb_codes = scenario_tb_codes
        self.txt1 = STAGE4_TXT1.replace(PLACE_HOLDER_1, self.prob_data["header"].replace("top_module", "golden_RTL_1"))
        self.TB_code_out = ""
        self.all_golden_RTL_headers_in_a_str = "\n".join([self.prob_data["header"].replace("top_module", "golden_RTL_%d" % (i+1)) for i in range(len(self.scenarios_dict.keys()))])
        self.testbench_template = testbench_template(self.prob_data["header"])
        self.provided_codes = self.testbench_template.gen_template(len(self.scenarios_dict.keys()))

    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line(self.txt1)
        # # problem description
        # self.add_prompt_line("RTL circuit problem description:")
        # self.add_prompt_line(self.prob_data["description"])
        # specification
        self.add_prompt_line("RTL testbench specification:")
        self.add_prompt_line(self.response_stage1)
        # DUT header
        # self.add_prompt_line("DUT header:")
        # self.add_prompt_line(self.prob_data["header"])
        # rules
        self.add_prompt_line("IMPORTANT - test scenario:")
        self.add_prompt_line(self.response_stage2)
        self.add_prompt_line("under each scenario, please use golden RTL with the same index to check the DUT's output signals. for example, in scenario 1, you use golden_RTL_1")
        # golden RTL headers
        # self.add_prompt_line("IMPORTANT - golden RTL headers: (please instantiate them in your testbench.)")
        # self.add_prompt_line(self.all_golden_RTL_headers_in_a_str)
        self.add_prompt_line("IMPORTANT - the provided codes:")
        self.add_prompt_line(self.provided_codes)
        # end
        self.add_prompt_line("please complement the testbench code accoding to the test scenarios. please only generate the missed verilog codes, no other words. You generated codes should exclude the already provided codes.")

    def postprocessing(self):
        # verilog codes
        self.response = self.extract_code(self.response, "verilog")[-1]
        self.TB_code_out = self.response # this is only the copmlementation part, not the full testbench
        # all_scenario_tb_codes_in_one_str = "\n".join([self.scenario_tb_codes["scenario %d" % (i+1)] for i in range(len(self.scenarios_dict.keys()))])
        # self.TB_code_out = self.response + "\n" + all_scenario_tb_codes_in_one_str
        # will be put after the checklist


TMEPLATE_TO_BE_CONTINUE = """
//now you should complement the code. testbench will test the DUT under scenarios using the corresponding golden_RTL_scenario_x.
//your code should rely on the provided scenarios list
"""
class testbench_template:
    def __init__(self, header) -> None:
        self.header = header
        self.signals = self.extract_signals()

    def gen_template(self, golden_RTL_num=2):
        """
        - testbench structure
        1. initial part
        2. instantiate signals: DUT's signals 
        3. instantiate DUT
        3. instantiate golden modules and their signals
        """
        initial_str = """`timescale 1ns / 1ps\nmodule testbench;\n"""
        testbench_str = ""
        testbench_str += "reg error = 0;\n"
        testbench_str += self.initial_signals(self.signals) + "\n"
        testbench_str += "// DUT instantiation\n"
        testbench_str += self.instantiate_module_by_signals("top_module", "DUT", self.signals) + "\n"
        for idx in range(1, golden_RTL_num+1):
            testbench_str += self.instantiate_goldenmodule_by_signals(idx, self.signals) + "\n"
        testbench_str += TMEPLATE_TO_BE_CONTINUE
        # add "    " for each line of testbench str
        testbench_str = "    " + testbench_str.replace("\n", "\n    ")
        end_str = "\nendmodule"
        return initial_str + testbench_str + end_str
    
    def extract_signals(self):
        def get_width_ifhave(signal):
            if len(signal) > 2 and "[" in signal[-2] and "]" in signal[-2]:
                # remove other parts except the [x:x]
                width = signal[-2]
                width = width.split("[")[1].split("]")[0]
                width = "[" + width + "]"
                return width
            else:
                return ""
        signals = self.header.split("(")[1].split(")")[0].split(",")
        signals = [signal.strip().split(" ") for signal in signals]
        signals = [{"name": signal[-1], "width": get_width_ifhave(signal), "type": signal[0]} for signal in signals]
        return signals
    
    def instantiate_DUT(self):
        return self.instantiate_module_by_signals("top_module", "DUT", self.signals) + "\n"

    @staticmethod
    def instantiate_module_by_signals(module_name, instantiate_name, signals):
        """
        - this function is used to instantiate a module by signals
        - the signals should be like [{"name": "a", "width": "[3:0]", "type": "input"}, ...]
        """
        instantiate_str = f"{module_name} {instantiate_name} (\n"
        for signal in signals:
            if signal["width"]:
                instantiate_str += f"\t.{signal['name']}({signal['name']}),\n"
            else:
                instantiate_str += f"\t.{signal['name']}({signal['name']}),\n"
        instantiate_str = instantiate_str[:-2] + "\n);"
        return instantiate_str
    
    @staticmethod
    def instantiate_goldenmodule_by_signals(index, signals):
        instantiate_str = f"golden_RTL_{index} golden_RTL_for_scenario_{index} (\n"
        for signal in signals:
            if signal["type"] == "output":
                instantiate_str += f"\t.{signal['name']}({signal['name']}_golden_{index}),\n"
                instantiate_str = f"wire {signal['width']} {signal['name']}_golden_{index};\n" + instantiate_str
            else:
                instantiate_str += f"\t.{signal['name']}({signal['name']}),\n"
        instantiate_str = instantiate_str[:-2] + "\n);"
        return instantiate_str
    
    @staticmethod
    def initial_signals(signals):
        """
        - this function is used to initialize signals
        """
        initial_str = ""
        for signal in signals:
            if signal["type"] == "input":
                initial_str += f"reg {signal['width']} {signal['name']};\n"
            else:
                initial_str += f"wire {signal['width']} {signal['name']};\n"
        return initial_str
    

class StageChecklist(BaseScriptStage):
    def __init__(self, TB_code:str, checklist_str:str, max_iter:int, **gptkwargs) -> None:
        super().__init__("stage_checklist", **gptkwargs)
        self.checklist = checklist_str
        self.max_iter = max_iter
        self.TB_code_out = TB_code
        self.exit = False
        self.iter = 0

    def make_prompt(self):
        self.prompt = ""
        self.add_prompt_line("please check the if the partial testbench code contains all the scenarios in the checklist:")
        self.add_prompt_line("testbench code here...\n")
        self.add_prompt_line(self.TB_code_out + "\n")
        self.add_prompt_line("please check the if the testbench code above contains all the scenarios in the checklist:")
        self.add_prompt_line(self.checklist)
        self.add_prompt_line("please reply 'YES' if all the items are included. If some of the items are missed in testbench, please add the missing items and reply the modified code (full code). Your attention should focus on the scenarios.")
        self.add_prompt_line("VERY IMPORTANT: please ONLY reply 'YES' or the full code modified. NEVER remove other irrelevant codes!!!")
    
    def postprocessing(self):
        self.iter += 1
        if "YES" in self.response:
            self.exit = True
        else:
            self.TB_code_out = self.extract_code(self.response, "verilog")[-1]

    def run(self):
        while (not self.exit) and (self.iter < self.max_iter):
            self.make_prompt()
            self.call_gpt()
            self.postprocessing()