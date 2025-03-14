"""
Description :   This module contains all functions related to loading and saving (except config loading).
Author      :   Ruidi Qiu (ruidi.qiu@tum.de)
Time        :   2023/11/28 14:03:56
LastEdited  :   2025/2/24 22:04:10
"""

import os
import sys
import inspect
from config.config import Dict
import config as cfg
from config import Config
# import matplotlib.pyplot as plt
import yaml
import json
from io import StringIO
from loguru import logger as logurulogger
from utils.utils import print_time, Timer, str_list

ORIGINAL_RUN_PATH = os.getcwd()

########################## yaml/json utils ############################
def load_yaml_dict(path: str):
    with open(path, 'rb') as f:
        yaml_dict = yaml.safe_load(f)
    return yaml_dict

def load_json_dict(path: str):
    with open(path, 'r') as f:
        json_dict = json.load(f)
    return json_dict

def save_dict_json_form(json_dict, path: str):
    with open(path, 'w') as f:
        json.dump(json_dict, f, indent=4)

def load_txt(path: str):
    with open(path, 'r') as f:
        txt = f.read()
    return txt

# jsonl related:
def load_json_lines(path: str):
    with open(path, 'r') as f:
        data = [json.loads(line) for line in f]
    return data

def save_json_lines(data, path: str):
    with open(path, 'w') as f:
        for line in data:
            json.dump(line, f)
            f.write('\n')

def find_line_jsonl(id_or_number, data):
    """
    quickly find the line in data by task_id or task_number
    """
    if isinstance(id_or_number, str):
        for line in data:
            if line["task_id"] == id_or_number:
                return line
    elif isinstance(id_or_number, int):
        for line in data:
            if line["task_number"] == id_or_number:
                return line

########################## set save path ############################
def save_path_setting(config, save_type, custom_name=''):
    '''support log/data/plot/postproc saving'''
    SAVE_TYPE_DICT = {
        'log': config.save.log,
        'message': config.save.message,
        'tb': config.save.iverilog,
        'dir': config.save.pub
    }
    type_config = SAVE_TYPE_DICT[save_type]
    run = config.run
    pub = config.save.pub
    if not save_type in SAVE_TYPE_DICT.keys():
        raise Exception('no such saving type named \"%s\"' % (save_type))
    # file name:
    if pub.prefix is None:
        unique_name = '%s'%(run.time)
    else:
        unique_name = '%s_%s'%(str(pub.prefix), run.time)
    if custom_name != '':
        custom_name = '%s_'%(custom_name)
    file_name = custom_name + unique_name
    # dir:
    # if (pub.dir is None):
    #     save_dir = type_config.dir
    # else:
    #     if pub.subdir not in ['', None] and not pub.subdir.endswith('/'): # in case of missing '/'
    #         pub.subdir = pub.subdir+'/'
    #     else:
    #         pub.subdir = pub.subdir 
    #     save_dir = '%s%s%s/'%(pub.dir, pub.subdir, unique_name)
    if pub.subdir not in ['', None] and not pub.subdir.endswith('/'): # in case of missing '/'
        pub.subdir = pub.subdir+'/'
    else:
        pub.subdir = pub.subdir 
    save_dir = '%s%s%s/'%(pub.dir, pub.subdir, unique_name)
    if save_type == 'dir':
        return save_dir
    if os.path.exists(save_dir) != True: #dir check
        os.makedirs(save_dir)
    # suffix:
    suffix_dict = {'log': '.log', 'tb': '.v'}#, 'model': '.pt'}
    if save_type == 'message': # leave the suffix to the user
        suffix = ''
    else:
        suffix = suffix_dict[save_type]
    # merge:
    save_path = save_dir + file_name + suffix
    return save_path
    
def add_save_root_to(config):
    """save root; ends with '/'"""
    config.save.root = save_path_setting(config, 'dir')
    return config

############################# log save ###############################
class AutoLogger:
    """singleton class, used as the logger in the project. supported by loguru."""
    _instance = None
    _initialized = False
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AutoLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not AutoLogger._initialized:
            if Config._instance is not None: # make sure that the initialization of logger is after the config
                AutoLogger._initialized = True
                self.config = Config()
                self.debug_en = self.config.save.log.debug_en
                self.log_level = self.config.save.log.level
                self.logger = logurulogger 
                # self.log_root_dir = ""
                # self.runing_log_path = os.path.join(self.log_root_dir, 'running.log')
                self.running_log_path = save_path_setting(self.config, 'log')
                self._save_config() # now the log is always saved
                self._init_levels()
                self._init_handlers()
                self.log_stream = None
                self.running_log_id = None
                self.temp_log_id = None
                self.logline_prefix_list:list[str] = []

    def __call__(self, string:str):
        self.info(string)

    def _init_levels(self):
        """initialize the customized log levels"""
        self.logger.level("POSITIVE", no=22, color="<fg 194>") # #d7ffd7 in console
        self.logger.level("NEGATIVE", no=23, color="<fg 225>") # #ffd7ff in console
        self.logger.level("FAILED", no=26, color="<red>")

    def _init_handlers(self):
        """set the loggers for the project"""
        self.logger.remove(0) # remove the original stderr handler (console handler)
        ##### console logger:
        console_level = "INFO" if not self.debug_en else "DEBUG"
        self.logger.add(sys.stdout, level=console_level, format="<green>{time:YYYY-MM-DD HH:mm:ss.S}</> | <level>{level: <8}</> | <level>{message}</>") # <color>...</> means colorize the text
        ##### running logger:
        self.running_log_id = self._set_handler(self.running_log_path, level=self.log_level)
        
    def _set_handler(self, path:str|StringIO, level:str=None, filter=None, format=None) -> int:
        """
            - set one handler for the logger (see loguru documentation to know what is a handler)
            - input:
                - level: the lowest level of the log that will be saved for this handler
                - filter: the customized filter (func/dict/str) to match what to be saved
                - format: the format of each record
        """
        if format is None:
            format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
            # format = "{time: HH:mm:ss} | {level} | {message}"
        format : str
        paras = {
            "sink": path,
            "format": format,
            "level": level,
            "filter": filter
        }
        if isinstance(path, str):
            paras["rotation"] = '500 MB'
            paras["encoding"] = 'utf-8'
        handler_id = self.logger.add(**paras)
        return handler_id

    # methods for temporary logging
    def set_temp_log(self):
        """
        initialize a temporary log stream, if already exists, reset it first
        - a temporary log means this is a independent log block at the same time with the running log, and it will be saved to a file
        """
        if self.temp_log_id is not None:
            self.reset_temp_log()
        self.log_stream = StringIO()
        self.temp_log_id = self._set_handler(self.log_stream, level=self.log_level) # same as the running logger

    def reset_temp_log(self):
        """delete the temporary log and return the content"""
        if self.temp_log_id is not None:
            log_content = self.get_temp_log()
            self.logger.remove(self.temp_log_id)
            self.log_stream.close()
            self.log_stream = None
            self.temp_log_id = None
            return log_content
        else:
            self.logger.warning("logger warning: no temp log to reset")
            return ""

    def get_temp_log(self)->str:
        """get the content of the temporary log"""
        if self.log_stream is not None:
            return self.log_stream.getvalue()
        else:
            return ""

    # methods for prefix of a line of log
    def set_prefix(self, prefix:str):
        """
        - set the prefix for the log line. the prefix will be stacked.
        - for example, if you set prefix1, prefix2, prefix3, the log line will be like: [prefix1] (prefix2) (prefix3) log_content
        """
        self.logline_prefix_list.append(prefix)

    def pop_prefix(self):
        """pop the last prefix out of the prefix stack"""
        if len(self.logline_prefix_list) > 0:
            return self.logline_prefix_list.pop()
        else:
            self.logger.warning("logger warning: no prefix to pop")

    def clear_prefix(self):
        """clear all the prefixes"""
        self.logline_prefix_list.clear()

    def show_prefix(self):
        """show the current prefixes"""
        self.logger.info(f"current prefixes: {self.logline_prefix}")

    def check_prefix(self, prefix:str):
        """check if the prefix is in the prefix stack"""
        return prefix in self.logline_prefix_list

    @property
    def logline_prefix(self):
        """ 
        - the prefix will be like: "[prefix1] (prefix2) (prefix3)", there should be [ ]/( ) around each prefix
        - if there is no prefix, return " "
        """
        first_bracker = "[]"
        other_bracker = "[]"
        if len(self.logline_prefix_list) > 0:
            prefix_first = first_bracker[0] + self.logline_prefix_list[0]  + first_bracker[-1] + " "
            if len(self.logline_prefix_list) > 1:
                prefix_other = " ".join([(other_bracker[0] + prefix + other_bracker[-1]) for prefix in self.logline_prefix_list[1:]]) + " "
            else:
                prefix_other = ""
            return prefix_first + prefix_other
        else:
            return ""

    # methods for logging
    def trace(self, string:str):
        """ the most trival info, level value: 5"""
        self.logger.trace(self.logline_prefix + string)

    def debug(self, string:str):
        """ debug level log, some point info; level value: 10"""
        string = string + " | " + self._get_caller_location()
        self.logger.debug(self.logline_prefix + string)

    def info(self, string:str):
        """info level log; level value: 20"""
        self.logger.info(self.logline_prefix + string)

    def positive(self, string:str):
        """positive level log; level value: 22"""
        self.logger.log("POSITIVE", self.logline_prefix + string)

    def negative(self, string:str):
        """negative level log; level value: 23"""
        self.logger.log("NEGATIVE", self.logline_prefix + string)

    def success(self, string:str):
        """success level log; level value: 25"""
        self.logger.success(self.logline_prefix + string)

    def failed(self, string:str):
        """failed level log; level value: 26"""
        self.logger.log("FAILED", self.logline_prefix + string)

    def warning(self, string:str):
        """warning level log; level value: 30"""
        string = string + " | " + self._get_caller_location() + " | caller: " + self._get_caller_location(3)
        self.logger.warning(self.logline_prefix + string)

    def error(self, string:str):
        """error level log; level value: 40"""
        string = string + " | " + self._get_caller_location() + " | caller: " + self._get_caller_location(3)
        self.logger.error(self.logline_prefix + string)

    def critical(self, string:str):
        """critical level log; level value: 50"""
        string = string + " | " + self._get_caller_location() + " | caller: " + self._get_caller_location(3)
        self.logger.critical(self.logline_prefix + string)

    def match_level(self, condition:bool, yeslevel:str, nolevel:str, string:str):
        """will log the string with yeslevel if condition is True, else with nolevel"""
        if condition:
            getattr(self, yeslevel)(string)
        else:
            getattr(self, nolevel)(string)

    def assert_(self, condition:bool, string:str, level:str='critical'):
        """
        - similar to the assert statement, but will save the log before raising the AssertionError
        - you can customize the level of the log, default: critical; you should use lower case
        """
        if not condition:
            getattr(self, level)(string)            
            raise AssertionError(string)

    @staticmethod
    def _get_caller_location(level:int=2):
        caller_file = inspect.stack()[level].filename
        caller_file = os.path.relpath(caller_file, ORIGINAL_RUN_PATH)
        caller_func = inspect.stack()[level].function
        caller_line = inspect.stack()[level].lineno
        return f"location: {caller_file}, func: {caller_func}, line: {caller_line}"

    def _save_config(self):
        with open(self.running_log_path, 'a') as file:
            #notes:
            if not self.config.save.log.notes is None:
                file.write('%s\n\n' % (self.config.save.log.notes))
            #config information:
            print_config(file, self.config)

    """
    loguru level table
    level  |   value
    TRACE  |   5
    DEBUG  |   10
    INFO   |   20
    SUCCESS|   25
    WARNING|   30
    ERROR  |   40
    CRITICAL|  50

    my level table
    level  |   value
    POSITIVE|  22
    NEGATIVE|  23
    FAILED |   26
    """

class log_localprefix:
    """
    usage as a context manager

    ::

        with log_localprefix('prefix'):
            # log content
            logger.info('log content')
    
            -> "[prefix] log content"

    
    usage as a decorator

    ::
        
            @log_localprefix('prefix')
            def func():
                logger.info('log content')
            
                -> "[prefix] log content

    """
    def __init__(self, prefix:str):
        self.prefix = prefix
        self.logger = AutoLogger()
    
    def __enter__(self):
        self.logger.set_prefix(self.prefix)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.pop_prefix()

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper

def print_dict(file, input_dict, indent='', ind_style=' '):
    if isinstance(input_dict, Dict) or isinstance(input_dict, dict):
        dict_items = input_dict.items()
    else:
        raise TypeError("input type of func 'print_dict' is not Dict(obj) or dict")
    for k, v in dict_items:
        if not isinstance(v, Dict) and not isinstance(v, dict):
            file.write('%s%s: %s\n' % (indent, k, v))
        else:
            file.write('%s%s: \n' % (indent, k))
            next_indent = '%s   %s'%(ind_style, indent)
            print_dict(file, v, next_indent, ind_style)

def print_config(file, config):
    """
    split mode: `running info` + `custom` config + `default` config
    iwantall mode: `custom` config + `merged` config + `default` config
    merge mode: `merged` config
    """
    mode = config.save.log.cfg_pmode
    indent_style = ' '
    if mode == 'split':
        # running information: (only split mode)
        file.write('---------------running info---------------\n')
        file.write('last version: %s\n' % (config.run.version))
        file.write('custom config file: %s\n' % (config.run.custom_path))
        file.write('starting time: %s\n' % (config.run.time))
        file.write('host name: %s\n' % (config.run.hostname))
        file.write('process ID: %s\n' % (config.run.pid))
        file.write('------------------------------------------\n')
    if mode in ['split', 'iwantall']:
        # custom config:
        custom_cfg, default_cfg = cfg.load_split_config(custom_config_path=config.run.custom_path)
        file.write('\n---------------custom config--------------\n')
        if custom_cfg is None:
            file.write('\nNo customized configuration\n')
        else:
            print_dict(file, custom_cfg, ind_style = indent_style)
        file.write('------------------------------------------\n')
    if mode in ['merge', 'iwantall']:
        # merged config:
        file.write('------config info (custom + default)------\n')
        print_dict(file, config, ind_style = indent_style)
        file.write('------------------------------------------\n')
    if mode in ['split', 'iwantall']:
        # default config:
        file.write('\n--------------default config--------------\n')
        print_dict(file, default_cfg, ind_style = indent_style)
        file.write('------------------------------------------\n')

def save_config():
    config = Config()
    save_path = save_path_setting(config, 'log')
    with open(save_path, 'a') as file:
        #notes:
        if config.save.log.notes is not None:
            file.write('%s\n\n' % (config.save.log.notes))
        #config information:
        print_config(file, config)

def save_log_line(line, config):
    # if config.save.log.en:
    #     save_path = save_path_setting(config, 'log')
    #     with open(save_path, 'a') as file:
    #         file.write('%s\n'%(line))
    autologger = AutoLogger()
    autologger.info(line)

def print_and_save(line, config):
    # print(line)
    # if config.save.log.en:
    #     save_log_line(line, config)
    autologger = AutoLogger()
    autologger.info(line)
    

############################# message/code save #############################
def save_messages_to_txt(messages, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'a') as file:
        for message in messages:
            if "time" in message.keys():
                file.write('########## %s (%ss used) ##########\n%s\n\n' % (message['role'], message['time'], message['content']))
            else:
                file.write('########## %s ##########\n%s\n\n' % (message['role'], message['content']))
        file.write('\n')

def print_messages(messages):
    # just like save_messages_to_txt
    for message in messages:
        if "time" in message.keys():
            print('########## %s (%ss used) ##########\n%s\n' % (message['role'], message['time'], message['content']))
        else:
            print('########## %s ##########\n%s\n' % (message['role'], message['content']))

def save_messages_to_log(messages, config):
    save_path = save_path_setting(config, 'log')
    save_messages_to_txt(messages, save_path)

def gpt_message_individual_save(messages, config, file_name = None, file_format = "json", silent = False):
    save_path = save_path_setting(config, 'message')
    # change the file name (xxx/xx.json->xxx/file_name.json)
    if file_name is not None:
        save_path = save_path.split('/')
        save_path[-1] = file_name + "." + file_format
        save_path = '/'.join(save_path)    
    if file_format == 'txt':
        save_messages_to_txt(messages, save_path)
    elif file_format == 'json':
        save_dict_json_form(messages, save_path)
    # print
    if not silent:
        print("\n")
        if file_name is not None:
            print("(file name: %s)"%(file_name))
        print('your conversation with ChatGPT has been successfully saved to "%s"\n' % (save_path))

# def save_TB_code(code_txt, task_id, config):
#     """save the verilog testbench code to a .v file."""
#     iverilog_dir = config.save.iverilog.subdir
#     save_path = save_path_setting(config, 'tb')
#     save_path = save_path.split('/')
#     # insert iverilog dir
#     save_path.insert(-1, iverilog_dir)
#     tb_name = task_id + '_tb.v'
#     save_path[-1] = tb_name
#     save_dir = '/'.join(save_path[:-1]) + '/'
#     save_path = '/'.join(save_path)
#     if os.path.exists(save_dir) != True: #dir check
#         os.makedirs(save_dir)
#     with open(save_path, 'a') as file:
#         file.write(code_txt)
#     print("\n")
#     print('your testbench code has been successfully saved to "%s"\n' % (save_path))
#     return {'name': tb_name, 'dir': save_dir, 'path': save_path}


# will be discarded in the future
def save_code_iv(code_txt, task_id, code_type, config, iverilog_dir = None, silent = False):
    """
    save the verilog TB/DUT code to a .v file. This func is for iverilog call.
    #### input:
    - code_txt: the verilog code in string format
    - task_id: the task id of the problem
    - code_type: 'TB' or 'DUT'
    - config: the config object
    - iverilog_dir: the directory to save the code. If None, use the default directory.
    """
    assert code_type in ["TB", "DUT"], "code_type should be 'TB' or 'DUT'"
    suffix_dict = {'TB': '_tb.v', 'DUT': '.v'}
    if iverilog_dir is None:
        iverilog_subdir = config.save.iverilog.subdir
        save_path = save_path_setting(config, 'tb')
        save_path = save_path.split('/')
        # insert iverilog dir
        save_path.insert(-1, iverilog_subdir)
    else:
        if not iverilog_dir.endswith('/'):
            iverilog_dir += '/'
        iverilog_path = iverilog_dir  + "name.v"
        save_path = iverilog_path.split('/')
    code_name = task_id + suffix_dict[code_type]
    save_path[-1] = code_name
    save_dir = '/'.join(save_path[:-1]) + '/'
    save_path = '/'.join(save_path)
    os.makedirs(save_dir, exist_ok=True)
    with open(save_path, 'a') as file:
        file.write(code_txt)
    if not silent:
        print("\n")
        print('your %s code has been successfully saved to "%s"\n' % (code_type, save_path))
    return {'name': code_name, 'dir': save_dir, 'path': save_path, 'code_type': code_type}

def save_code(code, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as file:
        file.write(code)

autologger = AutoLogger()

############################# __main__ ################################
if __name__ == "__main__":
    None