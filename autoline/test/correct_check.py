"""
Description :   corrector test and debug
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/8/3 14:17:11
LastEdited  :   2024/9/17 17:34:54
"""

import os
import loader_saver as ls
import json
import pandas as pd
from LLM_call import llm_manager
from data.probset import HDLBitsProbset
from autoline.TB3_funccheck import TaskTBcheck
from autoline.TB4_eval import TaskTBeval
from config import Config
from loader_saver import autologger as logger

LINES = [7, 49, 78, 201, 492, 539, 1237, 1401, 1451, 1469]
# the result index that has score between -1 and 0.5
# SCORE_RANGE_MINUS1_05 = [98, 148, 252, 273, 346, 393, 533, 614, 707, 780, 786, 806, 845, 1126, 1171, 1307, 1364, 1398, 1435, 1503]

# task: given a wrong testbench (but syntax correct), run corrector of TB3_funccheck, see if it can correct the testbench

def corrector_test(save_dir:str, probdata:dict, v_code:str, py_code:str, save_en:bool=True)->tuple[bool, bool, bool, float]:
    # will first use TBcheck.corrector to correct and then analyze the corrected testbench using TBEval 
    Eval0, Eval1, Eval2, Eval2_ratio = False, False, False, 0.0
    config = Config()
    root = save_dir
    tbcheck = TaskTBcheck(os.path.join(root, "TB3_check"), probdata["task_id"], probdata["description"], probdata["header"], v_code, py_code, probdata["llmgen_RTL"], correct_max=config.autoline.TBcheck.correct_max, discriminator_mode=config.autoline.TBcheck.discrim_mode, corrector_mode=config.autoline.TBcheck.correct_mode, runfiles_save=save_en, main_model=config.gpt.model)
    tbcheck.discriminate_TB()
    tbcheck.correct_TB()
    tbeval = TaskTBeval(probdata["task_id"], os.path.join(root, "TB4_eval"), tbcheck.TB_code_v, probdata["testbench"], probdata["module_code"], probdata["mutants"], pychecker_en=True, pychecker_code=tbcheck.TB_code_py, runfiles_save=save_en)
    try:
        tbeval.run()
    except Exception as e:
        Eval0, Eval1, Eval2, Eval2_ratio = False, False, False, 0.0
    else:
        Eval0, Eval1, Eval2 = True, tbeval.Eval1_pass, tbeval.Eval2_pass
        # , len(tbeval.Eval2_passed_mutant_idx)/len(tbeval.DUT_mutant_list)
        if hasattr(tbeval, "Eval2_passed_mutant_idx"):
            if isinstance(tbeval.Eval2_passed_mutant_idx, list):
                Eval2_ratio = len(tbeval.Eval2_passed_mutant_idx)/len(tbeval.DUT_mutant_list)

    return Eval0, Eval1, Eval2, Eval2_ratio

def run_corrector_test_with_abresults(abresults_path:str, probset:HDLBitsProbset, lines_mks:int|list[int], save_en:bool=True):
    lines_mks = [lines_mks] if isinstance(lines_mks, int) else lines_mks
    # from line mark to index (-1)
    lines_idx = [mk-1 for mk in lines_mks]
    df = pd.read_json(abresults_path, lines=True)
    config = Config()
    for line_idx in lines_idx:
        logger.info("")
        logger.info(f"[{line_idx+1}] begins")
        save_dir = os.path.join(config.save.root, str(line_idx+1))
        rslt_row = df.iloc[line_idx]
        rslt_row = rslt_row.where(pd.notnull(rslt_row), None)
        TB_under_correct_v = rslt_row["tb_v_driver"] 
        TB_under_correct_py = rslt_row["tb_py_checker"]
        # save the rslt_row to a json file as a record
        task_id = rslt_row["task_id"]
        probdata = probset.access_data_via_taskid(task_id)
        Eval0, Eval1, Eval2, Eval2_ratio = corrector_test(save_dir, probdata, TB_under_correct_v, TB_under_correct_py, save_en)
        ls.save_dict_json_form(rslt_row.to_dict(), os.path.join(save_dir, "old_result.json"))
        ls.save_dict_json_form(probdata, os.path.join(save_dir, "data.json"))
        if Eval2_ratio >= 0.8:
            logger.success(f"[{task_id}] - Eval0: {Eval0}, Eval1: {Eval1}, Eval2: {Eval2}, Eval2_ratio: {Eval2_ratio}")
        else:
            logger.failed(f"[{task_id}] - Eval0: {Eval0}, Eval1: {Eval1}, Eval2: {Eval2}, Eval2_ratio: {Eval2_ratio}")
    total_cost = llm_manager.cost_total
    logger.info(f"total cost: {total_cost}")

def find_eval1_failed_no_random(num:int, max_score:float=0.5, min_score:float=-1, max_ease:int=10, min_ease:int=0):
    # get a random number, range is from 0 to 1559 (int)
    import random
    output_idx = []
    score_list = []
    ease_list = []
    path_AutoBenchResults = "data/AutoBenchResults/run_info_and_codes.jsonl"
    path_HDLBits_data = "data/HDLBits/HDLBits_data.jsonl"
    path_HDLBits_data_rtllist = "data/HDLBits/HDLBits_data_RTL.jsonl"
    path_mutant_list = "data/HDLBits/HDLBits_data_mutants.jsonl"
    df = pd.read_json(path_AutoBenchResults, lines=True)
    while len(output_idx) < num:
        random_num = random.randint(0, 1559)
        score = df.iloc[random_num]["Eval_score"]
        score_condition = (score >= min_score) and (score <= max_score)
        ease_condition = df.iloc[random_num]["ease"] >= min_ease and df.iloc[random_num]["ease"] <= max_ease
        if score_condition and ease_condition:
            output_idx.append(random_num)
            score_list.append(float(score))
            ease_list.append(int(df.iloc[random_num]["ease"]))
    # reorder the list
    output_idx.sort()
    print(f"the output index is: {output_idx}")
    print(f"the score list is: {score_list}")
    print(f"the ease list is: {ease_list}")
    return output_idx

def main():

    path_AutoBenchResults = "data/AutoBenchResults/run_info_and_codes.jsonl"
    path_HDLBits_data = "data/HDLBits/HDLBits_data.jsonl"
    path_HDLBits_data_rtllist = "data/HDLBits/HDLBits_data_RTL.jsonl"
    path_mutant_list = "data/HDLBits/HDLBits_data_mutants.jsonl"

    my_config = Config("/home/ge45vuq/Projects/Chatbench/config/custom.yaml")
    ls.add_save_root_to(my_config)
    logger = ls.AutoLogger()
    probset = HDLBitsProbset(path_HDLBits_data, [path_HDLBits_data_rtllist, path_mutant_list])

    # lines = SCORE_RANGE_MINUS1_05[6:11]
    lines = LINES
    logger.info(f"begin, lines: {lines}")
    run_corrector_test_with_abresults(path_AutoBenchResults, probset, lines, save_en=True)
