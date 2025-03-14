"""
Description :   generate confidence according to RS matrix, test the matchness between confidence and the ground truth scenario correctness
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2025/1/8 04:44:46
LastEdited  :   2025/3/12 15:59:05
"""

import loader_saver as ls
import config
from loader_saver import autologger
from config import Config
import os
from data.probset import HDLBitsProbset
from autoline.TB4_eval import TaskTBeval
from autoline.TB3_funccheck import TaskTBcheck
from sympy import symbols, Eq, solve, exp
import matplotlib.pyplot as plt
import math
import numpy as np
import json
import scipy

class Confidence:
    """
    ## anything regarding confidence
    - conf_gen: generate confidence according to RS matrix
    - conf_test: test the matchness between confidence and the ground truth scenario correctness
    """
    e_rank_super_cache_conf_thresh = 0
    e_rank_super_cache_K = 0
    e_rank_super_cache_A = 0
    e_rank_super_cache_B = 0
    e_rank_super_cache_configered = False

    def __init__(self, confidence_config):
        self.config = confidence_config
        
        # confidence related config
        self.conf_stra = self.config.confidence.strategy
        
        # boolean confidence related config
        self.conf_bool_str = self.config.conf_bool.strategy
        self.e_rank_super_threshold = self.config.conf_bool.e_rank_super.threshold
        self.e_rank_super_K = self.config.conf_bool.e_rank_super.K
        self.confb_e_rank_super_config(self.e_rank_super_threshold, self.e_rank_super_K)
        self.conf_only_threshold = self.config.conf_bool.conf_only.threshold
        # set the confidence boolean function
        strategy_mode = self.conf_bool_str
        conf_bool_func_dict = {
            "e_rank": self.confb_e_rank,
            "e_rank_super": self.confb_e_rank_super,
            "conf_only": self.confb_conf_only
        }
        autologger.assert_(strategy_mode in conf_bool_func_dict.keys(), f"strategy_mode {strategy_mode} is not supported")
        self.conf_bool_func = conf_bool_func_dict[strategy_mode]
        self.conf_bool_func_name = strategy_mode
        # latest record:
        self.last_confidence = []
        self.last_conf_bool = []
        self.last_rank = []


    def conf_gen(self, RS_matrix: list[list[int]], scenario_num: int)->list[float]:
        # rule of confidence:
        # input matrix is a m row n col matrix. output confidence is a list with lenth = n
        # 1. delete the rows in RS matrix that all elements are -1
        # 2. init confidence list with all 1
        # 3. for each column, calculate the penalty: penalty = e^x - 1. x is the percentage of 0 in the column. then we will get a penalty list with length = n
        # 4. for each row, if the row is full of 1, reward_total += 1. calculate the percentage of all 1 rows in all of the rows that is not full of -1, the percentage is x. reward = ln(x+1). then we have a list of reward with all the elements in the list is the same, lenth = n
        # 5. calculate the confidence: confidence = 1 - penalty + reward
        # 6. if the confidence is less than 0, set it to 0; if the confidence is larger than 1, set it to 1
        # 7. return confidence
        strategy = self.conf_stra
        RS_matrix = np.array(RS_matrix)
        col_num = scenario_num
        # step 1
        RS_matrix = RS_matrix[~np.all(RS_matrix == -1, axis = 1)]
        # step 2
        confidence = [1] * col_num
        # step 3
        penalties = self._penalty(RS_matrix, scenario_num)  
        # step 4
        rewards = self._reward(RS_matrix, scenario_num)
        # step 5
        confidence = 1 - penalties + rewards
        # step 6
        confidence = [0 if i < 0 else i for i in confidence]
        confidence = [1 if i > 1 else i for i in confidence]
        # step 7
        confidence = [float(i) for i in confidence]
        self.last_confidence = confidence # record the confidence
        return confidence
    
    def conf_bool_gen(self, confidence: list[float])->list[bool]:
        # we want get a rank score list of the confidence. the rank score is a list with the same length as the confidence list. the rank score is a float between 0 and 1. the rank score is calculated by the rank of the confidence in a even way. 1 is the highest rank score, 0 is the lowest rank score. the rank score is calculated by the formula: rank score = rank / len(confidence)

        conf_rank = scipy.stats.rankdata(confidence, method='average') / len(confidence)
        self.last_rank = conf_rank # record the rank score
        conf_bool = [False] * len(confidence)

        for i in range(len(confidence)):
            conf_bool[i] = self.conf_bool_func(confidence[i], conf_rank[i])
        self.last_conf_bool = conf_bool # record the confidence boolean
        return conf_bool

    def _penalty(self, RS_matrix: list[list[int]], scenario_num: int, p_strategy: str = "exp_std", p_alpha: float = 1):
        penalty_list = []
        for i in range(scenario_num):
            column = RS_matrix[:, i]
            percentage_of_zeros = np.sum(column == 0) / len(column)
            if p_strategy == "exp_std":
                penalty = p_alpha * (np.exp(percentage_of_zeros) - 1)
            elif p_strategy == "pwr_2_std":
                penalty = p_alpha * (percentage_of_zeros ** 2)
            penalty_list.append(penalty)
        return np.array(penalty_list)

    def _reward(self, RS_matrix: list[list[int]], scenario_num: int, reward_strategy: str = "log_std", reward_alpha: float = 0.1):
        reward_total = 0
        for row in RS_matrix:
            if np.all(row == 1):
                reward_total += 1
        if reward_strategy == "log_std":
            reward = reward_alpha * math.log(reward_total / len(RS_matrix) + 1)
        elif reward_strategy == "root_2":
            reward = reward_alpha * math.sqrt(reward_total / len(RS_matrix))
        return np.array([reward] * scenario_num) 

    @staticmethod
    def confb_e_rank(confidence: float, conf_rank: float):
        # 1. the confidence lager than 0.8 is always correct
        # 2. the confidence less than 0.2 is always wrong
        # 3. the confidence between 0.2 and 0.8 will be predicted by both its value and its rank in the confidence list. the rule is: total score of one scenario = confidence * e^(rank-1). if the total score is larger than 0.5, the scenario is predicted as correct. otherwise, it is predicted as wrong. 
        if confidence > 0.8:
            conf_bool = True
        elif confidence < 0.2:
            conf_bool = False
        else:
            total_score = confidence * math.exp(conf_rank - 1)
            if total_score > 0.5:
                conf_bool = True
            else:
                conf_bool = False
        return conf_bool
    
    def confb_e_rank_super_config(self, conf_thresh=0.2, K_value = 8):
        self.e_rank_super_configered = True
        if (Confidence.e_rank_super_cache_conf_thresh == conf_thresh) and (Confidence.e_rank_super_cache_K == K_value) and Confidence.e_rank_super_cache_configered:
            # use class cache        
            self.A_value = Confidence.e_rank_super_cache_A
            self.B_value = Confidence.e_rank_super_cache_B
            self.K_value = Confidence.e_rank_super_cache_K
            return
        Confidence.e_rank_super_cache_conf_thresh = conf_thresh
        Confidence.e_rank_super_cache_configered = True
        m = conf_thresh
        a, b = symbols('a b')
        eq1 = Eq(a - exp(K_value*m + b), 1)
        eq2 = Eq(a - exp(K_value*(1 - m) + b), 0)
        A_value, B_value = solve((eq1, eq2), (a, b))[0]
        self.A_value = A_value
        self.B_value = B_value
        self.K_value = K_value
        Confidence.e_rank_super_cache_A = A_value
        Confidence.e_rank_super_cache_B = B_value
        Confidence.e_rank_super_cache_K = K_value

    def confb_e_rank_super(self, confidence: float, conf_rank: float):
        autologger.assert_(hasattr(self, 'e_rank_super_configered'), "Please config confb_e_rank_super first")
        if conf_rank + math.exp(self.K_value*confidence+self.B_value) > self.A_value:
            return True
        else:
            return False

    def confb_conf_only(self, confidence: float, conf_rank: float):
        if confidence > self.conf_only_threshold:
            return True
        else:
            return False

    def conf_test(self):
        pass

    def draw_conf_bool_region(self, fig_path):
        # Generate a grid of confidence and rank values
        confidence_values = np.linspace(0, 1, 500)
        rank_values = np.linspace(0, 1, 500)  # rank ranges from 0 to 1
        confidence_grid, rank_grid = np.meshgrid(confidence_values, rank_values)

        # Classify each point in the grid
        classification = np.vectorize(self.conf_bool_func)(confidence_grid, rank_grid)

        # Plotting
        plt.figure(figsize=(8, 8))
        plt.contourf(confidence_grid, rank_grid, classification, levels=[0, 0.5, 1], cmap='coolwarm', alpha=0.7)
        plt.colorbar(label='Classification (red for True, blue for False)')

        if self.conf_bool_func_name in ["e_rank_super", "e_rank"]:
            threshold = 0.2 if self.conf_bool_func_name == "e_rank" else self.e_rank_super_threshold
            # Plot threshold boundaries
            plt.axvline(x=threshold, color='black', linestyle='--', label='Confidence = %.2f' %(threshold))
            plt.axvline(x=1-threshold, color='black', linestyle='--', label='Confidence = %.2f' %(1-threshold))
        elif self.conf_bool_func_name == "conf_only":
            plt.axvline(x=self.conf_only_threshold, color='black', linestyle='--', label='Confidence = %.2f'%(self.conf_only_threshold))

        title_suffix = ""
        if self.conf_bool_func_name == "e_rank_super":
            title_suffix = f", threshold={Confidence.e_rank_super_cache_conf_thresh}, K={Confidence.e_rank_super_cache_K}"
        plt.title(f'Boolean Confidence Region (alg: {self.conf_bool_func_name}{title_suffix})')
        plt.xlabel('Confidence')
        plt.ylabel('Rank')
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.legend(loc='lower center')
        plt.grid(True)
        plt.savefig(fig_path)
        plt.close()

    @staticmethod
    def draw_conf_confbool_lists(conf_list:list[float], conf_bool_list:list[bool], save_path:str, title:str = ""):
        # Verify that all lists have the same length
        assert len(conf_list) == len(conf_bool_list), "All lists must have the same length."
        length = len(conf_list)
        data = [conf_list, conf_bool_list]
        labels = ['Confidence', 'Conf_bool']
        # Create a custom colormap from red to green to blue
        cmap = plt.get_cmap('RdYlGn')
        # Create a figure with 2 subplots
        fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(1.2*length+2, 4), constrained_layout=True)
        for ax, d, label in zip(axes, data, labels):
            # Display each list as an image
            cax = ax.imshow([d], cmap=cmap, aspect='auto', vmin=0, vmax=1)
            ax.set_title(label)
            ax.set_xticks(range(len(d)))
            ax.set_yticks([])  # No y-ticks for the individual plots
            ax.set_xlim(-0.5, len(d) - 0.5)
            for j, val in enumerate(d):
                ax.text(j, 0, f'{val:.2f}', ha='center', va='center', color='black', fontsize=15)
        cbar = fig.colorbar(cax, ax=axes, orientation='vertical', fraction=0.02, pad=0.04)
        cbar.set_label('Value')
        fig.suptitle(title)
        plt.savefig(save_path)
        plt.close()


class CorrectBenchResultTester:
    def __init__(self, result_path = None, probset_path = None, test_num = 1, start_id = 1):
        self.test_num = test_num
        self.start_id = start_id
        self.result_path = "/home/ge45vuq/Projects/Chatbench/data/CorrectBenchResults/run_info_and_codes_new.jsonl" if result_path is None else result_path
        self.probset_path = "/home/ge45vuq/Projects/Chatbench/data/HDLBits/HDLBits_data.jsonl" if probset_path is None else probset_path
        self.probset = HDLBitsProbset(self.probset_path)
        self.CB_result = HDLBitsProbset(self.result_path)
        self.CB_result_data = self.CB_result.data
        self.result_num = self.CB_result.num
        self.config = Config()
        self.confidencer = None
        self.MSE_Eval1 = [] # point biserial correlation of Eval1
        self.MSE_Eval1_failed = [] # point biserial correlation of Eval1 (for those failing at Eval1)
        self.MSE_Eval1_passed = [] # point biserial correlation of Eval1 (for those passing at Eval1)

    def run(self, conf_config):
        # run MSE test for Eval1 and draw the result
        self.confidencer = Confidence(conf_config)
        self.get_MSE_Eval1()
        self.draw_MSE(self.MSE_Eval1, os.path.join(self.config.save.root, "MSE_Eval1.png"), "Eval1")
        self.draw_MSE(self.MSE_Eval1_failed, os.path.join(self.config.save.root, "MSE_Eval1_failed.png"), "Eval1_failed")
        self.draw_MSE(self.MSE_Eval1_passed, os.path.join(self.config.save.root, "MSE_Eval1_passed.png"), "Eval1_passed")

    def get_MSE_Eval1(self):
        MSE_skipped_id = []
        for i in range(self.result_num):
            self.cur_result_id = i + 1
            autologger.info(f"Processing result {self.cur_result_id}")
            self.cur_result = self.CB_result_data[self.cur_result_id-1]
            self.cur_data = self.probset.find_data_by_id(self.cur_result['task_id'])
            self.cur_scenario_num = self.cur_result['scenario_num']
            self.cur_TB_correctness = self.cur_result["Eval1_scen_data"]["TB_correctness"]
            if self.self_check() is False:
                MSE_skipped_id.append(self.cur_result_id)
                continue
            self.cur_TB_confidence = self.confidencer.conf_gen(self.cur_result["RSmatrixes"][-1][-1], scenario_num=self.cur_scenario_num)
            cur_MSE_Eval1 = mean_square_error(self.cur_TB_correctness, self.cur_TB_confidence)
            self.MSE_Eval1.append(cur_MSE_Eval1)
            if self.cur_result["Eval_score"] < 0: 
                self.MSE_Eval1_failed.append(cur_MSE_Eval1)
            else:
                self.MSE_Eval1_passed.append(cur_MSE_Eval1)
        autologger.info("MSE test for Eval1 finished")
        autologger.info(f"MSE test skipped for the following {len(MSE_skipped_id)} results: {str(MSE_skipped_id)}")
        return self.MSE_Eval1, self.MSE_Eval1_failed, self.MSE_Eval1_passed
    
    def get_Eval1_pass_ratio(self):
        Eval1_pass_ratio = 0.
        pass_num = 0
        total_num = 0
        scen_waste_ratio_total = 0.
        for i in range(self.result_num):
            self.cur_result_id = i + 1
            autologger.info(f"Processing result {self.cur_result_id}")
            self.cur_result = self.CB_result_data[self.cur_result_id-1]
            self.cur_data = self.probset.find_data_by_id(self.cur_result['task_id'])
            self.cur_scenario_num = self.cur_result['scenario_num']
            self.cur_TB_correctness = self.cur_result["Eval1_scen_data"]["TB_correctness"]
            if self.self_check() is False:
                continue
            self.cur_TB_confidence = self.confidencer.conf_gen(self.cur_result["RSmatrixes"][-1][-1], scenario_num=self.cur_scenario_num)
            self.cur_TB_confidence_bool = self.confidencer.conf_bool_gen(self.cur_TB_confidence)
            TT_num, TF_num, FT_num, FF_num = 0, 0, 0, 0
            for i in range(self.cur_scenario_num):
                match self.cur_TB_correctness[i], self.cur_TB_confidence_bool[i]:
                    case 1, True:
                        TT_num += 1
                    case 1, False:
                        TF_num += 1
                    case 0, True:
                        FT_num += 1
                    case 0, False:
                        FF_num += 1
            if FT_num == 0:
                pass_num += 1
            else:
                scen_waste_ratio_cur = TF_num / (TT_num + TF_num) if (TT_num + TF_num) != 0 else 0
                scen_waste_ratio_total += scen_waste_ratio_cur
            total_num += 1
            autologger.info(f"result {self.cur_result_id}: TT_num: {TT_num}, TF_num: {TF_num}, FT_num: {FT_num}, FF_num: {FF_num}")
        Eval1_pass_ratio = pass_num / total_num
        scen_waste_ratio_total = scen_waste_ratio_total / pass_num
        return Eval1_pass_ratio, scen_waste_ratio_total

    def draw_Eval1Failed_four_lists_and_RSmatrix(self, start_id=1, end_id=9999, num=20, only_Eval1Failed=True):
        counter = 0
        os.makedirs(self.config.save.root, exist_ok=True)
        self.cur_result_id = 0
        for i in range(start_id, end_id+1):
            self.cur_result_id = i
            if counter >= num:
                break
            self.cur_result = self.CB_result_data[self.cur_result_id-1]
            if self.self_check() is False:
                continue
            if (self.cur_result["Eval_score"] != -1.0) and only_Eval1Failed:
                continue
            if self.cur_result["result_id"] < start_id or self.cur_result["result_id"] > end_id:
                continue
            autologger.info(f"Processing result {self.cur_result_id}")
            self.cur_scenario_num = self.cur_result['scenario_num']
            self.cur_TB_correctness = self.cur_result["Eval1_scen_data"]["TB_correctness"]
            self.cur_TB_confidence = self.confidencer.conf_gen(self.cur_result["RSmatrixes"][-1][-1], scenario_num=self.cur_scenario_num)
            self.cur_TB_conf_bool = self.confidencer.conf_bool_gen(self.cur_TB_confidence)
            self.cur_TB_conf_rank = self.confidencer.last_rank
            save_path = os.path.join(self.config.save.root, f"{self.cur_result["result_id"]}_{self.cur_result['task_id']}.png")
            self.draw_conf_compare_super(self.cur_TB_correctness, self.cur_TB_confidence, self.cur_TB_conf_bool, self.cur_TB_conf_rank, f"result_{self.cur_result["result_id"]}_{self.cur_result['task_id']}", save_path)
            TaskTBcheck.draw_scenario_matrix(np.array(self.cur_result["RSmatrixes"][-1][-1]), f"{self.cur_result["result_id"]}_{self.cur_result['task_id']}", os.path.join(self.config.save.root, f"{self.cur_result["result_id"]}_{self.cur_result['task_id']}_RS_matrix.png"))
            counter += 1

    def self_check(self):
        # column number of RS matrix should be equal to the scenario number
        if self.cur_result["RSmatrixes"] is None:
            autologger.error(f"Error in processing result {self.cur_result_id}: RS matrix is None; WILL SKIP THIS RESULT")
            return False
        if self.cur_result["scenario_num"] != len(self.cur_result["RSmatrixes"][-1][-1][0]):
            autologger.error(f"Error in processing result {self.cur_result_id}: RS matrix column number ({len(self.cur_result["RSmatrixes"][-1][-1][0])}) is not equal to the scenario number ({self.cur_result["scenario_num"]}) recorded in result file; WILL SKIP THIS RESULT")
            return False
        if self.cur_result["Eval1_scen_data"]["TB_correctness"] is None:
            autologger.error(f"Error in processing result {self.cur_result_id}: TB_correctness is None; WILL SKIP THIS RESULT")
            return False

    def draw_MSE(self, MSE, save_path, MSE_name:str=""):
        plt.hist(MSE, bins=20, color='blue', edgecolor='black')
        plt.xlabel('MSE')
        plt.ylabel(f'Amount (total: {len(MSE)})')
        plt.title('MSE Distribution - ' + MSE_name)
        plt.savefig(save_path)
        plt.close()
    

            




    # def run(self):
    #     test_num = self.test_num
    #     result_id = self.start_id
    #     while test_num > 0:
    #         self.cur_result = self.result_df.iloc[result_id-1]
    #         if self.cur_result['Eval_score'] != -1.0:
    #             result_id += 1
    #             continue
    #         self.run_test_single_result(result_id)
    #         result_id += 1
    #         test_num -= 1

    # # not used, the correctness is already stored in the result file
    # def run_test_single_result(self, result_id):
    #     # pick the result_id th line from result_df
    #     self.cur_result = self.result_df.iloc[result_id-1]
    #     self.cur_data = self.probset.find_data_by_id(self.cur_result['task_id'])
    #     self.cur_dir = os.path.join(self.config.save.root, f"{self.cur_result["result_id"]}_{self.cur_result['task_id']}")
    #     os.makedirs(self.cur_dir, exist_ok=True)
    #     RS_matrix = self.cur_result['RSmatrixes'][-1][-1]
    #     self.cur_scenario_num = len(RS_matrix[0])
    #     # save the result to a file
    #     cur_result_dict = self.cur_result.to_dict()
    #     cur_result_dict.pop("RSmatrixes")
    #     cur_result_dict.pop("tb_v_driver")
    #     cur_result_dict.pop("tb_py_checker")
    #     cur_result_dict = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in cur_result_dict.items()}
    #     with open(os.path.join(self.cur_dir, "result.json"), "w") as f:
    #         json.dump(cur_result_dict, f)
    #     # draw RS matrix
    #     TaskTBcheck.draw_scenario_matrix(np.array(RS_matrix), f"{self.cur_result["result_id"]}_{self.cur_result['task_id']}", os.path.join(self.cur_dir, "RS_matrix.png"))
    #     # save RS matrix into a file
    #     with open(os.path.join(self.cur_dir, "RS_matrix.txt"), "w") as f:
    #         f.write(str(RS_matrix))
    #     # get confidence
    #     confidence = Confidence().conf_gen(RS_matrix)
    #     # get Eval1 correctness
    #     correctness = self._get_Eval1_correctness()
    #     if correctness is not None:
    #         self.draw_conf_correct_compare(confidence, correctness, os.path.join(self.cur_dir, "conf_correct_compare.png"))
    #     else:
    #         # make a empty file with name run_failed
    #         with open(os.path.join(self.cur_dir, "run_failed"), "w") as f:
    #             pass
        
        
        

    def _get_Eval1_correctness(self, save_Eval1_files=False):
        # get the Eval1 correctness, return a list with the same length as the scenario number
        # Eval part:
        autologger.assert_(hasattr(self, 'cur_result'), "Please run the test first")
        # TBEval = TaskTBeval(self.cur_data["task_id"], os.path.join(self.cur_dir, "eval1"), TB_gen=self.cur_result["tb_v_driver"], TB_golden=self.cur_data["testbench"], DUT_golden=self.cur_data["module_code"], pychecker_en=True, pychecker_code=self.cur_result["tb_py_checker"], runfiles_save=True)
        # TBEval.run_Eval1()
        # TBEval.clean_wave_vcd()
        try:
            failed_scenarios = TaskTBcheck.run_testbench(os.path.join(self.cur_dir, "Eval1"), self.cur_result["tb_v_driver"], self.cur_data["module_code"], self.cur_result["tb_py_checker"], save_en=save_Eval1_files)
            # use cur_scenario_num and failed_scenarios, convert failed_scenarios into a correctness list: [0, 0 , 1, 1, 1], 0 for failed, 1 for passed. The first scenario's index is 1
            correctness = [1] * self.cur_scenario_num
            for i in failed_scenarios:
                correctness[i-1] = 0
            return correctness
        except Exception as e:
            return None

    @staticmethod
    def draw_list(input_nums, save_path):
        # draw the confidence/correctness list. the elements' value is between 0 and 1. use red for 0 and green for 1. use continuous color for values between 0 and 1.
        # we want a lot of blocks, each block is a rectangle with width = 1, height = 1. the color of the block is determined by the value of the element in the list
        # the blocks are horizontally arranged. the value of each block is attached under the block.
        # the whole picture is saved to save_path
        fig, ax = plt.subplots()
        ax.set_xlim(0, len(input_nums))
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        ax.axis('off')
        for i in range(len(input_nums)):
            ax.add_patch(plt.Rectangle((i, 0), 1, 1, color=(1-input_nums[i], input_nums[i], 0)))
            ax.text(i+0.5, 0.5, f"{input_nums[i]:.2f}", ha='center', va='center')
        plt.savefig(save_path)
        plt.close()
    
    @staticmethod
    def draw_conf_correct_compare(confidence, correctness, save_path):
        # draw the confidence/correctness list. the elements' value is between 0 and 1. use red for 0 and green for 1. use continuous color for values between 0 and 1.
        # we want a lot of blocks, each block is a rectangle with width = 1, height = 1. the color of the block is determined by the value of the element in the list
        # the blocks are horizontally arranged. the value of each block is attached under the block.
        # the first row is confidence, the second row is correctness
        # the whole picture is saved to save_path
        # please attach "confidence" and "correctness" on the left of each row
        fig, ax = plt.subplots()
        ax.set_xlim(0, len(confidence))
        ax.set_ylim(0, 2)
        ax.set_aspect('equal')
        ax.axis('off')
        for i in range(len(confidence)):
            ax.add_patch(plt.Rectangle((i, 0), 1, 1, color=(1-confidence[i], confidence[i], 0)))
            ax.text(i+0.5, 0.5, f"{confidence[i]:.2f}", ha='center', va='center')
            ax.add_patch(plt.Rectangle((i, 1), 1, 1, color=(1-correctness[i], correctness[i], 0)))
            ax.text(i+0.5, 1.5, f"{correctness[i]}", ha='center', va='center')
        # attach "confidence" and "correctness" on the left of each row
        ax.text(-1, 0.5, "confidence", ha='center', va='center')
        ax.text(-1, 1.5, "correctness", ha='center', va='center')
        plt.savefig(save_path)
        plt.close()

    @staticmethod
    def draw_conf_compare_super(correctness, confidence, conf_bool, rank, title, save_path):
        # Verify that all lists have the same length
        assert len(correctness) == len(confidence) == len(conf_bool) == len(rank), "All lists must have the same length."
        length = len(correctness)
        data = [confidence, rank, conf_bool, correctness]
        labels = ['Confidence', 'Rank', 'Conf_bool', 'Correctness']
        # Create a custom colormap from red to green to blue
        cmap = plt.get_cmap('RdYlGn')
        # Create a figure with 4 subplots
        fig, axes = plt.subplots(nrows=4, ncols=1, figsize=(1.2*length+2, 8), constrained_layout=True)
        for ax, d, label in zip(axes, data, labels):
            # Display each list as an image
            cax = ax.imshow([d], cmap=cmap, aspect='auto', vmin=0, vmax=1)
            ax.set_title(label)
            ax.set_xticks(range(len(d)))
            ax.set_yticks([])  # No y-ticks for the individual plots
            ax.set_xlim(-0.5, len(d) - 0.5)
            for j, val in enumerate(d):
                ax.text(j, 0, f'{val:.2f}', ha='center', va='center', color='black', fontsize=15)
        cbar = fig.colorbar(cax, ax=axes, orientation='vertical', fraction=0.02, pad=0.04)
        cbar.set_label('Value')
        fig.suptitle(title)
        plt.savefig(save_path)
        plt.close()

def mean_square_error(correctness:list[float], confidence:list[float]):
    mse = np.mean((np.array(confidence) - np.array(correctness))**2)
    return mse

# if "__main__" == __name__:
#     my_config = config.Config(config.CFG_CUS_PATH)
#     logger = ls.AutoLogger() # initialize the autologger
#     tester = CorrectBenchResultTester()
#     tester.run()

if "__main__" == __name__:
    my_config = config.Config(config.CFG_CUS_PATH)
    logger = ls.AutoLogger() # initialize the autologger
    tester = CorrectBenchResultTester()
    tester.confidencer = Confidence(my_config.confibench)
    
    Eval1_pass_ratio, scen_waste_ratio_total = tester.get_Eval1_pass_ratio()
    logger.info(f"Eval1 pass ratio: {Eval1_pass_ratio}")
    logger.info(f"Average scenario waste ratio: {scen_waste_ratio_total}")
    tester.confidencer.draw_conf_bool_region(os.path.join(my_config.save.root, "conf_bool_region.png"))
    logger.info("Confidence boolean region saved")

    # tester.draw_Eval1Failed_four_lists_and_RSmatrix(start_id=300, end_id=9999, num=20, only_Eval1Failed=True)