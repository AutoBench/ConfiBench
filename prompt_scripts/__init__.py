"""
Description :   description
Author      :   Ruidi Qiu (r.qiu@tum.de)
Time        :   2024/3/23 11:30:00
LastEdited  :   2024/7/24 11:43:13
"""

from .base_script import BaseScript, BaseScriptStage
from .legacy.script_RTLchecker0306 import WF_RTLchecker0306
from .script_pychecker import WF_pychecker
from .script_directgen import WF_directgen
from .legacy.script_RTLmulticheckers import WF_RTLmulticheckers
from .legacy.script_test import WF_test
from .legacy.script_under_tuning import WF_undertuning
from .script_pychecker_CMB import WF_pychecker_CMB
from .legacy.script_pychecker_claude import WF_pychecker_claude
from .legacy.script_pychecker_20240403 import WF_pychecker as WF_pychecker_20240403

SCRIPTS_SELECTER = {
    "RTLchecker0306": WF_RTLchecker0306,
    "pychecker": WF_pychecker,
    "pychecker_CMB": WF_pychecker_CMB,
    "pychecker_0403": WF_pychecker_20240403,
    "directgen": WF_directgen,
    "RTLmulticheckers": WF_RTLmulticheckers,
    "test": WF_test, 
    "tuning": WF_undertuning, 
    "pychecker_claude": WF_pychecker_claude
}

def get_script(script_name:str) -> BaseScript:
    if script_name in SCRIPTS_SELECTER:
        return SCRIPTS_SELECTER[script_name]
    else:
        raise ValueError(f"script name {script_name} is not supported")