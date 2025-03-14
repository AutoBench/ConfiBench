"""
Description :   generate the RTL codes
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/7/31 23:28:04
LastEdited  :   2025/3/8 14:15:13
"""

import os
import LLM_call as llm
import loader_saver as ls
import sys
from data.probset import HDLBitsProbset
from LLM_call import llm_manager
import loader_saver as ls
from config import Config
import config
import LLM_call as gpt
import autoline as al
import iverilog_call as iv
import getopt
import sys
import confidence as cf
import analyze
from config import CFG_CUS_PATH
from autoline.TB4_eval import TaskTBeval
from loader_saver import autologger as logger


EXP_DIR = "saves_inEDA/TODAES/ConfiBench_4omini/NO3_20250306_235707"
REMOVE_DIR = False
VR_THRESHOLD = 0.8

def ablation1_no_multibench(old_results):
    my_config = Config()
    run_info_list = []
    for old_result in old_results:
        incomplete_running = False
        multibench_info = old_result["multibench_info"]
        # sort the multibench_info from big to small: 1. the number of "valid_ratio" 2. if the same, the number of "iter_id"
        multibench_info = sorted(multibench_info, key=lambda x: (x["valid_ratio"], x["iter_id"]), reverse=True)
        single_info = multibench_info[0]

        task_id = old_result["task_id"]
        working_dir = os.path.join(my_config.save.root, "Ablation1_no_multibench", task_id)
        TB_gen = single_info["TB_code_v"]
        TB_golden = old_result["testbench"]
        DUT_golden = old_result["module_code"]
        DUT_mutant_list = old_result["mutants"]
        DUT_gptgen_list = None
        pychecker_en = True
        pychecker_code = single_info["TB_code_py"]
        runfiles_save = False
        scen_mask = single_info["scen_mask"]
        multibench_en = False
        multibench_info_final = None

        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
        TBeval = TaskTBeval(task_id, working_dir, TB_gen, TB_golden, DUT_golden, DUT_mutant_list, DUT_gptgen_list, pychecker_en, pychecker_code, runfiles_save, scen_mask, multibench_en, multibench_info_final)

        try:
            TBeval.run()
        except Exception as e:
            logger.error(f"[{task_id}] - {e}")
            incomplete_running = True
            continue
        logger.info(f"[{task_id}] - TBeval finished")
        run_info = {
            "task_id": task_id,
            "ERROR(incomplete)": incomplete_running,
            "Eval0_pass": not incomplete_running
        }

        if TBeval is not None:
            if TBeval.Eval1_exist:
                run_info.update({"Eval1_pass": TBeval.Eval1_pass})
            if TBeval.Eval2_exist:
                run_info.update({
                    "Eval2_pass": TBeval.Eval2_pass,
                    "Eval2_ratio": "%d/%d"%(len(TBeval.Eval2_passed_mutant_idx), len(DUT_mutant_list)),
                    "Eval2_failed_mutant_idxes": TBeval.Eval2_failed_mutant_idx
                })
        run_info_list.append(run_info)

        # remove the working dir
        if REMOVE_DIR:
            os.system("rm -rf %s"%working_dir)

    analyzer = analyze.Analyzer(run_info_list)
    analyzer.out_txt += "\n########## Analyze of Chatbench_RunInfo ##########\n"
    analyzer.out_txt += "\nAblation1: No MultiBench (only use one masked testbench)\n"
    analyzer.out_txt += "\n#### pass numbers:\n"
    analyzer.out_txt += "Eval2 : %d\n" % analyzer.fullpass_num
    analyzer.out_txt += "Eval1 : %d\n" % analyzer.Eval1pass_num
    analyzer.out_txt += "Eval0 : %d\n" % analyzer.Eval0pass_num
    analyzer.out_txt += "total : %d " % analyzer.total_num

    return run_info_list, analyzer.out_txt
    
        

def ablation2_no_scenmask(old_results):
    my_config = Config()
    run_info_list = []
    for old_result in old_results:
        incomplete_running = False
        multibench_info = old_result["multibench_info"]
        # sort the multibench_info from big to small: 1. the number of "valid_ratio" 2. if the same, the number of "iter_id"
        multibench_info = sorted(multibench_info, key=lambda x: (x["valid_ratio"], x["iter_id"]), reverse=True)
        multibench_info_new = []
        valid_ratio_sum = 0.0
        for info in multibench_info:
            vr_now = info["valid_ratio"]
            valid_ratio_sum += vr_now
            info["scen_mask"] = [True for x in info["scen_mask"]] # disable the mask
            multibench_info_new.append(info)
            if valid_ratio_sum >= VR_THRESHOLD:
                break
        single_info = multibench_info[0]

        task_id = old_result["task_id"]
        working_dir = os.path.join(my_config.save.root, "Ablation2_no_scenmask", task_id)
        TB_gen = single_info["TB_code_v"] # disabled
        TB_golden = old_result["testbench"]
        DUT_golden = old_result["module_code"]
        DUT_mutant_list = old_result["mutants"]
        DUT_gptgen_list = None
        pychecker_en = True
        pychecker_code = single_info["TB_code_py"] # disabled
        runfiles_save = False
        scen_mask = single_info["scen_mask"] # disabled
        multibench_en = True
        multibench_info_final = multibench_info_new

        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
        TBeval = TaskTBeval(task_id, working_dir, TB_gen, TB_golden, DUT_golden, DUT_mutant_list, DUT_gptgen_list, pychecker_en, pychecker_code, runfiles_save, scen_mask, multibench_en, multibench_info_final)

        try:
            TBeval.run()
        except Exception as e:
            logger.error(f"[{task_id}] - {e}")
            incomplete_running = True
            continue
        logger.info(f"[{task_id}] - TBeval finished")
        run_info = {
            "task_id": task_id,
            "ERROR(incomplete)": incomplete_running,
            "Eval0_pass": not incomplete_running
        }
        if TBeval is not None:
            if TBeval.Eval1_exist:
                run_info.update({"Eval1_pass": TBeval.Eval1_pass})
            if TBeval.Eval2_exist:
                run_info.update({
                    "Eval2_pass": TBeval.Eval2_pass,
                    "Eval2_ratio": "%d/%d"%(len(TBeval.Eval2_passed_mutant_idx), len(DUT_mutant_list)),
                    "Eval2_failed_mutant_idxes": TBeval.Eval2_failed_mutant_idx
                })
        run_info_list.append(run_info)

        # remove the working dir
        if REMOVE_DIR:
            os.system("rm -rf %s"%working_dir)

    analyzer = analyze.Analyzer(run_info_list)
    analyzer.out_txt += "\n########## Analyze of Chatbench_RunInfo ##########\n"
    analyzer.out_txt += "\nAblation2: No Scenmask (set all to True)\n"
    analyzer.out_txt += "\n#### pass numbers:\n"
    analyzer.out_txt += "Eval2 : %d\n" % analyzer.fullpass_num
    analyzer.out_txt += "Eval1 : %d\n" % analyzer.Eval1pass_num
    analyzer.out_txt += "Eval0 : %d\n" % analyzer.Eval0pass_num
    analyzer.out_txt += "total : %d " % analyzer.total_num

    return run_info_list, analyzer.out_txt

def reset_params(old_results):
    my_config = Config()
    run_info_list = []
    confidencer = cf.Confidence(my_config.confibench)
    for old_result in old_results:
        incomplete_running = False
        multibench_info = old_result["multibench_info"]
        # sort the multibench_info from big to small: 1. the number of "valid_ratio" 2. if the same, the number of "iter_id"
        multibench_info = sorted(multibench_info, key=lambda x: (x["valid_ratio"], x["iter_id"]), reverse=True)
        multibench_info_new = []
        valid_ratio_sum = 0.0
        for info in multibench_info:
            confidence = confidencer.conf_gen(info["RSmatrix"], info["scen_num"])
            scen_mask = confidencer.conf_bool_gen(confidence)
            info["scen_mask"] = scen_mask
            # valid ratio = number of Trues / all scenarios
            info["valid_ratio"] = sum(scen_mask) / len(scen_mask)
        # reorder
        multibench_info = sorted(multibench_info, key=lambda x: (x["valid_ratio"], x["iter_id"]), reverse=True)
        for info in multibench_info:
            vr_now = info["valid_ratio"]
            valid_ratio_sum += vr_now
            multibench_info_new.append(info)
            if valid_ratio_sum >= my_config.confibench.multibench.min_ratio:
                break

        single_info = multibench_info[0]
        multibench_info = multibench_info_new

        task_id = old_result["task_id"]
        working_dir = os.path.join(my_config.save.root, task_id)
        TB_gen = single_info["TB_code_v"] # disabled
        TB_golden = old_result["testbench"]
        DUT_golden = old_result["module_code"]
        DUT_mutant_list = old_result["mutants"]
        DUT_gptgen_list = None
        pychecker_en = True
        pychecker_code = single_info["TB_code_py"] # disabled
        runfiles_save = False
        scen_mask = single_info["scen_mask"] # disabled
        multibench_en = True
        multibench_info_final = multibench_info_new

        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
        TBeval = TaskTBeval(task_id, working_dir, TB_gen, TB_golden, DUT_golden, DUT_mutant_list, DUT_gptgen_list, pychecker_en, pychecker_code, runfiles_save, scen_mask, multibench_en, multibench_info_final)

        try:
            TBeval.run()
        except Exception as e:
            logger.error(f"[{task_id}] - {e}")
            incomplete_running = True
            continue
        logger.info(f"[{task_id}] - TBeval finished")
        run_info = {
            "task_id": task_id,
            "ERROR(incomplete)": incomplete_running,
            "Eval0_pass": not incomplete_running
        }
        if TBeval is not None:
            if TBeval.Eval1_exist:
                run_info.update({"Eval1_pass": TBeval.Eval1_pass})
            if TBeval.Eval2_exist:
                run_info.update({
                    "Eval2_pass": TBeval.Eval2_pass,
                    "Eval2_ratio": "%d/%d"%(len(TBeval.Eval2_passed_mutant_idx), len(DUT_mutant_list)),
                    "Eval2_failed_mutant_idxes": TBeval.Eval2_failed_mutant_idx
                })
        run_info_list.append(run_info)

        # remove the working dir
        if REMOVE_DIR:
            os.system("rm -rf %s"%working_dir)

    analyzer = analyze.Analyzer(run_info_list)
    analyzer.out_txt += "\n########## Analyze of Chatbench_RunInfo ##########\n"
    analyzer.out_txt += "\nReset paras\n"
    analyzer.out_txt += f"K = {my_config.confibench.conf_bool.e_rank_super.K}\n"
    analyzer.out_txt += f"threshold = {my_config.confibench.conf_bool.e_rank_super.threshold}\n"
    analyzer.out_txt += f"min valid ratio = {my_config.confibench.multibench.min_ratio}\n"
    analyzer.out_txt += "\n\n#### pass numbers:\n"
    analyzer.out_txt += "Eval2 : %d\n" % analyzer.fullpass_num
    analyzer.out_txt += "Eval1 : %d\n" % analyzer.Eval1pass_num
    analyzer.out_txt += "Eval0 : %d\n" % analyzer.Eval0pass_num
    analyzer.out_txt += "total : %d " % analyzer.total_num
        
    return run_info_list, analyzer.out_txt

def analyze_org(old_results):
    analyzer = analyze.Analyzer(old_results)
    analyzer.out_txt += "\n########## Analyze of Chatbench_RunInfo ##########\n"
    analyzer.out_txt += "\nThis is original\n"
    analyzer.out_txt += "\n\n#### pass numbers:\n"
    analyzer.out_txt += "Eval2 : %d\n" % analyzer.fullpass_num
    analyzer.out_txt += "Eval1 : %d\n" % analyzer.Eval1pass_num
    analyzer.out_txt += "Eval0 : %d\n" % analyzer.Eval0pass_num
    analyzer.out_txt += "total : %d " % analyzer.total_num
    return analyzer.out_txt

if __name__ == "__main__":
    init_config = Config(CFG_CUS_PATH)
    logger = ls.AutoLogger() # initialize the autologger
    logger.info("all configurations are loaded")
    # assemble the results
    old_results = []
    taskdirs = os.listdir(EXP_DIR)    
    for taskdir in taskdirs:
        taskdir_path = os.path.join(EXP_DIR, taskdir)
        if not os.path.isdir(taskdir_path):
            continue
        result_data = ls.load_json_dict(os.path.join(taskdir_path, "data.json"))
        old_results.append(result_data)
        
    run_info_list_ablation1, text_ablation1 = ablation1_no_multibench(old_results)
    ls.save_dict_json_form(run_info_list_ablation1, os.path.join(init_config.save.root, "ablation1.json"))
    
    run_info_list_ablation2, text_ablation2 = ablation2_no_scenmask(old_results)
    ls.save_dict_json_form(run_info_list_ablation2, os.path.join(init_config.save.root, "ablation2.json"))

    analyzer_old = analyze.Analyzer(old_results)
    analyze_org(old_results)
    logger.info(analyzer_old.out_txt)
    logger.info("----------------------\n\n")

    logger.info(text_ablation1)

    logger.info("----------------------\n\n")
    logger.info(text_ablation2)
    