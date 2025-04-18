"""
Description :   analyze the output from autoline mode.
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2023/12/12 17:35:00
LastEdited  :   2025/3/8 16:35:48
"""

import loader_saver as ls
import utils.utils as utils
from data.probset import dictlist, HDLBitsProbset, muti_dictlist
from LLM_call import PRICING_MODELS
import os
import math

import matplotlib.pyplot as plt
import matplotlib

"""
template of the EXP1 json file:
[
    {
        "task_id": "shift18",
        "task_number": 12,
        "sim_pass": true,
        "debug_iter": 1,
        "time": 374.14
        ...
    }
    {
        ...
    }
]
"""

LOOSE_FACTOR = 0.8
DEFAULT_SAVING_DIR = "analysis"
DEFAULT_LOG_NAME = "analyze_out.log"
DEFAULT_LOG_PATH = os.path.join(DEFAULT_SAVING_DIR, DEFAULT_LOG_NAME)
K_LIST = [1]

MULTI_DIR = "saves_inEDA/TODAES/ConfiBench_4omini"

CONFIBENCH_DATA_DIR = "saves_inEDA/Y25_0224~0302/NO1_ConfiBench_4omini_20250226_104808"

CHATBENCH_RUNINFO_PATH = "saves_inEDA/TODAES/ConfiBench_4o/NO1_20250302_220907/Chatbench_RunInfo.json"

def main():
    diy_main()
    # regular_main()
    # regular_multiA_main()

def diy_main():

    # k_list = [1]
    # multi_analyzer = MultiAnalyzer(MULTI_DIR, k_list)    
    # multi_analyzer.messages += "\n#################### TOTAL ####################\n"
    # multi_analyzer.run()
    # multi_analyzer.get_avg_tokens_one_task()
    # multi_analyzer.get_avg_pass_by_disc_and_corr()
    # multi_analyzer.get_Eval_score_levelbar_chart()
    # multi_analyzer.draw_Evalscore_histogram()
    # multi_analyzer.save()

    # # find the passed with correction
    # Chatbench_RunInfo = ls.load_json_dict(CHATBENCH_RUNINFO_PATH)
    # # analyze the data
    # analyzer = Analyzer(Chatbench_RunInfo)
    # analyzer.run()
    # for i in analyzer.data:
    #     if i.get("TB_corrected", False) and analyzer.Eval2_pass(i):
    #         print(i["task_id"])
    # save the result to a txt file
    # with open(DEFAULT_LOG_PATH, "w") as f:
    #     f.write(analyzer.messages)
    #     # also, write the current time
    #     f.write("analysis time: %s\n" % (utils.get_time()))

    # with open(DEFAULT_LOG_PATH, "w") as f:
    #     f.write("analysis time: %s\n" % (utils.get_time()))
    # # task_eval2passtimes_analyze()
    # full_analyzer = Analyzer(ls.load_json_dict(CHATBENCH_RUNINFO_PATH))
    # full_analyzer.run()
    # with open(DEFAULT_LOG_PATH, "a") as f:
    #     f.write(full_analyzer.messages)
    # analyze_subset(HDLBitsProbset("data/HDLBits/HDLBits_circuit_type.jsonl", filter_content={"circuit_type": "CMB"}), CHATBENCH_RUNINFO_PATH, "full CMB")
    # analyze_subset(HDLBitsProbset("data/HDLBits/HDLBits_circuit_type.jsonl", filter_content={"circuit_type": "SEQ"}), CHATBENCH_RUNINFO_PATH, "full SEQ")
    # analyze_subset("data/HDLBits/HDLBits_data_CMB15.jsonl", CHATBENCH_RUNINFO_PATH, "CMB15")
    # analyze_subset("data/HDLBits/HDLBits_data_SEQ15.jsonl", CHATBENCH_RUNINFO_PATH, "SEQ15")



    k_list = [1]
    # Eval_scenchecks = ["Eval0_scencheck", "Eval0_noscencheck", "Eval1_scencheck", "Eval1_noscencheck", "Eval2_scencheck", "Eval2_noscencheck"]
    # Eval_scenchecks = ["Eval2b", "Eval2"]
    multi_analyzer = MultiAnalyzer(MULTI_DIR, k_list)
    # multi_analyzer.exclude_debug = True
    multi_analyzer.messages += "\n#################### TOTAL ####################\n"
    multi_analyzer.run()
    multi_analyzer.get_avg_tokens_one_task()
    multi_analyzer.get_avg_pass_by_disc_and_corr()
    multi_analyzer.save()
    CMB_set = HDLBitsProbset("data/HDLBits/HDLBits_circuit_type.jsonl", filter_content={"circuit_type": "CMB"})
    SEQ_set = HDLBitsProbset("data/HDLBits/HDLBits_circuit_type.jsonl", filter_content={"circuit_type": "SEQ"})
    CMB_tasks = CMB_set.task_id_list
    SEQ_tasks = SEQ_set.task_id_list
    multi_analyzer_CMB = MultiAnalyzer(MULTI_DIR, k_list)
    # multi_analyzer_CMB.exclude_debug = True
    multi_analyzer_CMB.del_items(SEQ_tasks, del_by_list=True)
    # print(multi_analyzer_CMB.access("total_num"))
    multi_analyzer_CMB.messages += "\n#################### CMB ####################\n"
    multi_analyzer_CMB.run()
    multi_analyzer_CMB.get_avg_tokens_one_task()
    multi_analyzer_CMB.get_avg_pass_by_disc_and_corr()
    multi_analyzer_CMB.save(os.path.join(DEFAULT_SAVING_DIR, "CMB_" + DEFAULT_LOG_NAME))
    multi_analyzer_SEQ = MultiAnalyzer(MULTI_DIR, k_list)
    # multi_analyzer_SEQ.exclude_debug = True
    multi_analyzer_SEQ.del_items(CMB_tasks, del_by_list=True)
    multi_analyzer_SEQ.messages += "\n#################### SEQ ####################\n"
    multi_analyzer_SEQ.run()
    multi_analyzer_SEQ.get_avg_tokens_one_task()
    multi_analyzer_SEQ.get_avg_pass_by_disc_and_corr()
    multi_analyzer_SEQ.save(os.path.join(DEFAULT_SAVING_DIR, "SEQ_" + DEFAULT_LOG_NAME))

    multi_analyzer_SEQ.save(os.path.join(DEFAULT_SAVING_DIR, "SEQ_" + DEFAULT_LOG_NAME))

    # show the pass num for seq15 of each try
    # multi_analyzer = MultiAnalyzer(MULTI_DIR)
    # multi_analyzer.exclude_debug = True
    # SEQ15_set = HDLBitsProbset("data/HDLBits/HDLBits_data_SEQ15.jsonl")
    # SEQ15_tasks = SEQ15_set.task_id_list
    # multi_analyzer.del_items(SEQ15_tasks, del_by_list=False)
    # multi_analyzer.renew_result_dict()
    # multi_analyzer.run()
    # print(multi_analyzer.access("total_num"))
    # print(multi_analyzer.access("fullpass_num_nodebug"))
    # print(sum(multi_analyzer.access("fullpass_num_nodebug")))
    # for task in multi_analyzer.result_dict.data:
    #     print(task["task_id"] + ": " + str(round(task["Eval2_pass_at_1"], 2)))
        
    # k_list = [1,5,10]
    # multi_analyzer = MultiAnalyzer(MULTI_DIR, k_list)
    # data_list = multi_analyzer.dictlists
    # CMB_num_list = []
    # for data in data_list:
    #     CMB_num = 0
    #     for i in data.data:
    #         if i.get("circuit_type", "NO data") == "CMB":
    #             CMB_num += 1
    #     CMB_num_list.append(CMB_num)
    # print(CMB_num_list)
    
    # k_list = [1,5,10]
    # multi_analyzer = MultiAnalyzer(MULTI_DIR, k_list)
    # # multi_analyzer.exclude_debug = True
    # multi_analyzer.messages += "\n#################### TOTAL ####################\n"
    # multi_analyzer.run()
    # multi_analyzer.save()
    # CMB_set = HDLBitsProbset("data/HDLBits/HDLBits_circuit_type.jsonl", filter_content={"circuit_type": "CMB"})
    # SEQ_set = HDLBitsProbset("data/HDLBits/HDLBits_circuit_type.jsonl", filter_content={"circuit_type": "SEQ"})
    # CMB_tasks = CMB_set.task_id_list
    # SEQ_tasks = SEQ_set.task_id_list
    # multi_analyzer_CMB = MultiAnalyzer(MULTI_DIR, k_list)
    # # multi_analyzer_CMB.exclude_debug = True
    # multi_analyzer_CMB.del_items(SEQ_tasks, del_by_list=True)
    # # print(multi_analyzer_CMB.access("total_num"))
    # multi_analyzer_CMB.messages += "\n#################### CMB ####################\n"
    # multi_analyzer_CMB.run()
    # multi_analyzer_CMB.save(os.path.join(DEFAULT_SAVING_DIR, "CMB_" + DEFAULT_LOG_NAME))
    # multi_analyzer_SEQ = MultiAnalyzer(MULTI_DIR, k_list)
    # # multi_analyzer_SEQ.exclude_debug = True
    # multi_analyzer_SEQ.del_items(CMB_tasks, del_by_list=True)
    # multi_analyzer_SEQ.messages += "\n#################### SEQ ####################\n"
    # multi_analyzer_SEQ.run()
    # multi_analyzer_SEQ.save(os.path.join(DEFAULT_SAVING_DIR, "SEQ_" + DEFAULT_LOG_NAME))

    # k_list = [1,3,5,10]
    # multi_analyzer = MultiAnalyzer(MULTI_DIR, k_list)
    # multi_analyzer.exclude_debug = True
    # multi_analyzer.messages += "\n#################### TOTAL ####################\n"
    # multi_analyzer.run()
    # multi_analyzer.save()
    # CMB_set = HDLBitsProbset("data/HDLBits/HDLBits_circuit_type.jsonl", filter_content={"circuit_type": "CMB"})
    # SEQ_set = HDLBitsProbset("data/HDLBits/HDLBits_circuit_type.jsonl", filter_content={"circuit_type": "SEQ"})
    # CMB_tasks = CMB_set.task_id_list
    # SEQ_tasks = SEQ_set.task_id_list
    # multi_analyzer_CMB = MultiAnalyzer(MULTI_DIR, k_list)
    # multi_analyzer_CMB.del_items(SEQ_tasks, del_by_list=True)
    # multi_analyzer_CMB.exclude_debug = True
    # multi_analyzer_CMB.messages += "\n#################### CMB ####################\n"
    # multi_analyzer_CMB.run()
    # multi_analyzer_CMB.save(os.path.join(DEFAULT_SAVING_DIR, "CMB_" + DEFAULT_LOG_NAME))
    # multi_analyzer_SEQ = MultiAnalyzer(MULTI_DIR, k_list)
    # multi_analyzer_SEQ.del_items(CMB_tasks, del_by_list=True)
    # multi_analyzer_SEQ.exclude_debug = True
    # multi_analyzer_SEQ.messages += "\n#################### SEQ ####################\n"
    # multi_analyzer_SEQ.run()
    # multi_analyzer_SEQ.save(os.path.join(DEFAULT_SAVING_DIR, "SEQ_" + DEFAULT_LOG_NAME))
                            

    # Chatbench_RunInfo = ls.load_json_dict(CHATBENCH_RUNINFO_PATH)
    # analyzer = Analyzer(Chatbench_RunInfo)


    # # task 2024/04/25 17:09:39, extract SEQ15 info from SEQ
    # Chatbench_RunInfo = ls.load_json_dict(CHATBENCH_RUNINFO_PATH)
    # seq15 = HDLBitsProbset("data/HDLBits/HDLBits_data_SEQ15.jsonl")
    # seq15_taskids = seq15.task_id_list
    # analyzer = Analyzer(Chatbench_RunInfo)
    # analyzer.del_items(seq15_taskids, False)
    # # analyzer.filter({"debug_iter_iv": 0})
    # analyzer.run()
    # with open(DEFAULT_LOG_PATH, "w") as f:
    #     f.write(analyzer.messages)
    #     # also, write the current time
    #     f.write("analysis time: %s\n" % (utils.get_time()))

    # # Chatbench_RunInfo = ls.load_json_dict(CHATBENCH_RUNINFO_PATH)
    # data_al = DataAnalyzer(CONFIBENCH_DATA_DIR)
    # # analyze the data
    # analyzer = data_al.analyzer
    # analyzer.draw_confibench_multi_tb_num_histogram()
    # analyzer.draw_confibench_valid_ratio_histogram()




    pass

def multi_exp_draw_confibench_histograms(multi_dir = MULTI_DIR):
    subdirs = os.listdir(multi_dir)
    multi_tb_nums = []
    multi_valid_ratios = []
    for subdir in subdirs:
        subdir_path = os.path.join(multi_dir, subdir)
        if os.path.isdir(subdir_path):
            data_al = DataAnalyzer(subdir_path)
            analyzer = data_al.analyzer
            


def regular_multiA_main():
    multi_analyzer = MultiAnalyzer(MULTI_DIR)
    multi_analyzer.run()
    multi_analyzer.save()

def regular_main():
    Chatbench_RunInfo = ls.load_json_dict(CHATBENCH_RUNINFO_PATH)
    # analyze the data
    analyzer = Analyzer(Chatbench_RunInfo)
    analyzer.run()
    # save the result to a txt file
    with open(DEFAULT_LOG_PATH, "w") as f:
        f.write(analyzer.messages)
        # also, write the current time
        f.write("analysis time: %s\n" % (utils.get_time()))

def analyze_subset(subset:str|HDLBitsProbset, runinfo_path, subset_name=""):
    """
    this function is used to only analyze a subset of the runinfo data
    - subset (only the task_ids are needed):
        - str: path of the subset
        - HDLBitsProbset: the subset
    - runinfo_path: path of the Chatbench_RunInfo.json
    - subset_name: the name of the subset
    """
    if isinstance(subset, str):
        # path, load the subset
        subset = HDLBitsProbset(subset)
    elif isinstance(subset, HDLBitsProbset):
        subset = subset
    else:
        raise TypeError("subset should be a path or a HDLBitsProbset")
    subset_tasks = subset.task_id_list
    analyzer = Analyzer(ls.load_json_dict(runinfo_path))
    analyzer.del_items(subset_tasks, False)
    analyzer.out_txt += f"\n#################### {subset_name} ####################\n"
    analyzer.run()
    with open(DEFAULT_LOG_PATH, "a") as f:
        f.write(analyzer.messages)
        f.write("analysis time: %s\n" % (utils.get_time()))

class Analyzer(HDLBitsProbset):
    def __init__(self, Chatbench_RunInfo, pricing_model="gpt-4o-2024-05-13"):
        super().__init__()
        self.data = Chatbench_RunInfo
        self.check_existance()
        self.pricing_model = pricing_model
        self.out_txt = ""
        self.loose_factor = LOOSE_FACTOR

    def run(self):
        self.out_txt += "\n########## Analyze of Chatbench_RunInfo ##########\n"

        self.out_txt += "\n#### pass numbers:\n"
        if self.Eval2b_exist:
            self.out_txt += "Eval2b: %d\n" % self.Eval2bpass_num
        self.out_txt += "Eval2 : %d\n" % self.fullpass_num
        self.out_txt += "Eval1 : %d\n" % self.Eval1pass_num
        self.out_txt += "Eval0 : %d\n" % self.Eval0pass_num
        self.out_txt += "total : %d " % self.total_num
        self.out_txt += "(Failed: %d)\n" % (self.total_num - self.Eval0pass_num)
        if self.reboot_times_exist:
            self.out_txt += "passed TB by autoline reboot action (from TB3_check): %d\n" % self.autoline_reboot_task_num
        if self.TB_corrected_exist:
            self.out_txt += "\npassed TB by functional corrector: %d\n" % self.corrected_num
        # self.out_txt += self.get_avg_debug_iter_on_sim_pass_with_debug()[-1]
        # self.out_txt += self.get_debug_failed_num()[-1]
        # self.out_txt += self.get_debug_total_pass_num()[-1]
        # self.out_txt += self.get_debug_sim_pass_num()[-1]

        self.out_txt += "\n#### tokens and cost:\n"
        # self.out_txt += "average prompt tokens: %d\naverage completion tokens: %d\n" % (self.prompt_tokens_num/self.total_num, self.completion_tokens_num/self.total_num)
        self.out_txt += "average prompt tokens: %d\n" % (self.prompt_tokens_num / self.total_num)
        self.out_txt += "average completion tokens: %d\n" % (self.completion_tokens_num / self.total_num)
        self.out_txt += "total cost: %.4f\n" % self.cost
        self.out_txt += "average cost: %.4f\n" % self.avg_cost

        self.out_txt += "\n#### time:\n"
        self.out_txt += "average time: %.2fs\n" % self.avg_time

        self.out_txt += "\n#### debug info table:\n"
        self.out_txt += self.get_debug_infotable()

        self.out_txt += "\n#### Eval2 ratio:\n"
        self.out_txt += self.get_eval2_ratio_each_problem()

        if self.Eval2b_exist:
            self.out_txt += "\n#### Eval2b ratio:\n"
            self.out_txt += self.get_eval2b_ratio_each_problem()


        # self.get_iv_runing_time_info()

        self.out_txt += "\nloose Eval2 pass metric applied: %s\n\n" % self.loose_factor

    def find_fake_eval0pass(self):
        self.filter({"sim_pass": 1})
        task_ids_fake_eval0pass = []
        for i in self.data:
            if i.get("Eval1_pass","NO data") == "NO data":
                task_ids_fake_eval0pass.append(i["task_id"])
        self.out_txt += "fake Eval0 pass: %d\n" % len(task_ids_fake_eval0pass)
        for i in task_ids_fake_eval0pass:
            self.out_txt += i + "\n"

    def check_existance(self):
        self.Eval2b_exist = False
        self.TB_corrected_exist = False
        self.reboot_times_exist = False
        for i in self.data:
            if "Eval2b_pass" in i.keys():
                self.Eval2b_exist = True
            if "TB_corrected" in i.keys():
                self.TB_corrected_exist = True
            if "reboot_times" in i.keys():
                self.reboot_times_exist = True
            if self.Eval2b_exist and self.TB_corrected_exist and self.reboot_times_exist:
                break

    # task
    def draw_Eval2_histogram(self, figurename="eval2_histogram.png"):
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')
        ratios = []
        for i in self.data:
            if self.Eval0_pass(i) and self.Eval1_pass(i):
                # get the numerical ratio
                ratio_str = i.get("Eval2_ratio", None)
                if ratio_str is None:
                    continue
                numerator, denominator = ratio_str.split("/")
                ratio = float(numerator) / float(denominator)
                ratios.append(ratio)
        # draw histogram of ratios, it will have 10 bars, 0~10%, 10~20%, ..., 90~100%
        plt.hist(ratios, bins=11, range=(0,1))
        # add grids
        plt.grid(True)
        # save to analysis/eval2_histogram.png
        plt.savefig(os.path.join(DEFAULT_SAVING_DIR, figurename))
        plt.close()

    @property
    def messages(self):
        return self.out_txt
    
    @property
    def total_num(self):
        if not hasattr(self, "_total_num"):
            self._total_num = len(self.data)
        return self._total_num
    
    @property
    def fullpass_num(self):
        if not hasattr(self, "_fullpass_num"):
            self._fullpass_num = 0
            for i in self.data:
                if self.Eval0_pass(i) and i.get("Eval1_pass",0) and self.Eval2_pass(i):
                    self._fullpass_num += 1
        return self._fullpass_num

    @property
    def fullpass_num_nodebug(self):
        if not hasattr(self, "_fullpass_num"):
            self._fullpass_num = 0
            for i in self.data:
                if self.Eval0_pass(i) and i.get("Eval1_pass",0) and self.Eval2_pass(i) and self.debug_iter(i) == 0:
                    self._fullpass_num += 1
        return self._fullpass_num
    
    @property
    def Eval2bpass_num(self):
        if not hasattr(self, "_Eval2bpass_num"):
            self._Eval2bpass_num = 0
            if self.Eval2b_exist:
                for i in self.data:
                    if self.Eval0_pass(i) and i.get("Eval1_pass",0) and i.get("Eval2b_pass",0):
                        self._Eval2bpass_num += 1
        return self._Eval2bpass_num

    @property
    def Eval0pass_num(self):
        if not hasattr(self, "_Eval0pass_num"):
            self._Eval0pass_num = 0
            for i in self.data:
                if self.Eval0_pass(i):
                    self._Eval0pass_num += 1
        return self._Eval0pass_num
    
    @property
    def Eval1pass_num(self):
        if not hasattr(self, "_Eval1pass_num"):
            self._Eval1pass_num = 0
            for i in self.data:
                if self.Eval0_pass(i) and i.get("Eval1_pass",0):
                    self._Eval1pass_num += 1
        return self._Eval1pass_num
    
    @property
    def corrected_num(self):
        if not hasattr(self, "_corrected_num"):
            self._corrected_num = 0
            if self.TB_corrected_exist:
                for i in self.data:
                    if i.get("TB_corrected",0) and self.Eval2_pass(i):
                        self._corrected_num += 1
        return self._corrected_num
    
    @property
    def autoline_reboot_task_num(self):
        if not hasattr(self, "_autoline_reboot_task_num"):
            self._autoline_reboot_task_num = 0
            if self.reboot_times_exist:
                for i in self.data:
                    if (i.get("reboot_times",0) > 0) and self.Eval2_pass(i):
                        self._autoline_reboot_task_num += 1
        return self._autoline_reboot_task_num

    @property
    def avg_time(self):
        if not hasattr(self, "_avg_time"):
            time_sum = 0
            for i in self.data:
                time_sum += i.get("time",0)
            self._avg_time = time_sum / len(self.data)
        return self._avg_time
        
    @property
    def tokens_num(self):
        if not hasattr(self, "_tokens_num"):
            prompt_tokens_sum = 0
            completion_tokens_sum = 0
            for i in self.data:
                prompt_tokens_sum += i.get("prompt_tokens",0)
                completion_tokens_sum += i.get("completion_tokens",0)
            self._prompt_tokens_num = prompt_tokens_sum
            self._completion_tokens_num = completion_tokens_sum
            self._tokens_num = prompt_tokens_sum + completion_tokens_sum
        return self._tokens_num
    
    @property
    def prompt_tokens_num(self):
        if not hasattr(self, "_prompt_tokens_num"):
            self.tokens_num
        return self._prompt_tokens_num
    
    @property
    def completion_tokens_num(self):
        if not hasattr(self, "_completion_tokens_num"):
            self.tokens_num
        return self._completion_tokens_num
    
    @property
    def avg_tokens(self):
        if not hasattr(self, "_avg_tokens"):
            self._avg_tokens = self.tokens_num / self.total_num
        return self._avg_tokens
    
    @property
    def cost(self):
        if not hasattr(self, "_cost"):
            self._cost = self.get_total_cost()
        return self._cost
    
    @property
    def avg_cost(self):
        if not hasattr(self, "_avg_cost"):
            self._avg_cost = self.cost / self.total_num
        return self._avg_cost
    
    def get_total_cost(self):
        """
        return the average cost of the data
        """
        prompt_cost_perk, completion_cost_perk = PRICING_MODELS[self.pricing_model]
        prompt_cost = self.prompt_tokens_num * prompt_cost_perk / 1000
        completion_cost = self.completion_tokens_num * completion_cost_perk / 1000
        total_cost = prompt_cost + completion_cost
        return total_cost
    
    def get_eval2_ratio_each_problem(self):
        """
        return the ratio of the second evaluation
        """
        txt_out = ""
        for i in self.data:
            if self.Eval0_pass(i) and i.get("Eval1_pass",0):
                task_id = i["task_id"]
                eval2_ratio = i.get("Eval2_ratio", "No Eval2 ratio data")
                txt_out += "%s: %s\n" % (task_id, eval2_ratio)
        return txt_out
    
    def get_eval2b_ratio_each_problem(self):
        """
        return the ratio of the second evaluation
        """
        txt_out = ""
        for i in self.data:
            if self.Eval2b_exist:
                if self.Eval0_pass(i) and i.get("Eval1_pass",0):
                    task_id = i["task_id"]
                    eval2_ratio = i.get("Eval2b_ratio", "No Eval2b ratio data")
                    txt_out += "%s: %s\n" % (task_id, eval2_ratio)
            else:
                txt_out = "No Eval2b data"
        return txt_out

    def get_debug_infotable(self):
        """
        return the debug info table:
                  | un-debugged | debugged | total |
        failed    |      -      |    2     |     2 |
        Eval0     |      3      |    5     |     8 |
        Eval1     |      2      |    2     |     4 |
        Eval2     |      1      |    0     |     1 |
        if have Eval2b:
        Eval2b    |      1      |    0     |     1 |
        """
        txt_out = ""
        # debugged but failed
        failed_debugged_num = 0
        failed_undebugged_num = 0
        Eval0_debugged_num, Eval1_debugged_num, Eval2_debugged_num, Eval2b_debugged_num = 0, 0, 0, 0
        Eval0_undebugged_num, Eval1_undebugged_num, Eval2_undebugged_num, Eval2b_undebugged_num = 0, 0, 0, 0
        if self.reboot_times_exist or self.TB_corrected_exist:
            mode = "funcdebug"
        else:
            mode = "syndebug"
        for i in self.data:
            if mode == "syndebug":
                debugged = (self.debug_iter(i) != 0)
            elif mode == "funcdebug":
                debugged = (i.get("reboot_times", 0) > 0 or (i.get("TB_corrected", False)))
            else:
                raise ValueError("mode should be 'syndebug' or 'funcdebug'")
            failed_debugged_num += 1 if not self.Eval0_pass(i) and debugged else 0
            failed_undebugged_num += 1 if not self.Eval0_pass(i) and (not debugged) else 0
            Eval0_debugged_num += 1 if self.Eval0_pass(i) and debugged else 0
            Eval0_undebugged_num += 1 if self.Eval0_pass(i) and (not debugged) else 0
            Eval1_debugged_num += 1 if self.Eval0_pass(i) and i.get("Eval1_pass", 0) and debugged else 0
            Eval1_undebugged_num += 1 if self.Eval0_pass(i) and i.get("Eval1_pass", 0) and (not debugged) else 0
            Eval2_debugged_num += 1 if self.Eval0_pass(i) and i.get("Eval1_pass", 0) and self.Eval2_pass(i) and debugged else 0
            Eval2_undebugged_num += 1 if self.Eval0_pass(i) and i.get("Eval1_pass", 0) and self.Eval2_pass(i) and (not debugged) else 0
            if self.Eval2b_exist:
                Eval2b_debugged_num += 1 if self.Eval0_pass(i) and i.get("Eval1_pass", 0) and self.Eval2b_pass(i) and debugged else 0
                Eval2b_undebugged_num += 1 if self.Eval0_pass(i) and i.get("Eval1_pass", 0) and self.Eval2b_pass(i) and (not debugged) else 0
        failed_num = failed_debugged_num + failed_undebugged_num
        Eval0_num = Eval0_debugged_num + Eval0_undebugged_num
        Eval1_num = Eval1_debugged_num + Eval1_undebugged_num
        Eval2_num = Eval2_debugged_num + Eval2_undebugged_num
        if self.Eval2b_exist:
            Eval2b_num = Eval2b_debugged_num + Eval2b_undebugged_num
        # make a table; each cell should have a width of 11
        txt_out += ("SYNTACTIC" if mode == "syndebug" else "FUNCTIONAL") + " debug info table:\n"
        txt_out += "(debugged here means " + ("syntactic debugging" if mode == "syndebug" else "functional debugging") + ")\n"
        if mode == "syndebug":
            txt_out += "         | un-synt-debugged | synt-debugged | total |\n"
        elif mode == "funcdebug":
            txt_out += "         | un-func-debugged | func-debugged | total |\n"
        txt_out += "failed   | %16d | %13d | %5d |\n" % (failed_undebugged_num, failed_debugged_num, failed_num)
        txt_out += "Eval0    | %16d | %13d | %5d |\n" % (Eval0_undebugged_num, Eval0_debugged_num, Eval0_num)
        txt_out += "Eval1    | %16d | %13d | %5d |\n" % (Eval1_undebugged_num, Eval1_debugged_num, Eval1_num)
        txt_out += "Eval2    | %16d | %13d | %5d |\n" % (Eval2_undebugged_num, Eval2_debugged_num, Eval2_num)
        if self.Eval2b_exist:
            txt_out += "Eval2b   | %16d | %13d | %5d |\n" % (Eval2b_undebugged_num, Eval2b_debugged_num, Eval2b_num)
        return txt_out

    def get_iv_runing_time_info(self):
        max_time = 0.0
        min_time = 0.0
        total_time = 0.0
        cnt = 0
        for i in self.data:
            if self.Eval0_pass(i):
                time = float(i.get("iv_runing_time", 0.0))
                if (time > max_time) or (max_time == 0.0):
                    max_time = time
                if (time < min_time) or (min_time == 0.0):
                    min_time = time
                total_time += time
                cnt += 1
        avg_time = total_time / cnt if cnt != 0 else 0.0                
        if cnt != 0:
            self.out_txt += "\n#### iv_runing_time info:\n"
            self.out_txt += "avg_time: %.2fs\n" % avg_time
            self.out_txt += "max_time: %.2fs\n" % max_time
            self.out_txt += "min_time: %.2fs\n" % min_time

    def Eval0_pass(self, data):
        if "Eval0_pass" in data.keys():
            return data["Eval0_pass"] # latest version
        elif "sim_pass" in data.keys():
            return data["sim_pass"] # old version
        else:
            return False

    def Eval1_pass(self, data):
        return data.get("Eval1_pass", False)
    
    def Eval2_pass(self, data):
        """check if one data pass the Eval 2"""
        # we use this to compensate special cases: m2014_q3
        if data["task_id"] == "m2014_q3":
            if data.get("Eval2_failed_mutant_idxes", []) == [3,4,7,8,9,10] or self.loose_Eval2_pass(data):
                return True
            else:
                return False
        # normal cases
        else:
            return self.loose_Eval2_pass(data)

    def Eval_score(self, data):
        if data.get("Eval_score", None) is not None:
            return data["Eval_score"]
        return self.scores_from_runinfo(data)

    @staticmethod
    def scores_from_runinfo(data:dict):
        """
        - Eval0 failed: -2; 
        - Eval0 passed but Eval1 failed: -1; 
        - Eval1 passed: 0~1 depending on the ratio of passed mutants in Eval2; """
        if not (data.get("Eval0_iv_pass", False) and data.get("Eval0_py_pass", False)):
            return -2.0
        elif not data.get("Eval1_pass", False):
            return -1.0
        else:
            eval2_ratio = data.get("Eval2_ratio", None)
            if eval2_ratio is not None:
                eval2_ratio = float(eval2_ratio.split("/")[0]) / float(eval2_ratio.split("/")[1])
            else:
                eval2_ratio = 0.0
            return eval2_ratio        
        
    def Eval0_scencheck_pass(self, data):
        return self.Eval0_pass(data) and data.get("checklist_worked", False)
    
    def Eval1_scencheck_pass(self, data):
        return self.Eval1_pass(data) and data.get("checklist_worked", False)
    
    def Eval2_scencheck_pass(self, data):
        return self.Eval2_pass(data) and data.get("checklist_worked", False)
    
    def Eval0_noscencheck_pass(self, data):
        return self.Eval0_pass(data) and (not data.get("checklist_worked", False))
    
    def Eval1_noscencheck_pass(self, data):
        return self.Eval1_pass(data) and (not data.get("checklist_worked", False))
    
    def Eval2_noscencheck_pass(self, data):
        return self.Eval2_pass(data) and (not data.get("checklist_worked", False))

    def Eval0_nodebug_pass(self, data):
        return (self.Eval0_pass(data)) and (self.debug_iter(data) == 0)

    def Eval1_nodebug_pass(self, data):
        return (self.Eval1_pass(data)) and (self.debug_iter(data) == 0)
    
    def Eval2_nodebug_pass(self, data):
        return (self.Eval2_pass(data)) and (self.debug_iter(data) == 0)

    def Eval2b_pass(self, data):
        """check if one data pass the Eval 2"""
        # we use this to compensate special cases: m2014_q3
        if data["task_id"] == "m2014_q3":
            if self.Eval2_pass(data):
                return True
            else:
                return False
        # normal cases
        else:
            return self.loose_Eval2b_pass(data)
        
    def debug_iter(self, data):
        if data.get("debug_iter", None) is not None:
            return data["debug_iter"]
        else:
            return data.get("debug_iter_iv", 0) + data.get("debug_iter_py", 0)
        
    def loose_Eval2_pass(self, data):
        """pass for 9/10, 8/10 and 4/5"""
        if data.get("Eval2_pass", False):
            return True
        ratio_str = data.get("Eval2_ratio", None)
        if ratio_str is None:
            return False
        numerator, denominator = ratio_str.split("/")
        numerator, denominator = int(numerator), int(denominator)
        # if int(numerator) + 1 >= int(denominator):
        if float(numerator) / float(denominator) >= self.loose_factor:
            return True
        else:
            return False
    
    def loose_Eval2b_pass(self, data):
        """pass for 9/10, 8/10 and 4/5"""
        if data.get("Eval2b_pass", False):
            return True
        ratio_str = data.get("Eval2b_ratio", None)
        if ratio_str is None:
            return False
        numerator, denominator = ratio_str.split("/")
        numerator, denominator = int(numerator), int(denominator)
        # if int(numerator) + 1 >= int(denominator):
        if float(numerator) / float(denominator) >= self.loose_factor:
            return True
        else:
            return False
        
    def draw_confibench_multi_tb_num_histogram(self):
        # draw histogram of tb_nums
        plt.hist(self.multi_tb_num_statistics, bins=9, range=(1,10), color="skyblue")
        plt.hist(self.multi_tb_num_pass_statistics, bins=9, range=(1,10), color="orange")
        plt.legend(["all", "pass"])
        plt.grid(True, which='both', axis='both', color='gray', linestyle='-', linewidth=0.5)
        plt.xlabel("number of sub-TBs in each task")
        plt.ylabel("number of tasks")
        plt.title("number of sub-TBs in each task")
        plt.savefig(os.path.join(DEFAULT_SAVING_DIR, "confibench_tb_num_histogram.png"))
        plt.close()

    @property
    def multi_tb_num_statistics(self):
        if hasattr(self, "_cache_multi_tb_num_statistics"):
            return self._cache_multi_tb_num_statistics
        tb_nums = []
        for data in self.data:
            # check data["multibench_info"], the number of data["multibench_info"][i][picked_as_final] == True
            tb_num = 0
            for i in data["multibench_info"]:
                if i["picked_as_final"]:
                    tb_num += 1
            tb_nums.append(tb_num)
        self._cache_multi_tb_num_statistics = tb_nums
        return tb_nums

    @property
    def multi_tb_num_pass_statistics(self):
        if hasattr(self, "_cache_multi_tb_num_pass_statistics"):
            return self._cache_multi_tb_num_pass_statistics
        tb_nums = []
        for data in self.data:
            # check data["multibench_info"], the number of data["multibench_info"][i][picked_as_final] == True
            if not self.Eval2_pass(data):
                continue
            tb_num = 0
            for i in data["multibench_info"]:
                if i["picked_as_final"]:
                    tb_num += 1
            tb_nums.append(tb_num)
        self._cache_multi_tb_num_pass_statistics = tb_nums
        return tb_nums


    def draw_confibench_valid_ratio_histogram(self):
        # draw histogram of tb_nums
        plt.hist(self.valid_ratio_statistics, bins=10, range=(0,1), color="skyblue")
        plt.hist(self.valid_ratio_pass_statistics, bins=10, range=(0,1), color="orange")
        plt.legend(["all", "pass"])
        plt.grid(True, which='both', axis='both', color='gray', linestyle='-', linewidth=0.5)
        plt.xlabel("valid ratio of each sub-TB")
        plt.ylabel("number of sub-TBs")
        plt.title("valid ratio of each sub-TB")
        plt.savefig(os.path.join(DEFAULT_SAVING_DIR, "confibench_valid_ratio_histogram.png"))
        plt.close()
        
    @property
    def valid_ratio_statistics(self):
        if hasattr(self, "_cache_valid_ratio_statistics"):
            return self._cache_valid_ratio_statistics
        valid_ratios = []
        for data in self.data:
            for i in data["multibench_info"]:
                if i["picked_as_final"]:
                    valid_ratios.append(i["valid_ratio"])
        self._cache_valid_ratio_statistics = valid_ratios
        return valid_ratios
    
    @property
    def valid_ratio_pass_statistics(self):
        if hasattr(self, "_cache_valid_ratio_pass_statistics"):
            return self._cache_valid_ratio_pass_statistics
        valid_ratios = []
        for data in self.data:
            if not self.Eval2_pass(data):
                continue
            for i in data["multibench_info"]:
                if i["picked_as_final"]:
                    valid_ratios.append(i["valid_ratio"])
        self._cache_valid_ratio_pass_statistics = valid_ratios
        return valid_ratios

class MultiAnalyzer(muti_dictlist):
    def __init__(self, group_dir:str=None, pass_at_k_kvalues = K_LIST):
        """
        group_dir: includes many subdirs, each subdir contains a Chatbench_RunInfo.json
        """
        super().__init__(id_key="task_id")
        self.runinfo_paths = []
        self.result = {} # include the final results
        self.pass_at_k_kvalues = pass_at_k_kvalues
        self.exclude_debug = False # this is uesd in baseline when analyzing the data without debug
        self.messages = ""
        self.group_dir = group_dir
        for subdir in os.listdir(group_dir):
            path_runinfo = os.path.join(group_dir, subdir, "Chatbench_RunInfo.json")
            if os.path.exists(path_runinfo):
                self.runinfo_paths.append(path_runinfo)
        for path in self.runinfo_paths:
            self.dictlists.append(Analyzer(ls.load_json_dict(path)))
        self.dictlists: list[Analyzer]
        # check if the values in self.num(list) are the same
        if not self.all_equal("num"):
            print(self.num)
            raise ValueError("The total_num of the data are not the same")

    @property
    def analyzers(self):
        return self.dictlists

    def run(self, Evals=["Eval0", "Eval1", "Eval2"]):
        num_tasks = self.dictlists[0].total_num
        pass_at = self.pass_at_k_kvalues
        for Eval_idx in Evals:
            for pass_at_k in pass_at:
                self.Evalx_ratio_passatk(Eval_idx, pass_at_k)
        self.messages += "\n########## Analyze of Chatbench_RunInfos ##########\n"
        self.messages += "\n#### basic info:\n"
        self.messages += "total number of tasks: %d\n" % self.dictlists[0].total_num
        self.messages += "sample numbers: %d\n" % len(self.dictlists)
        self.messages += "\n#### pass@k ratios:\n"
        for key, value in self.result.items():
            self.messages += "%s: %.2f%% (%.1f)\n" % (key, value*100, value*num_tasks)
        self.messages += "\nloose Eval2 pass metric applied: %s\n\n" % self.dictlists[0].loose_factor

    def save(self, path:str=None):
        if path is None:
            path = DEFAULT_LOG_PATH
        with open(path, "w") as f:
            f.write(self.messages)
            # also, write the current time
            f.write("analysis time: %s\n" % (utils.get_time()))

    def get_avg_tokens_one_task(self):
        self.prompt_tokens_num = 0
        self.completion_tokens_num = 0
        for analyzer in self.dictlists:
            self.prompt_tokens_num += analyzer.prompt_tokens_num
            self.completion_tokens_num += analyzer.completion_tokens_num
        self.avg_prompt_tokens = self.prompt_tokens_num / len(self.dictlists) / self.dictlists[0].total_num
        self.avg_completion_tokens = self.completion_tokens_num / len(self.dictlists) / self.dictlists[0].total_num
        self.messages += "average prompt tokens: %d\n" % self.avg_prompt_tokens
        self.messages += "average completion tokens: %d\n" % self.avg_completion_tokens

    def get_avg_pass_by_disc_and_corr(self):
        self.pass_by_corrected = 0.0
        self.pass_by_disc = 0.0
        for analyzer in self.dictlists:
            self.pass_by_corrected += analyzer.corrected_num
            self.pass_by_disc += analyzer.autoline_reboot_task_num
        self.pass_by_corrected /= len(self.dictlists)
        self.pass_by_disc /= len(self.dictlists)
        self.messages += "passed with functional corrector: %.1f\n" % self.pass_by_corrected
        self.messages += "passed with autoline reboot action: %.1f\n" % self.pass_by_disc

    def get_Eval_score_levelbar_chart(self):
        """
        levels: -2, -1, 0~0.4, 0.4~0.8, 0.8~1 (left included, right excluded unless it is the last one)
        """
        score_counter = {"-2": 0, "-1": 0, "0~0.4": 0, "0.4~0.8": 0, "0.8~1": 0}
        for analyzer in self.dictlists:
            for i in analyzer.data:
                score = analyzer.Eval_score(i)
                if score == -2:
                    score_counter["-2"] += 1
                elif score == -1:
                    score_counter["-1"] += 1
                elif score < 0.4:
                    score_counter["0~0.4"] += 1
                elif score < 0.8:
                    score_counter["0.4~0.8"] += 1
                else:
                    score_counter["0.8~1"] += 1
        self.messages += "\n#### Eval score level bar chart:\n"
        for key, value in score_counter.items():
            self.messages += "%s: %d\n" % (key, value)
        
    def draw_Evalscore_histogram(self, dir:str = DEFAULT_SAVING_DIR):
        fig_name = "Eval_score_histogram.png"
        scores = []
        for analyzer in self.dictlists:
            for i in analyzer.data:
                scores.append(analyzer.Eval_score(i))
        # draw histogram of scores
        matplotlib.use('Agg')
        plt.hist(scores, bins=33, range=(-2,1))
        plt.title("distribution of Eval score in %s" % self.group_dir)
        plt.ylabel("number of tasks")
        plt.xlabel("score")
        plt.grid(True, which='both', axis='both', color='lightgray', linestyle='-', linewidth=0.5)
        plt.figtext(0.5, 0.005, "the score is defined as follows: -2: Eval0 failed; -1: Eval0 passed but Eval1 failed; 0~1: Eval2 ratio", ha="center", fontsize=8)
        # save to analysis/eval2_histogram.png
        plt.savefig(os.path.join(dir, fig_name))
        plt.close()

    def renew_result_dict(self):
        self.result_dict = HDLBitsProbset()
        self.result_dict.create_empty_set_via_taskids(self.dictlists[0].task_id_list)

    def Evalx_ratio_passatk(self, Eval_idx="Eval0", pass_at:int=1):
        """
        return the ratio of the Eval0 pass under pass@k
        """
        # assert Eval_idx in ["Eval0", "Eval1", "Eval2", "Eval2b"], "Eval_idx should be one of Eval0, Eval1, Eval2, Eval2b"
        if not hasattr(Analyzer, Eval_idx + "_pass"):
            raise ValueError("The function %s_pass is not defined in Analyzer" % Eval_idx) 
        k = pass_at
        n = len(self.dictlists)
        Evalx_pass_at_k_total = 0
        # compute the pass ratio under pass@k for each task
        for task_id in self.dictlists[0].task_id_list:
            if hasattr(self, "result_dict"):
                task_result = self.result_dict.access_data_via_taskid(task_id)
            pass_num = 0
            for dictlist in self.dictlists:
                Evalx_pass_func = getattr(dictlist, "%s_pass"%Eval_idx)
                # if dictlist.access_data_via_taskid(task_id)["%s_pass"%Eval_idx]:
                if Evalx_pass_func(dictlist.access_data_via_taskid(task_id)):
                    if not (self.exclude_debug and dictlist.debug_iter(dictlist.access_data_via_taskid(task_id))):
                        # if exclude_debug is True and the task is debugged, we will not count it
                        pass_num += 1
            # data = self.result_set.access_data_via_taskid(task_id)
            pass_at_k = self.pass_at_k_under_n(n, k, pass_num)
            Evalx_pass_at_k_total += pass_at_k
            if hasattr(self, "result_dict"):
                task_result["%s_pass_num"%Eval_idx] = pass_num
                task_result["%s_pass_at_%d"%(Eval_idx, k)] = pass_at_k
        Evalx_pass_at_k_total /= self.dictlists[0].total_num
        self.result["%s_pass_at_%d" % (Eval_idx, k)] = Evalx_pass_at_k_total

    
    @staticmethod
    def pass_at_k_under_n(n:int, k:int, c:int):
        """
        - n: total number of samples
        - k: number of samples we want to pick
        - c: number of samples passed
        - output: pass@k under n
        - return the pass ratio under pass@k for n times; we have n samples, pass_num samples passed. Now we want to calculate the possibility that we pick k samples and at least one of them passed
        """
        return 1 - (math.comb(n-c, k) / math.comb(n, k))
    
class DataAnalyzer:
    def __init__(self, exp_dir, pricing_model="gpt-4o-2024-05-13"):
        self.exp_dir = exp_dir
        self.pricing_model = pricing_model
        self._get_data(exp_dir)
        self.analyzer = Analyzer(self.resultdata, pricing_model)
    
    def _get_data(self, exp_dir):
        self.resultdata = []
        taskdirs = os.listdir(exp_dir)
        for taskdir in taskdirs:
            taskdir_path = os.path.join(exp_dir, taskdir)
            if not os.path.isdir(taskdir_path):
                continue
            result_data = ls.load_json_dict(os.path.join(taskdir_path, "data.json"))
            self.resultdata.append(result_data)


def Eval2_histogram():
    """draw Eval2 histogram"""
    k_list = [1,5,10]
    multi_analyzer = MultiAnalyzer(MULTI_DIR, k_list)
    ratios = []
    for analyzer in multi_analyzer.dictlists:
        for i in analyzer.data:
            if analyzer.Eval0_pass(i) and analyzer.Eval1_pass(i):
                # get the numerical ratio
                ratio_str = i.get("Eval2_ratio", None)
                if ratio_str is None:
                    continue
                numerator, denominator = ratio_str.split("/")
                ratio = float(numerator) / float(denominator)
                ratios.append(ratio)
    # draw histogram of ratios, it will have 10 bars, 0~10%, 10~20%, ..., 90~100%
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')
    plt.hist(ratios, bins=10, range=(0,1))
    # title: distribution of Eval2 (Our work)
    plt.title("distribution of Eval2 (Baseline)")
    # y label is the number of tasks, tick is 10
    plt.ylabel("number of tasks")
    plt.yticks(range(0, 700, 50))
    # small grid so we can see the number of tasks, major grid, both axis. the grid color should be very light
    plt.grid(True, which='both', axis='both', color='lightgray', linestyle='-', linewidth=0.5)
    # x label is the ratio, tick is 10%
    plt.xlabel("ratio")
    plt.xticks([0.1 * i for i in range(11)])
    # save to analysis/eval2_histogram.png
    plt.savefig(os.path.join(DEFAULT_SAVING_DIR, "eval2_histogram_Baseline.png"))
    # save the ratios to out, it is grouped by 0.1. the first group will contain both 0 and 0.1
    # the format is csv
    with open(os.path.join(DEFAULT_SAVING_DIR, "eval2_ratios_Baseline.txt"), "w") as f:
        for i in range(11):
            ratio = 0.1 * i
            ratio_num = len([j for j in ratios if math.floor(j*10) == i])
            f.write("%.1f, %d\n" % (ratio, ratio_num))
    # export the original bin data
    with open(os.path.join(DEFAULT_SAVING_DIR, "eval2_ratios_bin_Baseline.txt"), "w") as f:
        for i in ratios:
            f.write("%.2f\n" % i)
    plt.close()

def task_eval2passtimes_analyze():
    multi_analyzer = MultiAnalyzer(MULTI_DIR)
    pass_taskids_list = []
    for analyzer in multi_analyzer.dictlists:
        # find the task_id that pass Eval2
        pass_taskids = []
        for data in analyzer.data:
            if analyzer.Eval2_pass(data):
                pass_taskids.append(data["task_id"])
        pass_taskids_list.append(pass_taskids)
    # find the idx of task "lemming3"
    idxs = []
    for idx, pass_taskids in enumerate(pass_taskids_list):
        if "countbcd" in pass_taskids:
            idxs.append(idx)
    print("countbcd passed at:")
    print(idxs)
    # calculate the pass times for each task_id
    # pass_times_dict = {}
    # for pass_taskids in pass_taskids_list:
    #     for task_id in pass_taskids:
    #         if task_id in pass_times_dict.keys():
    #             pass_times_dict[task_id] += 1
    #         else:
    #             pass_times_dict[task_id] = 1
    # circuit_type_data_path = "data/HDLBits/HDLBits_circuit_type.jsonl"
    # SEQ_task_ids = HDLBitsProbset(circuit_type_data_path, filter_content={"circuit_type": "SEQ"}).task_id_list
    # # remove tasks that are not seq and then print
    # seq_passed_tasks = []
    # for task_id in pass_times_dict.keys():
    #     if task_id in SEQ_task_ids:
    #         seq_passed_tasks.append(task_id)
    # # pick 5 most complex tasks according to complexity = 1*len(description) + 2*len(module_code)
    # HDLdata = HDLBitsProbset("data/HDLBits/HDLBits_data.jsonl", only_tasks=seq_passed_tasks)
    # HDLdata.data.sort(key=lambda x: 1*len(x["description"]) + 2*len(x["module_code"]), reverse=True)
    # # print the task_id and pass times of the 5 most complex tasks
    # for i in range(10):
    #     task_id = HDLdata.data[i]["task_id"]
    #     pass_times = pass_times_dict[task_id]
    #     print(task_id + ": " + str(pass_times))

if __name__ == "__main__":
    main()
# FULLEXP_no1_paths = [
#     "saves/1211~1217/Chatbench_RunInfo.json"
# ]


# def get_TCpass_num(data):
#     """
#     return the number of passed tasks
#     """
#     pass_num = 0
#     for i in data:
#         if i["TC_pass"]:
#             pass_num += 1
#     return pass_num

# def get_debugTCpass_num(data):
#     """
#     return the number of passed tasks with debug iter != 0
#     """
#     pass_num = 0
#     for i in data:
#         if i["TC_pass"] and self.debug_iter(i) != 0:
#             pass_num += 1
#     return pass_num

# def get_debugsimpass_num(data):
#     """
#     return the number of passed tasks with debug iter != 0
#     """
#     pass_num = 0
#     for i in data:
#         if self.Eval0_pass(i) and self.debug_iter(i) != 0:
#             pass_num += 1
#     return pass_num

# def get_average_debugiter_debugTCpass(data):
#     """
#     return the average debug iter of the passed with debug data
#     """
#     debug_iter_sum = 0
#     debug_iter_num = 0
#     for i in data:
#         if i["TC_pass"] and self.debug_iter(i) != 0:
#             debug_iter_sum += self.debug_iter(i)
#             debug_iter_num += 1
#     return debug_iter_sum / debug_iter_num

# def get_average_time(data):
#     """
#     return the average time of the data
#     """
#     time_sum = 0
#     for i in data:
#         time_sum += i["time"]
#     return time_sum / len(data)

# def get_num_of_onetime_simpass(data):
#     """
#     return the number of tasks that passed in the first run
#     """
#     pass_num = 0
#     for i in data:
#         if self.Eval0_pass(i) and self.debug_iter(i) == 0:
#             pass_num += 1
#     return pass_num


# def analyze_EXP1_main(json_file_list):
#     output_data_list = []
#     for json_file in json_file_list:
#         data = ls.load_json_dict(json_file)
#         output_data_list.extend(data)
#     analyze(output_data_list)

# def correct_exp_no1_main(json_file_list):
#     output_data_list = correct_exp_no1(json_file_list)
#     analyze(output_data_list)

# def analyze(output_data_list):
#     # show all of the above processed data
#     print("total number of tasks: %d" % (get_total_num(output_data_list)))
#     print("number of simpassed tasks: %d" % (get_simpass_num(output_data_list)))
#     print("number of allpassed tasks: %d" % (get_TCpass_num(output_data_list)))
#     print("TCpass percentage: %.2f%%" % (get_TCpass_num(output_data_list) / get_total_num(output_data_list) * 100))
#     print("number of debug_and_TCpass: %d" % (get_debugTCpass_num(output_data_list)))
#     print("number of debug_and_simpass: %d" % (get_debugsimpass_num(output_data_list)))
#     print("average debug iter of debug_and_TCpass: %.2f" % (get_average_debugiter_debugTCpass(output_data_list)))
#     print("average time: %.2fs" % (get_average_time(output_data_list)))
#     # save them to a txt file analyze_out.txt
#     with open("analyze_out.txt", "w") as f:
#         f.write("total number of tasks: %d\n" % (get_total_num(output_data_list)))
#         f.write("number of simpassed tasks: %d\n" % (get_simpass_num(output_data_list)))
#         f.write("number of allpassed tasks: %d\n" % (get_TCpass_num(output_data_list)))
#         f.write("TCpass percentage: %.2f%%\n" % (get_TCpass_num(output_data_list) / get_total_num(output_data_list) * 100))
#         f.write("number of debug_and_TCpass: %d\n" % (get_debugTCpass_num(output_data_list)))
#         f.write("number of debug_and_simpass: %d\n" % (get_debugsimpass_num(output_data_list)))
#         f.write("average debug iter of debug_and_TCpass: %.2f\n" % (get_average_debugiter_debugTCpass(output_data_list)))
#         f.write("average time: %.2fs\n" % (get_average_time(output_data_list)))
#         # also, write the current time
#         f.write("time: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))

# def correct_exp_no1(json_file_list):
#     new_results = []
#     for json_file in json_file_list:
#         data_dir = json_file[:json_file.rfind("/")+1]
#         results = ls.load_json_dict(json_file)
#         for prob_result in results:
#             prob_dir = data_dir + prob_result["task_id"] + "/"
#             if prob_result["debug_iter"] == 0:
#                 prob_last_run_info_path = prob_dir + "TBgen_codes/" + "run_info.txt"
#             else:
#                 prob_last_run_info_path = prob_dir + "debug_%s" % (prob_result["debug_iter"]) + "/" + "run_info.txt"
#             prob_last_run_info = ls.load_txt(prob_last_run_info_path)
#             # check if "All test cases passed" is in the last run info
#             if "test cases passed" in prob_last_run_info:
#                 prob_result["TC_pass"] = True
#             else:
#                 prob_result["TC_pass"] = False
#         new_results.extend(results)
#     ls.save_dict_json_form(new_results, "corrected_exp_no1.json")
#     return new_results

# if __name__ == "__main__":
#     # correct_exp_no1_main(FULLEXP_no1_paths)
#     analyze_EXP1_main(FULLEXP_no1_paths)
#     # main()