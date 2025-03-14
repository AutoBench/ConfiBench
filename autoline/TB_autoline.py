"""
Description :   The main function of autoline, originally the first part of autoline.py in AutoBench 1.0
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/7/24 11:44:15
LastEdited  :   2025/3/14 23:53:04
"""
import os
import analyze as al
import loader_saver as ls
import confidence as cf
import copy
import concurrent.futures
import queue
import threading
from config import Config
from loader_saver import save_dict_json_form, log_localprefix
from data.probset import HDLBitsProbset
from loader_saver import autologger as logger
from utils.utils import Timer
from autoline.TB1_gen import TaskTBgen
from autoline.TB2_syncheck import TaskTBsim
from autoline.TB3_funccheck import TaskTBcheck
from autoline.TB4_eval import TaskTBeval
from prompt_scripts import BaseScript
from LLM_call import llm_manager


def run_autoline():
    # load config
    config = Config()
    autoline = AutoLine(config)
    autoline()

class AutoLine():
    """the class of the autoline"""
    def __init__(self, config: Config):
        self.config = config
        self.logger = logger
        self.logger.assert_(config.get_item("autoline", "promptscript") is not None, "config.autoline.promptscript is None, please check the config file.")
        self.load_data()
        # set run info
        # self.run_info_path = config.save.root + "Chatbench_RunInfo.json"
        self.run_info_path = os.path.join(config.save.root, "Chatbench_RunInfo.json")
        self.run_info = []
        self.analyzer_en = (config.autoline.onlyrun is None) or (config.autoline.onlyrun == "TBgensimeval") # only run the analyzer when not in the onlyrun mode (partial run)

    def run(self):
        for idx, probdata_single in enumerate(self.probset.data):
            task_id = probdata_single["task_id"]
            self.logger.info("")
            self.logger.info("######################### task %d/%d [%s] #########################" % (idx+1, self.probset.num, task_id))
            # run_info_single = pipeline_one_prob(probdata_single, self.config)
            one_task = AutoLine_Task(probdata_single, self.config)
            run_info_single = one_task.run()
            self.run_info.append(run_info_single)
            # save run info: (write to file every iteration and will overwrite the previous one)
            save_dict_json_form(self.run_info, self.run_info_path)
        if self.analyzer_en:
            self.run_analyzer()

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)
        
    def load_data(self):
        cfg_probset = self.config.autoline.probset
        self.probset = HDLBitsProbset()
        self.probset.load_by_config(cfg_probset)

    def run_analyzer(self):
        analyzer = al.Analyzer(self.run_info, self.config.gpt.model)
        analyzer.run()
        logger.info(analyzer.messages)



class AutoLine_Task():
    def __init__(self, prob_data:dict, config:Config):
        # config:
        self.config = config
        # probdata:
        self.prob_data = prob_data
        self.main_model = self.config.gpt.model # The main llm model used in the autoline (generation, correction...)
        self.task_id = prob_data["task_id"]
        self.task_NO = prob_data["task_number"]
        self.prob_description = prob_data["description"]
        self.header = prob_data["header"]
        self.DUT_golden = prob_data['module_code']
        self.TB_golden = prob_data.get("testbench", None)
        self.mutant_list = prob_data.get("mutants", None)
        self.rtlgen_list = prob_data.get('llmgen_RTL', None)
        self.rtlgen_model = self.config.gpt.rtlgen_model # if llmgen_list is none, this will be used
        self.rtl_num = self.config.autoline.TBcheck.rtl_num # will be covered if llmgen_list is not None
        # system config:
        # self.task_dir = self.config.save.root + self.task_id + "/"
        self.task_dir = os.path.join(self.config.save.root, self.task_id)
        self.working_dir = self.task_dir
        os.makedirs(self.task_dir, exist_ok=True)
        self.update_desc = config.autoline.update_desc
        self.error_interuption = config.autoline.error_interruption # for debug'
        self.save_codes = config.autoline.save_finalcodes
        self.save_compile = self.config.autoline.save_compile # save the compiling codes in TBcheck and TBeval or not.
        # TBgen paras:
        self.TBgen_prompt_script = config.autoline.promptscript
        self.circuit_type = None
        self.scenario_dict = None
        self.scenario_num = None
        self.checklist_worked = None
        # TBcheck paras:
        self.TBcheck_correct_max = self.config.autoline.TBcheck.correct_max
        self.iter_max = config.autoline.itermax
        self.discrim_mode = config.autoline.TBcheck.discrim_mode
        self.correct_mode = config.autoline.TBcheck.correct_mode
        self.rtl_compens_en = config.autoline.TBcheck.rtl_compens_en
        self.rtl_compens_max_iter = config.autoline.TBcheck.rtl_compens_max_iter
        # stages:
        self.TBgen_manager:TaskTBgen = None
        self.TBgen:BaseScript = None
        self.TBsim:TaskTBsim = None
        self.TBcheck:TaskTBcheck = None
        self.TBeval:TaskTBeval = None
        self.stage_now = "initialization"
        # dynamic values:
        self.autoline_iter_now = 0
        self.next_action = None
        self.TB_code_v = None
        self.TB_code_py = None
        self.RSmatrix = None # the last scenario_matrix in TB3_funccheck
        self.scen_mask = None
        self.syntax_error = False
        self.multibench_info:list[dict] = [] # each element includes TB_code_v, TB_code_py, scen_num, RSmatrix, scen_mask, iter_id (from 1), valid_ratio
        # results:
        self.incomplete_running = True
        self.full_pass = False
        self.TB_corrected = False
        self.run_info = {}
        self.run_info_short = {}
        self.TBcheck_rtl_newly_gen_num = 0 # in autoline, "funccheck" = "TBcheck"
        self.op_record = [] # will record the order of each stage, for example: ["gen", "syncheck", "funccheck", "gen", "syncheck", "funccheck", "eval"]
        self.funccheck_op_record = []
        self.funccheck_iters = []
        self.scen_mask_worked = False
        # confidence:
        self.confidence_config = self.config.confibench
        self.confidence_en = self.confidence_config.en
        if self.confidence_en:
            self.confidencer = cf.Confidence(self.confidence_config)
        # multibench: (valid only when confidence_en is True)
        self.multibench_en = self.confidence_config.multibench.en and self.confidence_en
        self.multibench_min_tb = self.confidence_config.multibench.min_tb
        self.multibench_min_ratio = self.confidence_config.multibench.min_ratio
        self.sum_valid_ratio = 0.0
        # save data:
        self.save_data_en = self.config.autoline.save_data # will save all the data, including the prob_data, run_info, codes and RSmatrix into a json file
        # renew current section of llm_manager and logger
        llm_manager.new_section()
        logger.set_temp_log()

    def run(self):
        """
        The main function of running the autoline for one problem
        """
        with log_localprefix(self.task_id):
            self.run_stages()
            self.runinfo_update()
            if self.save_codes and not self.multibench_en:
                self.save_TB_codes()
        return self.run_info

    @log_localprefix("TBgen")
    def run_TBgen(self, subdir:str=None):
        # TODO: export the circuit type and scenario number
        self.op_record.append("gen")
        working_dir = os.path.join(self.task_dir, subdir) if subdir is not None else self.task_dir
        self.stage_now = "TBgen"
        self.TBgen_manager = TaskTBgen(self.prob_data, self.TBgen_prompt_script, working_dir, self.config)
        self.TBgen = self.TBgen_manager.workflow
        self.TBgen()
        self.TB_code_v = self.TBgen.get_attr("TB_code_v")
        self.TB_code_py = self.TBgen.get_attr("TB_code_py")
        self.scenario_dict = self.TBgen.get_attr("scenario_dict")
        self.scenario_num = self.TBgen.get_attr("scenario_num")
        self.circuit_type = self.TBgen.get_attr("circuit_type")
        self.checklist_worked = self.TBgen.get_attr("checklist_worked")
        self.incomplete_running = True
        self._blank_log()

    @log_localprefix("TBsim")
    def run_TBsim(self, subdir:str=None):
        self.op_record.append("syncheck")
        working_dir = os.path.join(self.task_dir, subdir) if subdir is not None else self.task_dir
        self.stage_now = "TBsim"
        self.TBsim = TaskTBsim(
            self.TBgen, 
            self.TBgen.TB_code, 
            self.header, 
            working_dir, 
            self.task_id, 
            self.config
        )
        self.TBsim.run()
        self.TB_code_v = self.TBsim.TB_code_now
        self.TB_code_py = self.TBsim.PY_code_now
        self._blank_log()

    @log_localprefix("TBcheck")
    def run_TBcheck(self, subdir:str=None):
        # confidence related operations are in this stage
        self.op_record.append("funccheck")
        working_dir = os.path.join(self.task_dir, subdir) if subdir is not None else self.task_dir
        self.stage_now = "TBcheck"
        self.TBcheck = TaskTBcheck(
            task_dir = working_dir, 
            task_id = self.task_id, 
            description = self.prob_description, 
            module_header = self.header, 
            TB_code_v = self.TB_code_v,
            TB_code_py = self.TB_code_py,
            rtl_list = self.rtlgen_list,
            rtl_num = self.rtl_num,
            scenario_num = self.scenario_num,
            correct_max = self.TBcheck_correct_max,
            runfiles_save=self.save_compile,
            discriminator_mode=self.discrim_mode,
            corrector_mode=self.correct_mode,
            circuit_type=self.circuit_type,
            rtl_compens_en=self.rtl_compens_en,
            rtl_compens_max_iter=self.rtl_compens_max_iter,
            main_model = self.main_model,
            rtlgen_model = self.rtlgen_model,
            desc_improve=self.update_desc
        )
        self.rtlgen_list = self.TBcheck.rtl_list
        self.TBcheck.run()
        self.TB_code_v = self.TBcheck.TB_code_v
        self.TB_code_py = self.TBcheck.TB_code_py
        self.TB_corrected = self.TBcheck.corrected
        self.RSmatrix = self.TBcheck.scenario_matrix
        self.syntax_error = self.TBcheck.TB_syntax_error
        if self.confidence_en and not self.syntax_error:
            self.get_scen_mask()
            if self.confidence_config.save_fig:
                self.confidencer.draw_conf_confbool_lists(self.confidence, self.scen_mask, os.path.join(working_dir, "confidence.png"))
        if self.syntax_error:
            with open(os.path.join(working_dir, "syntax_error.txt"), "w") as f:
                f.write("syntax error in the result TB code from this TBcheck stage")
        self.funccheck_op_record.append(self.TBcheck.op_record)
        self.funccheck_iters.append(self.TBcheck.iter_now)
        self.TBcheck_rtl_newly_gen_num += self.TBcheck.rtl_newly_gen_num
        self.next_action = self.TBcheck.next_action
        if self.update_desc:
            self.prob_data['description'] = self.TBcheck.update_description()
            self.prob_description = self.prob_data['description']
        self._blank_log()

    @log_localprefix("TBeval")
    def run_TBeval(self, subdir:str=None):
        # get the final multibench info according to the valid_ratio
        self.gen_multibench_final()
        self.op_record.append("eval")
        working_dir = os.path.join(self.task_dir, subdir) if subdir is not None else self.task_dir
        self.stage_now = "TBeval"
        self.TBeval = TaskTBeval(
            self.task_id, 
            working_dir, 
            TB_gen=self.TB_code_v, 
            TB_golden=self.TB_golden, 
            DUT_golden=self.DUT_golden, 
            DUT_mutant_list=self.mutant_list, 
            DUT_gptgen_list=None, 
            pychecker_en=self.TBsim.pychecker_en, 
            pychecker_code=self.TB_code_py,
            runfiles_save=self.save_compile,
            scen_mask = self.scen_mask,
            multibench_en = self.multibench_en,
            multibench_info_final = self.multibench_info_final
        )
        # attention: the rtls in DUT_gptgen_list are not the same as the rtls used in TBcheck, so currently we just block this feature
        try:
            self.TBeval.run()
        except Exception as e:
            logger.failed("error when running TBeval, the autoline for this task stopped. error message: %s"%(str(e)))
            self.incomplete_running = True
        self._blank_log()

    def update_multibench(self):
        # this is right after the TBcheck stage
        if self.multibench_en and (not self.syntax_error) and (self.RSmatrix is not None):
            self.multibench_info.append({
                "iter_id": self.autoline_iter_now+1,
                "scen_num": self.scenario_num,
                "scen_mask": self.scen_mask,
                "valid_ratio": sum(self.scen_mask) / self.scenario_num, # scenario_num === len(scen_mask)
                "TB_code_v": self.TB_code_v,
                "TB_code_py": self.TB_code_py,
                "RSmatrix": self.RSmatrix,
                "picked_as_final": False # will be updated in the final stage
            })
            self.sum_valid_ratio += self.multibench_info[-1]["valid_ratio"]
            logger.info("multibench info updated: iter_id - %d, valid_ratio - %.2f; total ratio / min required - %.2f/%.2f"%(self.autoline_iter_now+1, self.multibench_info[-1]["valid_ratio"], self.sum_valid_ratio, self.multibench_min_ratio))

    def gen_multibench_final(self):
        # step1 reordering the multibench_info according to the valid_ratio, the first one is the best
        self.multibench_info = sorted(self.multibench_info, key=lambda x: x["valid_ratio"], reverse=True)
        # step2 get the final TB code, from the first one to the one that make the total valid_ratio >= min_ratio 
        self.multibench_info_final = []
        valid_ratio_sum = 0
        for info in self.multibench_info:
            info["picked_as_final"] = True
            self.multibench_info_final.append(info)
            valid_ratio_sum += info["valid_ratio"]
            if valid_ratio_sum >= self.multibench_min_ratio:
                break

    def run_stages(self):
        with Timer(print_en=False) as self.running_time:
            if not self.error_interuption:
                self.run_stages_core()
            else:
                try:
                    self.run_stages_core()
                except Exception as e:
                    self.incomplete_running = True
                    logger.error("error when running %s, the autoline for this task stopped. error message: %s"%(self.stage_now, str(e)))
                    if self.error_interuption:
                        # if True, stop the pipeline
                        raise e
                self.incomplete_running = False
                
    def run_stages_core(self):
        match self.config.autoline.onlyrun:
            case "TBgen":
                self.run_TBgen()
            case "TBgensim": 
                self.run_TBgen()
                self.run_TBsim()
            # case _: # default, run all
            case "TBgensimeval":
                try:
                    self.run_TBgen("1_TBgen")
                    self.run_TBsim("2_TBsim")
                    self.run_TBeval("3_TBeval")
                except Exception as e:
                    self.incomplete_running = True
                    logger.error("error when running %s, the autoline for this task stopped. error message: %s"%(self.stage_now, str(e)))
                else:
                    self.incomplete_running = False
            case _: # default, run all
                for i in range(self.iter_max):
                    self.autoline_iter_now = i
                    try: 
                        self.run_TBgen(f"{i+1}_1_TBgen")
                        self.run_TBsim(f"{i+1}_2_TBsim")
                        self.run_TBcheck(f"{i+1}_3_TBcheck")
                        self.update_multibench()
                    except Exception as e:
                        logger.error(f"error when running {self.stage_now}, current pipeline iter: {i+1}, will {"REBOOT" if i<self.iter_max-1 else "go to NEXT STAGE"}. error message: {str(e)}")
                        self.next_action = "reboot"
                        continue
                    match self.next_action:
                        case "pass":
                            if self.multibench_en:
                                # confibench path
                                if self.sum_valid_ratio < self.multibench_min_ratio:
                                    logger.info("min ratio (%.2f) not satisfied, will reboot and collect more testbenches"%(self.multibench_min_ratio))
                                    continue
                                elif len(self.multibench_info) < self.multibench_min_tb:
                                    logger.info("min iter num (%d) not satisfied, will reboot and collect more testbenches"%(self.multibench_min_tb))
                                    continue
                                else:
                                    break
                            else:
                                # correctbench path
                                break
                        case "reboot":
                            continue
                try:
                    self.run_TBeval(f"{self.autoline_iter_now+1}_4_TBeval")
                except Exception as e:
                    self.incomplete_running = True
                    logger.error("error when running %s, the autoline for this task stopped. error message: %s"%(self.stage_now, str(e)))

    def runinfo_update(self):
        ### general
        self.run_info = {
            "task_id": self.task_id,
            "task_number": self.task_NO,
            "time": round(self.running_time.interval, 2),
            "prompt_tokens": llm_manager.tokens_in_section,
            "completion_tokens": llm_manager.tokens_out_section,
            "token_cost": llm_manager.cost_section,
            "ERROR(incomplete)": self.incomplete_running,
            "op_record": self.op_record,
            "reboot_times": self.autoline_iter_now,
            "max_iter": self.iter_max
        }
        # token and cost from llm_manager
        
        # TBgen
        if self.TBgen is not None:
            # self.run_info["prompt_tokens"] += self.TBgen.tokens["prompt"]
            # self.run_info["completion_tokens"] += self.TBgen.tokens["completion"]
            self.run_info["circuit_type"] = self.circuit_type
            if not self.multibench_en:
                self.run_info["checklist_worked"] = self.checklist_worked
                self.run_info["scenario_num"] = self.scenario_num
        # TBsim
        if self.TBsim is not None:
            # self.run_info["prompt_tokens"] += self.TBsim.tokens["prompt"]
            # self.run_info["completion_tokens"] += self.TBsim.tokens["completion"]
            self.run_info.update({
                "Eval0_pass": self.TBsim.Eval0_pass,
                "Eval0_iv_pass": self.TBsim.sim_pass,
                "debug_iter_iv": self.TBsim.debug_iter_iv_now,
                "iv_runing_time": self.TBsim.iv_runing_time
            })
            if self.TBsim.pychecker_en:
                self.run_info.update({
                    "Eval0_py_pass": self.TBsim.py_pass,
                    "debug_iter_py": self.TBsim.debug_iter_py_now,
                    "py_runing_time": self.TBsim.py_runing_time
                })
            # complementing by multibench
            if self.TBcheck is not None:
                self.run_info["debug_iter_iv"] = "N/A"
                self.run_info["iv_runing_time"] = "N/A"
                self.run_info["debug_iter_py"] = "N/A"
                self.run_info["py_runing_time"] = "N/A"
            if self.multibench_en:
                self.run_info["Eval0_pass"] = len(self.multibench_info_final) > 0
                self.run_info["Eval0_iv_pass"] = "N/A"
                self.run_info["Eval0_py_pass"] = "N/A"
        # TODO: TBcheck runinfo update
        if self.TBcheck is not None:
            self.run_info.update({
                "TB_corrected": self.TB_corrected,
                "TBcheck_oprecord": self.funccheck_op_record,
                "rtl_num_newly_gen": self.TBcheck_rtl_newly_gen_num
            })
        # confidence and multibench
        if self.confidence_en and not self.multibench_en:
            self.run_info.update({
                "confidence": self.confidence,
                "scen_mask": self.scen_mask,
                "scen_mask_worked": self.scen_mask_worked
            })
        if self.multibench_en:
            self.run_info.update({
                "multibench_iter_ids": [info["iter_id"] for info in self.multibench_info_final],
                "multibench_valid_ratios": [info["valid_ratio"] for info in self.multibench_info_final]
            })
        # TBeval
        if self.TBeval is not None:
            if self.TBeval.Eval1_exist:
                self.run_info.update({"Eval1_pass": self.TBeval.Eval1_pass})
            if self.TBeval.Eval2_exist:
                self.run_info.update({
                    "Eval2_pass": self.TBeval.Eval2_pass,
                    "Eval2_ratio": "%d/%d"%(len(self.TBeval.Eval2_passed_mutant_idx), len(self.prob_data['mutants'])),
                    "Eval2_failed_mutant_idxes": self.TBeval.Eval2_failed_mutant_idx
                })
            if self.TBeval.Eval2b_exist:
                self.run_info.update({
                    "Eval2b_pass": self.TBeval.Eval2b_pass,
                    "Eval2b_ratio": "%d/%d"%(len(self.TBeval.Eval2b_passed_mutant_idx), len(self.prob_data['gptgen_RTL'])),
                    "Eval2b_failed_mutant_idxes": self.TBeval.Eval2b_failed_mutant_idx
                })
        # full pass
        if not self.incomplete_running:
            self.full_pass = self.TBsim.sim_pass and self.TBeval.Eval1_pass and self.TBeval.Eval2_pass
            self.run_info.update({
                "full_pass": self.full_pass
            })
        save_dict_json_form(self.run_info, os.path.join(self.task_dir, "run_info.json"))

        ### short run info 
        if "Eval2_ratio" in self.run_info.keys():
            eval_progress = "Eval2 - " + self.run_info["Eval2_ratio"]
        elif "Eval1_pass" in self.run_info.keys() and self.run_info["Eval1_pass"]:
            eval_progress = "Eval1 - passed"
        elif "Eval0_pass" in self.run_info.keys() and self.run_info["Eval0_pass"]:
            eval_progress = "Eval1 - failed"
        elif "Eval0_pass" in self.run_info.keys() and not self.run_info["Eval0_pass"]:
            eval_progress = "Eval0 - failed"
        else:
            eval_progress = "Eval0 - not found"
        self.run_info_short = {
            "task_id": self.run_info.get("task_id", None),
            "eval_progress": eval_progress,
            "TB_corrected": self.run_info.get("TB_corrected", None),
            "reboot_times": self.run_info.get("reboot_times", None),
            "time": self.run_info.get("time", None),
            "cost": self.run_info.get("token_cost", None),
        }
        if self.confidence_en:
            self.run_info_short.update({
                "scen_mask_worked": self.scen_mask_worked,
            })
        if self.multibench_en:
            self.run_info_short.update({
                "multibench_iter_ids": [info["iter_id"] for info in self.multibench_info_final],
                "multibench_valid_ratios": [info["valid_ratio"] for info in self.multibench_info_final]
            })
        save_dict_json_form(self.run_info_short, os.path.join(self.task_dir, "run_info_short.json"))

        ### data
        if self.save_data_en:
            self.save_data = copy.deepcopy(self.run_info)
            self.save_data.update(self.prob_data)
            if not self.multibench_en:
                self.save_data.update({
                    "TB_code_v": self.TB_code_v,
                    "TB_code_py": self.TB_code_py
                })
                if self.TBcheck is not None:
                    self.save_data.update({
                        "RSmatrix": self.RSmatrix.tolist()
                    })
                if self.confidence_en:
                    self.save_data.update({
                        "confidence": self.confidence,
                        "scen_mask": self.scen_mask
                    })
            else:
                for info in self.multibench_info:
                    info["RSmatrix"] = info["RSmatrix"].tolist()
                self.save_data.update({
                    "multibench_info": self.multibench_info
                })
            save_dict_json_form(self.save_data, os.path.join(self.task_dir, "data.json"))

        # run log
        running_log = logger.reset_temp_log()
        tasklog_path = os.path.join(self.task_dir, "task_log.log")
        os.makedirs(os.path.dirname(tasklog_path), exist_ok=True)
        with open(tasklog_path, "w") as f:
            f.write(running_log)
        
        return self.run_info
    
    def save_TB_codes(self):
        save_dir = self.task_dir
        ls.save_code(self.TB_code_v if isinstance(self.TB_code_v, str) else "// TB code (Verilog) unavailable", os.path.join(save_dir, "final_TB.v"))
        ls.save_code(self.TB_code_py if isinstance(self.TB_code_py, str) else "## TB code (Python) unavailable", os.path.join(save_dir, "final_TB.py"))

    def get_scen_mask(self):
        # we use confidencer to first generate scenario confidence, then use the confidence to generate the mask
        logger.assert_(self.RSmatrix is not None, "confidence is not applicable since last_RSmatrix is None") 
        self.confidence = self.confidencer.conf_gen(self.RSmatrix, self.scenario_num)
        self.scen_mask = self.confidencer.conf_bool_gen(self.confidence) # use conf_bool as the mask
        logger.info(f"scenario mask updated: scenario confidence - {[round(conf, 2) for conf in self.confidence]}, scenario mask - {self.scen_mask}")
        
    @staticmethod
    def _blank_log():
        if len(logger.logline_prefix_list) > 0:
            temp_log_prefix = logger.pop_prefix()
            logger.info("")
            logger.set_prefix(temp_log_prefix)
        else:
            logger.info("")

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)
