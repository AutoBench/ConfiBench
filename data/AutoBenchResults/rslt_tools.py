"""
Description :   some tools for the result operation
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/8/13 11:10:45
LastEdited  :   2024/8/13 11:50:11
"""

import sys
if __name__ == "__main__":
    sys.path.append(".")
from data.probset import HDLBitsProbset
import loader_saver as ls


EASE_PATH = "data/AutoBenchResults/pass_sum.json"

def check_ease_of_tasklist(tasklist:list[str]):
    """
    - check the ease of the tasklist
    - tasklist: list of task_id
    """
    ease_dict = ls.load_json_dict(EASE_PATH)
    ease_list = []
    for task_id in tasklist:
        ease_list.append(ease_dict[task_id])
        print(f"Task {task_id}: {ease_dict[task_id]}")
    print(tasklist)
    print(ease_list)
    return ease_dict 

if __name__ == "__main__":
    tasklist = ['fsm3comb', 'ece241_2013_q2', 'circuit4', 'lemmings1', 'review2015_fancytimer', 'm2014_q4d']
    check_ease_of_tasklist(tasklist)