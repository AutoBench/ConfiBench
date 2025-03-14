"""
Description :   Automatic pipeline of Chatbench: from HDLBits problem to simulation
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2023/12/7 15:13:00
LastEdited  :   2024/8/16 13:37:31
autoline.py (c) 2023
"""

from autoline.TB_autoline import run_autoline

from autoline.TB1_gen import TaskTBgen
from autoline.TB2_syncheck import TaskTBsim
from autoline.TB3_funccheck import TaskTBcheck, TB_corrector, TB_discriminator
from autoline.TB4_eval import TaskTBeval



if __name__ == "__main__":
    raise RuntimeError("you cannot run autoline.py directly!")
    # probset = Probset("data/HDLBits/HDLBits_data.jsonl", "data/HDLBits/HDLBits_data_miniset_mutants.jsonl", "data/HDLBits/HDLBits_circuit_type.jsonl", exclude_tasks=['rule110'], filter_content={'circuit_type': 'SEQ'})
    # print(probset.num)
    