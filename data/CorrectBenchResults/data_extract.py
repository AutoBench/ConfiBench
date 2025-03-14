"""
Description :   This file is used to extract more information from the CorrectBenchResults dataset. incl.: Eval1_scen_data and more in the future.
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2025/1/23 04:53:13
LastEdited  :   2025/1/23 17:20:04
"""

import sys
if __name__ == "__main__":
    sys.path.append(".")
import json
import config
from loader_saver import AutoLogger
from config import Config
import os
from autoline.TB3_funccheck import TaskTBcheck
import json
from data.probset import HDLBitsProbset


ORIG_RESULT_PATH = "data/CorrectBenchResults/run_info_and_codes.jsonl"
HDLBITS_DATA_PATH = "data/HDLBits/HDLBits_data.jsonl"

class Eval1ScenDataGen:
    """
    ## Eval1_scen_data structure: dict, element is a list with lenth = scenario_num
    - RTL correctness: all 1s.
    - TB prediction: list of 1 or 0
    - TB correctness: list of 1 or 0, TB correctness = RTL_correctness XNOR TB_prediction
    """
    def __init__(self, save_compiling_infos = False):
        self.save_compiling_infos = save_compiling_infos
        pass

    def add_scen_data(self, orig_result: dict, orig_data: dict, code_running_dir:str = "_temp"):
        scenario_num = orig_result["scenario_num"]
        orig_result["Eval1_scen_data"] = {}
        scenario_num = orig_result["scenario_num"]
        TB_prediction = TB_prediction_gen(orig_result["tb_v_driver"], orig_result["tb_py_checker"], orig_data["module_code"], scenario_num, code_running_dir, save_en = self.save_compiling_infos)
        if TB_prediction is None:
            orig_result["Eval1_scen_data"]["RTL_correctness"] = None
            orig_result["Eval1_scen_data"]["TB_prediction"] = None
            orig_result["Eval1_scen_data"]["TB_correctness"] = None
            return orig_result
        RTL_correctness = [1] * scenario_num
        TB_correctness = [1 if RTL_correctness[i] == TB_prediction[i] else 0 for i in range(scenario_num)]
        orig_result["Eval1_scen_data"]["RTL_correctness"] = RTL_correctness
        orig_result["Eval1_scen_data"]["TB_prediction"] = TB_prediction
        orig_result["Eval1_scen_data"]["TB_correctness"] = TB_correctness
        return orig_result

def TB_prediction_gen(tb_v_driver, tb_py_checker, rtl, scenario_num, run_dir, save_en = False):
    try:
        if not os.path.exists(run_dir):
            os.makedirs(run_dir)
        failed_scenarios = TaskTBcheck.run_testbench(run_dir, tb_v_driver, rtl, tb_py_checker, save_en=save_en)
        correctness = [1] * scenario_num
        for i in failed_scenarios:
            correctness[i-1] = 0
        if not save_en:
            os.system("rm -rf " + run_dir)
        return correctness
    except Exception as e:
        logger.warning(f"TB running error: {e}; the result will be set to NONE.")
        return None


# run this file from the root directory of the project
if __name__ == "__main__":
    SAVE_COMPILING_INFOS = False
    # config
    my_config = Config(config.CFG_CUS_PATH)
    logger = AutoLogger()
    eval1_scen_data_gen = Eval1ScenDataGen(save_compiling_infos=SAVE_COMPILING_INFOS)
    result_id = 1
    probset = HDLBitsProbset(HDLBITS_DATA_PATH)
    new_result_path = ORIG_RESULT_PATH.replace(".jsonl", "_new.jsonl")
    with open(new_result_path, "w") as f:
        pass
    with open(ORIG_RESULT_PATH, "r") as f:
        for line in f:
            logger.info(f"Processing result {result_id}")
            cur_result = json.loads(line)
            cur_result_id = str(cur_result["result_id"]) + "_" + cur_result["task_id"] 
            cur_data = probset.find_data_by_id(cur_result["task_id"])
            new_data = eval1_scen_data_gen.add_scen_data(cur_result, cur_data, os.path.join(my_config.save.root, cur_result_id, "_code_running"))
            if not SAVE_COMPILING_INFOS:
                os.system("rm -rf " + os.path.join(my_config.save.root, cur_result_id))
            with open(new_result_path, "a") as f:
                json.dump(new_data, f)
                f.write("\n")
            logger.info(f"Finished processing result {result_id}")
            result_id += 1
        logger.info("All results are processed.")