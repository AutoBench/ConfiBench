"""
Description :   The TB generation stage in the autoline. The main TB generation workflow is implemented in prompt_scriptws
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/7/24 11:27:21
LastEdited  :   2024/8/12 23:30:30
"""


from prompt_scripts import get_script, BaseScript
from loader_saver import log_localprefix

class TaskTBgen():
    # TODO: in the future use pythonized prompt scripts and this class to replace the old TaskTBgen
    """TBgen, in this class we generate tb by calling different python script according to stage_template"""
    def __init__(self, prob_data: dict, TBgen_prompt_script: str, task_dir: str, config):
        self.prob_data = prob_data
        self.prompt_script_name = TBgen_prompt_script
        self.task_dir = task_dir
        self.config = config
        WorkFlowClass = get_script(TBgen_prompt_script)
        self.workflow = WorkFlowClass(
            prob_data = prob_data,
            task_dir = task_dir,
            config = config
        )

    @log_localprefix("TBgen")
    def run(self):
        self.workflow()

    @property
    def scenario_num(self):
        return self.get_wf_attr("scenario_num")
        
    @property
    def scenario_dict(self):
        return self.get_wf_attr("scenario_dict")
        
    def get_wf_attr(self, attr_name:str):
        if hasattr(self.workflow, attr_name):
            return getattr(self.workflow, attr_name)
        else:
            return None