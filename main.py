"""
Description :   This is the head file of the project
Author      :   Ruidi Qiu (ruidi.qiu@tum.de)
Time        :   2023/11/28 11:19:59
LastEdited  :   2025/1/23 15:21:30
"""

import loader_saver as ls
from config import Config
import config
import LLM_call as gpt
import autoline as al
import iverilog_call as iv
import getopt
import sys
from config import CFG_CUS_PATH

def main(custom_cfg_path: str = CFG_CUS_PATH):
    
    # my_config = cfg.load_config(custom_cfg_path)
    # my_config = ls.add_save_root_to(my_config)
    my_config = Config(custom_cfg_path)
    # ls.add_save_root_to(my_config)
    logger = ls.AutoLogger() # initialize the autologger
    logger.info("all configurations are loaded, starting the main process...")
    match my_config.run.mode:
        case "chatgpt":
            gpt.run_like_a_chatgpt()
        case "iverilog":
            iv.run_iverilog()
        case "autoline":
            al.run_autoline()
        # case "dataset_manager":
        #     pass # TODO
        case _:
            raise ValueError("Invalid run mode: " + my_config.run.mode)
    print("Done!\n\n")

if __name__ == "__main__":
    # if no command, run the main function main()
    # if -h/--help, print the help message
    # if -c/--config + str, first get the custom config path, then run the main function


    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:", ["help", "config="])
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)
    if len(opts) == 1:
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print("Usage: python main.py [-h] [-c <custom_config_path>]")
                sys.exit(0)
            elif opt in ("-c", "--config"):
                config_path = config.get_cfg_path_from_alias(arg)
                main(config_path)
                sys.exit(0)
    elif len(opts) > 1:
        print("opts are more than 1; Usage: python main.py [-h] [-c <custom_config_path>]")
        sys.exit(2)
    else:
        main()
        sys.exit(0)