"""
Description :   discriminator eval: evaluate the performance of the discriminator we used
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/8/1 17:35:58
LastEdited  :   2024/9/19 13:55:39
"""

import os
import loader_saver as ls
import json
import numpy as np
from data.probset import HDLBitsProbset
from autoline import TB3_funccheck
from config import Config
from LLM_call import llm_manager
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


CONFIG_PATH = "config/templates/config_templates/discrim.yaml"
MAX_ITER = 200
RTL_LIST_NUM_REDUCE_TO = 20
PROBSET_PATH = "data/HDLBits/HDLBits_data.jsonl"
AUTOBENCHRESULTS = "data/AutoBenchResults/run_info_and_codes.jsonl"
SAVE_NEG_TB_POS_DISC_PATTERN = False
SAVE_POS_TB_NEG_DISC_PATTERN = False
SAVE_NEG_TB_NEG_DISC_PATTERN = True

def main():
    # please change the discrim mode in config file, other paras are set in this file
    my_config = Config(CONFIG_PATH)
    logger = ls.AutoLogger()
    ls.add_save_root_to(my_config)
    save_root_dir = my_config.save.root
    task_dir = os.path.join(save_root_dir, "TB3_funccheck")
    # rtl_list_path = "data/HDLBits/HDLBits_data_RTL_4omini_50.jsonl"
    rtl_list_path = "data/HDLBits/HDLBits_data_RTL.jsonl"
    probset = HDLBitsProbset(PROBSET_PATH, [rtl_list_path])
    result_data = {"positive_TB_negative_DSC": 0, "positive_TB_positive_DSC": 0, "negative_TB_positive_DSC": 0, "negative_TB_negative_DSC": 0}
    # MAX_ITER = 1000
    i_reduced = 0
    for data in probset.data:
        if len(data["llmgen_RTL"]) > RTL_LIST_NUM_REDUCE_TO:
            i_reduced += 1
            data["llmgen_RTL"] = data["llmgen_RTL"][:RTL_LIST_NUM_REDUCE_TO]
    logger.info(f"reduced {i_reduced} RTL lists to {RTL_LIST_NUM_REDUCE_TO} in length")
    with open(AUTOBENCHRESULTS, "r") as f:
        idx = 0
        for line in f:
            idx += 1
            current_TB_info = json.loads(line)
            task_id = current_TB_info["task_id"]
            result_id = current_TB_info.get("result_id", "")
            logger.info(f"current result id: [{result_id}]")
            probdata = probset.access_data_via_taskid(task_id)
            task_tb3 = TB3_funccheck.TaskTBcheck(task_dir, task_id, probdata["description"], probdata["header"], current_TB_info["tb_v_driver"], current_TB_info["tb_py_checker"], probdata["llmgen_RTL"], discriminator_mode=my_config.autoline.TBcheck.discrim_mode, main_model=my_config.gpt.model)
            task_tb3.discriminate_TB(True)
            # get the result
            TB_correctness = (current_TB_info["Eval_score"] >= 0.8)
            DSC_correctness = task_tb3.tb_pass
            result_key = f"{'positive' if TB_correctness else 'negative'}_TB_{'positive' if DSC_correctness else 'negative'}_DSC"
            result_data[result_key] += 1
            # if idx >= 5:
            #     break
            if (idx % 20) == 0:
                result_print  = " current confusion matrix:\n"
                result_print += "                | positive_TB | negative_TB |\n"
                result_print += " positive_DSC   | %11d | %11d |\n" % (result_data["positive_TB_positive_DSC"], result_data["negative_TB_positive_DSC"])
                result_print += " negative_DSC   | %11d | %11d |\n" % (result_data["positive_TB_negative_DSC"], result_data["negative_TB_negative_DSC"])
                logger.info("\n"+result_print)
            if SAVE_NEG_TB_POS_DISC_PATTERN:
                if (not TB_correctness) and DSC_correctness:
                    save_path = os.path.join(save_root_dir, "negTB_posDSC", f"{result_id}_negTB_posDSC.png")
                    os.makedirs(os.path.join(save_root_dir, "negTB_posDSC"), exist_ok=True)
                    task_tb3.draw_scenario_matrix(task_tb3.scenario_matrix, task_id+f"[{result_id}]", save_path)
                    logger.failed(f"[{result_id}] TB neg but Disc pos, saved the scenario matrix to {save_path}")
            if SAVE_POS_TB_NEG_DISC_PATTERN:
                if TB_correctness and (not DSC_correctness):
                    save_path = os.path.join(save_root_dir, "posTB_negDSC", f"{result_id}_posTB_negDSC.png")
                    os.makedirs(os.path.join(save_root_dir, "posTB_negDSC"), exist_ok=True)
                    task_tb3.draw_scenario_matrix(task_tb3.scenario_matrix, task_id+f"[{result_id}]", save_path)
                    logger.failed(f"[{result_id}] TB pos but Disc neg, saved the scenario matrix to {save_path}")
            if SAVE_NEG_TB_NEG_DISC_PATTERN:
                if (not TB_correctness) and (not DSC_correctness):
                    save_path = os.path.join(save_root_dir, "negTB_negDSC", f"{result_id}_negTB_negDSC.png")
                    os.makedirs(os.path.join(save_root_dir, "negTB_negDSC"), exist_ok=True)
                    task_tb3.draw_scenario_matrix(task_tb3.scenario_matrix, task_id+f"[{result_id}]", save_path)
                    logger.failed(f"[{result_id}] TB neg and Disc neg, saved the scenario matrix to {save_path}")
            if idx >= MAX_ITER:
                break
    result_print  = " final confusion matrix:\n"
    result_print += "                | positive_TB | negative_TB |\n"
    result_print += " positive_DSC   | %11d | %11d |\n" % (result_data["positive_TB_positive_DSC"], result_data["negative_TB_positive_DSC"])
    result_print += " negative_DSC   | %11d | %11d |\n" % (result_data["positive_TB_negative_DSC"], result_data["negative_TB_negative_DSC"])
    logger.info("\n"+result_print)


def only_gen_matrix():
    # please change the discrim mode in config file, other paras are set in this file
    scen_dict_path = "data/AutoBenchResults/scen_dict.jsonl"
    # if path not exist, create; if the file is not empty, wipe it
    os.makedirs(os.path.dirname(scen_dict_path), exist_ok=True)
    with open(scen_dict_path, "w") as f:
        pass
    my_config = Config(CONFIG_PATH)
    logger = ls.AutoLogger()
    ls.add_save_root_to(my_config)
    save_root_dir = my_config.save.root
    task_dir = os.path.join(save_root_dir, "TB3_funccheck")
    # rtl_list_path = "data/HDLBits/HDLBits_data_RTL_4omini_50.jsonl"
    rtl_list_path = "data/HDLBits/HDLBits_data_RTL_4o_20.jsonl"
    probset = HDLBitsProbset(PROBSET_PATH, [rtl_list_path])
    i_reduced = 0
    for data in probset.data:
        if len(data["llmgen_RTL"]) > RTL_LIST_NUM_REDUCE_TO:
            i_reduced += 1
            data["llmgen_RTL"] = data["llmgen_RTL"][:RTL_LIST_NUM_REDUCE_TO]
    logger.info(f"reduced {i_reduced} RTL lists to {RTL_LIST_NUM_REDUCE_TO} in length")
    with open(AUTOBENCHRESULTS, "r") as f:
        idx = 0
        llm_manager.new_section()
        for line in f:
            idx += 1
            current_TB_info:dict = json.loads(line)
            task_id = current_TB_info["task_id"]
            result_id = current_TB_info.get("result_id", "")
            with ls.log_localprefix(f"{result_id}--{task_id}"):
                probdata = probset.access_data_via_taskid(task_id)
                task_tb3 = TB3_funccheck.TaskTBcheck(task_dir, task_id, probdata["description"], probdata["header"], current_TB_info["tb_v_driver"], current_TB_info["tb_py_checker"], probdata["llmgen_RTL"], discriminator_mode=my_config.autoline.TBcheck.discrim_mode, main_model=my_config.gpt.model, rtlgen_model=my_config.gpt.model, runfiles_save=False)
                task_tb3.discriminate_TB(True)
                # get the result
                if task_tb3.scenario_matrix is None:
                    task_tb3.scenario_matrix = np.array([[-1]])
                current_onehot_sce_matrix = task_tb3.scenario_matrix.tolist() # the matrix is a numpy array, when loading, can use matrix_data = np.array(entry["matrix"]) to convert it back
                result_dict = {"result_id": result_id, "task_id": task_id, "Eval_score": current_TB_info.get("Eval_score", "N/A"), "ease": current_TB_info.get("ease", "N/A"), "scen_matrix": current_onehot_sce_matrix}
                with open(scen_dict_path, "a") as f:
                    f.write(json.dumps(result_dict)+"\n")
            if idx >= MAX_ITER:
                break
            if idx % 20 == 0:
                logger.info(f"finished {idx} tasks")
                logger.info(f"cost for these tasks: {llm_manager.cost_section}, total cost: {llm_manager.cost_total}")
                llm_manager.new_section()
    logger.info(f"finished all {idx} tasks")
    logger.info(f"total cost: {llm_manager.cost_total}")


ONLY_RESULT_IDS = [43, 136, 175, 39]
SCEN_DICT_PATH = "data/AutoBenchResults/scen_dict.jsonl"
EASE_PATH = "data/AutoBenchResults/pass_sum.json"
FIGURE_FORMAT = "svg"
# discriminator_mode = ["col_full_wrong", "col_90_wrong", "col_80_wrong", "col_70_wrong", "col_60_wrong", "col_50_wrong", "col_40_wrong"]
discriminator_mode = ["col_full_wrong"]
def quick_discrim(scen_matrix_path:str=SCEN_DICT_PATH):
    """
    - how to quickly discrim? we use the already generated scenario matrix to do the discrimination, thus no compilation of verilog is needed!
    """
    my_config = Config(CONFIG_PATH)
    logger = ls.AutoLogger()
    ls.add_save_root_to(my_config)
    ease_dict = ls.load_json_dict(EASE_PATH)
    root_dir = my_config.save.root
    scen_draw = draw_scenario_matrix
    for mode in discriminator_mode:
        sub_root_dir = os.path.join(root_dir, f"{mode}")
        os.makedirs(sub_root_dir, exist_ok=True)
        with ls.log_localprefix(f"{mode}"):
            disc_mode = my_config.autoline.TBcheck.discrim_mode
            # logger.success(f"discriminating with mode: {mode}")
            pass_but_killed_dict = {}
            blind_tasks_dict = {}
            discriminator = TB3_funccheck.TB_discriminator(mode)
            result_dict = {"positive_TB_negative_DSC": 0, "positive_TB_positive_DSC": 0, "negative_TB_positive_DSC": 0, "negative_TB_negative_DSC": 0}
            done_num = 0
            for line in open(scen_matrix_path, "r"):
                entry = json.loads(line)
                scen_matrix = np.array(entry["scen_matrix"])
                Eval_score = entry.get("Eval_score", -1)
                task_id = entry["task_id"]
                result_id = entry.get("result_id", "")
                groundtruth = (Eval_score >= 0.8)
                if ONLY_RESULT_IDS != [] and result_id not in ONLY_RESULT_IDS:
                    continue
                disc_TBpass, wrong_scen, correct_scen, unsure_scen = discriminator.discriminate(scen_matrix)
                if disc_TBpass is None:
                    result_dict["negative_TB_negative_DSC"] += 1
                else:
                    if disc_TBpass:
                        if groundtruth:
                            result_dict["positive_TB_positive_DSC"] += 1
                            draw_save_path = os.path.join(sub_root_dir, "pospos", f"pospos_{task_id}_{result_id}.{FIGURE_FORMAT}")
                            matrix_save_path = os.path.join(sub_root_dir, "pospos", f"pospos_{task_id}_{result_id}.csv")
                            os.makedirs(os.path.join(sub_root_dir, "pospos"), exist_ok=True)
                            scen_draw(scen_matrix, task_id+f"[{result_id}]", draw_save_path)
                            np.savetxt(os.path.join(matrix_save_path), scen_matrix, delimiter=",", fmt="%d")
                        else:
                            result_dict["negative_TB_positive_DSC"] += 1
                            # count into the blind 
                            if task_id not in blind_tasks_dict.keys():
                                blind_tasks_dict[task_id] = 1
                            else:
                                blind_tasks_dict[task_id] += 1
                    else:
                        if groundtruth:
                            # this is what we don't want to see
                            result_dict["positive_TB_negative_DSC"] += 1
                            if task_id not in pass_but_killed_dict.keys():
                                pass_but_killed_dict[task_id] = 1
                            else:
                                pass_but_killed_dict[task_id] += 1
                            # draw_save_path = os.path.join(sub_root_dir, f"{task_id}_{pass_but_killed_dict[task_id]}.png")
                            # scen_draw(scen_matrix, task_id+f"[{pass_but_killed_dict[task_id]}]", draw_save_path)
                        else:
                            result_dict["negative_TB_negative_DSC"] += 1
                            draw_save_path = os.path.join(sub_root_dir, "negneg", f"negneg_{task_id}_{result_id}.{FIGURE_FORMAT}")
                            matrix_save_path = os.path.join(sub_root_dir, "negneg", f"negneg_{task_id}_{result_id}.csv")
                            os.makedirs(os.path.join(sub_root_dir, "negneg"), exist_ok=True)
                            scen_draw(scen_matrix, task_id+f"[{result_id}]", draw_save_path)
                            np.savetxt(os.path.join(matrix_save_path), scen_matrix, delimiter=",", fmt="%d")

                done_num += 1
                if done_num >= MAX_ITER:
                    break   
                # if done_num % 100 == 0:
                #     logger.success(f"finished {done_num} tasks")
            # special session: if all the pass TB been killed by our discriminator
            killed_tasks = 0
            blind_tasks = 0
            killed_task_ids = []
            killed_task_ease = []
            blind_task_ids = []
            blind_task_ease = []
            for task_id, killed_num in pass_but_killed_dict.items():
                if killed_num == ease_dict[task_id]:
                    killed_tasks += 1
                    killed_task_ids.append(task_id)
            for task_id, blind_num in blind_tasks_dict.items():
                if blind_num == (10 - ease_dict[task_id]):
                    blind_tasks += 1
                    blind_task_ids.append(task_id)
            for task_id in killed_task_ids:
                killed_task_ease.append(ease_dict[task_id])
            for task_id in blind_task_ids:
                blind_task_ease.append(ease_dict[task_id])
            result_print  = " final confusion matrix:\n"
            result_print += "                | positive_TB | negative_TB |\n"
            result_print += " positive_DSC   | %11d | %11d |\n" % (result_dict["positive_TB_positive_DSC"], result_dict["negative_TB_positive_DSC"])
            result_print += " negative_DSC   | %11d | %11d |\n" % (result_dict["positive_TB_negative_DSC"], result_dict["negative_TB_negative_DSC"])
            total_success_rate = (result_dict["positive_TB_positive_DSC"]+result_dict["negative_TB_negative_DSC"])/done_num * 100
            posTB_success_rate = result_dict["positive_TB_positive_DSC"]/(result_dict["positive_TB_positive_DSC"]+result_dict["positive_TB_negative_DSC"]) * 100
            negTB_success_rate = result_dict["negative_TB_negative_DSC"]/(result_dict["negative_TB_negative_DSC"]+result_dict["negative_TB_positive_DSC"]) * 100
            result_print += "total success rate: %.2f\n" % total_success_rate
            result_print += "success rate for correct TB: %.2f\n" % posTB_success_rate
            result_print += "success rate for wrong TB: %.2f\n" % negTB_success_rate
            result_print += "killed tasks: %d " % killed_tasks + "(all the passed TBs of these tasks are discriminated as wrong)\n"
            result_print += "killed tasks' ease: " + str(killed_task_ease) + "\n"
            result_print += "blind tasks: %d" % blind_tasks + "(all the failed TBs of these tasks are discriminated as correct)\n"
            result_print += "blind tasks' ease: " + str(blind_task_ease) + "\n"
            logger.success("\n"+result_print + "\n\n")

def draw_scenario_matrix(scenario_matrix:np.ndarray, task_id:str, saving_path:str):
    """
    - draw the 2D failed scenario array. The element in the array can only be 0, 1, -1. We use red for 0, green for 1, and gray for -1.
    - if the scenario is empty, will return a gray color block.
    """
    if len(scenario_matrix) == 0:
        scenario_matrix = np.array([[-1]])
    # if the element in data not in [0, 1, -1], change the element to -1
    scenario_matrix = np.where(np.logical_or(scenario_matrix == 0, np.logical_or(scenario_matrix == 1, scenario_matrix == -1)), scenario_matrix, -1)
    # get the RGB values for salmon, grey and mediumseagreen
    salmon = mcolors.to_rgb("salmon")
    grey = mcolors.to_rgb("grey")
    # mediumseagreen = mcolors.to_rgb("darkgreen")
    mediumseagreen = [0.0, 0.6666666666666666, 0.4980392156862745]
    # salmon = [0.9333333333333333, 0.48627450980392156, 0.4745098039215686]
    # print(salmon, grey, mediumseagreen)
    color_mapping = {
        0: salmon,
        1: mediumseagreen,
        -1: grey
    }
    rgb_image = np.array([[color_mapping[value] for value in row] for row in scenario_matrix])
    # assign the color to the scenario_matrix
    for value, color in color_mapping.items():
        rgb_image[scenario_matrix == value] = color
    plt.figure(figsize=(6, 6))
    plt.imshow(rgb_image)
    # use times new roman font
    plt.ylabel("RTL index", fontsize=20)
    plt.xlabel("Scenario index", fontsize=20)
    # # the numbers on ylabel should be 0, 4, 8, 12, 16
    # plt.yticks(np.arange(0, len(scenario_matrix), 4), fontsize=16)
    # # the numbers on xlabel should has a step of 4
    # plt.xticks(np.arange(0, len(scenario_matrix[0]), 4), fontsize=16)
    # plt.gca().set_xticks(np.arange(-0.5, len(scenario_matrix[0])-0.5, 1), minor=True)
    # plt.gca().set_yticks(np.arange(-0.5, 19.5, 1), minor=True)
    plt.xticks(ticks=np.arange(-0.5, len(scenario_matrix[0])-0.5, 1), minor=True)
    plt.yticks(ticks=np.arange(-0.5, 19.5, 1), minor=True)
    plt.xticks(ticks=np.arange(0, len(scenario_matrix[0])-0.5, 4))
    plt.yticks(ticks=np.arange(0, 19.5, 4))
    # I only want one kind of grid, the grid step is 1
    plt.grid(which='minor', color='lightgrey', linestyle='-', linewidth=1)
    # plt.grid(which='minor', color='white', linestyle='-', linewidth=1)
    plt.savefig(saving_path, format=FIGURE_FORMAT)
    plt.close()

if __name__ == "__main__":
    main()


"""
CONFIG TEMPLATE:

run: 
    mode: autoline
save: 
    en: True
    pub: 
        prefix: fullwrongmode_10rtl_gpt4t
        subdir: discriminator
    log: 
        debug_en: True
        level: INFO
autoline: 
    TBcheck: 
        discrim_mode: col_full_wrong
"""