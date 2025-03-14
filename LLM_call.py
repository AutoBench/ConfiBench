"""
Description :   This file is related to GPT call, include the function of calling GPT and the function of running GPT in chatgpt mode
Author      :   Ruidi Qiu (ruidi.qiu@tum.de)
Time        :   2023/11/17 15:01:06
LastEdited  :   2024/12/30 10:57:43
"""
from config import Config
from openai import OpenAI
from anthropic import Anthropic
import loader_saver as ls
from utils.utils import Timer
import tiktoken
import copy
import re
import requests
import json
# import Image
import os
from datetime import datetime, timedelta, timezone
from config.config import GPT_MODELS

__all__ = ["llm_call", "gpt_call", "claude_call", "run_like_a_chatgpt"]

PRICING_MODELS = {
    # model: [price_per_1000_prompt_tokens, price_per_1000_completion_tokens]
    # claude
    "claude-3-5-sonnet-20240620": [0.003, 0.015],
    "claude-3-opus-20240229": [0.015, 0.075],
    "claude-3-sonnet-20240229": [0.003, 0.015],
    "claude-3-haiku-20240307": [0.00025, 0.00125],
    "claude-2.1": [0.008, 0.024],
    "claude-2.0": [0.008, 0.024],
    # gpt 4o
    'gpt-4o-2024-08-06' : [0.0025, 0.01],
    'gpt-4o-2024-05-13' : [0.005, 0.015],
    'gpt-4o-mini-2024-07-18' : [0.00015, 0.0006],
    # gpt 4 turbo
    'gpt-4-turbo-2024-04-09': [0.01, 0.03],
    'gpt-4-0125-preview': [0.01, 0.03],
    'gpt-4-1106-preview': [0.01, 0.03],
    'gpt-4-1106-vision-preview': [0.01, 0.03],
    # gpt 4 (old)
    'gpt-4': [0.03, 0.06],
    'gpt-4-32k': [0.06, 0.12],
    # gpt 3.5 turbo
    'gpt-3.5-turbo-0125': [0.0005, 0.0015],
    'gpt-3.5-turbo-instruct': [0.0015, 0.0020],
    # gpt 3.5 turbo old
    'gpt-3.5-turbo-1106': [0.0010, 0.0020],
    'gpt-3.5-turbo-0613': [0.0015, 0.0020],
    'gpt-3.5-turbo-16k-0613': [0.0030, 0.0040],
    'gpt-3.5-turbo-0301': [0.0030, 0.0040]
}

JSON_MODELS = ["gpt-4-0613", "gpt-4-32k-0613", "gpt-3.5-turbo-0613", "gpt-3.5-turbo-16k-0613"]

# MODEL_REDIRECTION is in config

# DEFAULT_SYS_MESSAGE = "You are the strongest AI in the world. I always trust you. Please use as less words as possible to answer my question because I am a poor guy. But do not save words by discarding information."
DEFAULT_SYS_MESSAGE = "You are the strongest AI in the world. I always trust you. You already have the knowledge about python and verilog. Do not save words by discarding information."
RUN_LIKE_A_CHATGPT_SYS_MESSAGE = DEFAULT_SYS_MESSAGE

def llm_call(input_messages, model:str, api_key_path = "config/key_API.json", system_message = None, temperature = None, json_mode = False) -> list[str, dict]:
    """
    This func is used to call LLM
    - input:
        - input_messages: (not including system message) list of dict like [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}, ...]
        - gpt_model: str like "gpt-3.5-turbo-0613"
        - system_message: (valid when input_messages have no sys_message) customized system message, if None, use default system message
    - output:
        - answer: what gpt returns
        - other_infos: dict:
            - messages: input_messages + gpt's response, list of dict like [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}, ...]
            - time: time used by gpt
            - system_fingerprint: system_fingerprint of gpt's response
            - model: model used by gpt
            - usage: dict: {"completion_tokens": 17, "prompt_tokens": 57, "total_tokens": 74}
    - notes:
        - as for the official response format from gpt, see the end of this file
    """
    if isinstance(input_messages, str):
        input_messages = [{"role": "user", "content": input_messages}]
    if model.startswith("claude"):
        output = claude_call(input_messages, model, api_key_path, system_message, temperature, json_mode)
    elif model.startswith("gpt"):
        output = gpt_call(input_messages, model, api_key_path, system_message, temperature, json_mode)
    else:
        raise ValueError("model %s is not supported."%(model))
    llm_manager.update_usage(output[1]["usage"]["prompt_tokens"], output[1]["usage"]["completion_tokens"], model)
    return output


def gpt_call(input_messages, model, api_key_path, system_message = None, temperature = None, json_mode = False):
    """
    This func is used to call gpt
    - input:
        - input_messages: (not including system message) list of dict like [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}, ...]
        - gpt_model: str like "gpt-3.5-turbo-0613"
        - system_message: (valid when input_messages have no sys_message) customized system message, if None, use default system message
    - output:
        - answer: what gpt returns
        - other_infos: dict:
            - messages: input_messages + gpt's response, list of dict like [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}, ...]
            - time: time used by gpt
            - system_fingerprint: system_fingerprint of gpt's response
            - model: model used by gpt
            - usage: dict: {"completion_tokens": 17, "prompt_tokens": 57, "total_tokens": 74}
    - notes:
        - as for the official response format from gpt, see the end of this file
    """
    client = enter_api_key(api_key_path)
    # system message
    has_sysmessage = False
    for message in input_messages:
        if message["role"] == "system":
            has_sysmessage = True
            break
    if not has_sysmessage:
        if system_message is None:
            messages = [{"role": "system", "content": DEFAULT_SYS_MESSAGE}]
        else:
            messages = [{"role": "system", "content": system_message}]
    else:
        messages = []
    messages.extend(input_messages)
    # other parameters
    more_completion_kwargs = {}
    if temperature is not None:
        more_completion_kwargs["temperature"] = temperature
    if json_mode:
        if not model in JSON_MODELS:
            more_completion_kwargs["response_format"] = {"type": "json_object"}
    # call gpt
    with Timer(print_en=False) as gpt_response:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            **more_completion_kwargs
        )
    answer = completion.choices[0].message.content
    messages.append({"role": "assistant", "content": answer})
    time = round(gpt_response.interval, 2)
    system_fingerprint = completion.system_fingerprint
    usage = {"completion_tokens": completion.usage.completion_tokens, "prompt_tokens": completion.usage.prompt_tokens, "total_tokens": completion.usage.total_tokens}
    model = completion.model
    other_infos = {"messages": messages, "time": time, "system_fingerprint": system_fingerprint, "model": model, "usage": usage}
    # return answer, messages, time, system_fingerprint
    return answer, other_infos

def claude_call(input_messages, model, api_key_path, system_message = None, temperature = None, json_mode = False):
    """
    This func is used to call gpt
    #### input:
    - input_messages: (not including system message) list of dict like [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}, ...]
    - gpt_model: str like "gpt-3.5-turbo-0613"
    - config: config object
    - system_message: (valid when input_messages have no sys_message) customized system message, if None, use default system message
    #### output:
    - answer: what gpt returns
    - other_infos: dict:
        - messages: input_messages + gpt's response, list of dict like [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}, ...]
        - time: time used by gpt
        - system_fingerprint: system_fingerprint of gpt's response
        - model: model used by gpt
        - usage: dict: {"completion_tokens": 17, "prompt_tokens": 57, "total_tokens": 74}
    #### notes:
    as for the official response format from gpt, see the end of this file
    """
    client = enter_api_key(api_key_path, provider="anthropic")
    prefill = None
    # system message
    has_sysmessage = False
    for message in input_messages:
        if message["role"] == "system":
            has_sysmessage = True
            break
    if not has_sysmessage:
        if system_message is None:
            messages = [{"role": "system", "content": DEFAULT_SYS_MESSAGE}]
        else:
            messages = [{"role": "system", "content": system_message}]
    else:
        messages = []
    messages.extend(input_messages)
    for message in messages:
        if message["role"] == "system":
            messages.remove(message) # delete the system message
    # other parameters
    more_completion_kwargs = {}
    if temperature is not None:
        more_completion_kwargs["temperature"] = temperature
    if json_mode:
        messages[-1]["content"] += "\nYour reply should be in JSON format."
        prefill = {"role": "assistant", "content": "{"}
        messages.append(prefill)
    # call claude
    if model == "claude-3-5-sonnet-20240620":
        max_tokens = 8192
    else:
        max_tokens = 4096
    with Timer(print_en=False) as gpt_response:
        completion = client.messages.create(
            max_tokens=max_tokens,
            model=model,
            messages=messages,
            **more_completion_kwargs
        )
    answer = completion.content[0].text
    if prefill is not None:
        answer = prefill["content"] + answer
    messages.append({"role": "assistant", "content": answer})
    time = round(gpt_response.interval, 2)
    system_fingerprint = ""
    usage = {"completion_tokens": completion.usage.output_tokens, "prompt_tokens": completion.usage.input_tokens, "total_tokens": completion.usage.input_tokens + completion.usage.output_tokens}
    other_infos = {"messages": messages, "time": time, "system_fingerprint": system_fingerprint, "model": model, "usage": usage}
    # return answer, messages, time, system_fingerprint
    return answer, other_infos

def run_like_a_chatgpt():
    config = Config()
    gpt_model = config.gpt.model
    gpt_key_path = config.gpt.key_path
    if config.gpt.chatgpt.start_form == 'prompt':
        preloaded_prompt = ls.load_txt(config.load.prompt.path)
    else:
        preloaded_prompt = None
    if gpt_model.startswith("gpt"):
        llm_name = "ChatGPT"
    elif gpt_model.startswith("claude"):
        llm_name = "Claude"
    else:
        llm_name = "LLM"
    # messages = [{"role": "system", "content": "You are a hardware code expert, skilled in understanding and generating verilog hardware language. You are the strongest AI hardware expert in the world. I totally believe you can fulfill the task I give you. You always give me the most detailed solution. Your reply should only contain code."}]
    messages = [{"role": "system", "content": RUN_LIKE_A_CHATGPT_SYS_MESSAGE}]
    response_data_dicts = [] # this is to record other data of gpt's response like seed and time
    while True:
        # load prompt
        if preloaded_prompt is not None:
            content = preloaded_prompt
            preloaded_prompt = None
            print("User (preloaded prompt): %s"%(content))
            ls.save_log_line("(the first user message is from preloaded prompt)", config)
        else:
            content = input("User: ")
        # break loop
        if content in ["exit", "quit", "break", "", None]:
            break
        # send prompt to gpt
        messages.append({"role": "user", "content": content})
        # run gpt
        answer, other_infos = llm_call(
            input_messages = messages, 
            model = gpt_model, 
            api_key_path = gpt_key_path, 
            system_message = RUN_LIKE_A_CHATGPT_SYS_MESSAGE, 
            temperature = config.gpt.temperature
        )
        messages, time, system_fingerprint = other_infos["messages"], other_infos["time"], other_infos["system_fingerprint"]
        # get data from response
        data_dict = {}
        data_dict["system_fingerprint"] = system_fingerprint
        data_dict["model"] = gpt_model
        data_dict["time"] = time
        response_data_dicts.append(data_dict)
        # print
        print(f'{llm_name}: {answer}')
        print("(%ss used)" % (time))
        if config.gpt.chatgpt.one_time_talk:
            break
    messages_plus = gen_messages_more_info(messages, response_data_dicts)
    if config.save.log.en:
        ls.save_messages_to_log(messages_plus, config)
    if config.save.message.en:
        ls.gpt_message_individual_save(messages, config, file_name="messages")
        ls.gpt_message_individual_save(messages_plus, config, file_name="messages_plus")


def enter_api_key(api_key_path, provider="openai"):
    if provider == "openai":
        key = ls.load_json_dict(api_key_path)["OPENAI_API_KEY"]
        client = OpenAI(api_key=key)
    elif provider == "anthropic":
        key = ls.load_json_dict(api_key_path)["ANTHROPIC_API_KEY"]
        client = Anthropic(api_key=key)
    else:
        raise ValueError("provider %s is not supported."%(provider))
    return client

def gen_messages_more_info(original_messages, response_data_dicts):
    # additional info only at: role = "assistant"
    messages = copy.deepcopy(original_messages)
    idx_response = 0
    for i in range(len(messages)):
        if messages[i]["role"] == "assistant":
            # messages[i].extend(response_data_dicts[idx_response]) # wrong syntax
            messages[i] = {**messages[i], **response_data_dicts[idx_response]}
            idx_response += 1
    # add idx to each message
    for i in range(len(messages)):
        messages[i]["idx"] = i
    return messages


def dalle3():
    """
        This function hasn't been well packaged
        now we have the free dalle3 application: microsoft - copilot
    """
    def download_image(url, folder_path):
        response = requests.get(url)
        file_path = os.path.join(folder_path, os.path.basename(url))
        with open(file_path, "wb") as file:
            file.write(response.content)
        return file_path
    
    model_name = "dall-e-3"
    image_size = "1024x1024" # 1792x1024, 1024x1024, 1024x1792
    download_folder = r"saves/dalle3/"
    os.makedirs(download_folder, exist_ok=True)

    while True:
        name = input("please name the generated figure (\"exit\" to exit): ")
        if name == "exit":
            break
        prompt = input("please input the prompt(\"exit\" to exit): ")
        if prompt == "exit":
            break
        
        try:
            # num_images = int(input("please input the number of figures (default=1)：") or "1")
            num_images = 1
            print("generating your figure...")
            # response = requests.post(
            #     "https://api.openai-proxy.org/v1/images/generations",
            #     headers={"Authorization": ""},
            #     json={"model": model_name, "size": image_size, "prompt": prompt, "n": num_images},
            # )
            client = enter_api_key('config/key_API.json')
            response = client.images.generate(
                model=model_name,
                prompt=prompt,
                size=image_size,
                quality="standard",
                n=num_images,
            )
            # response.raise_for_status()
            # data = response.json()["data"]

            image_url = response.data[0].url
            # the name should end with .png
            file_name = name + ".png"
            file_path = download_image(image_url, download_folder)
            new_file_path = os.path.join(download_folder, file_name)
            os.rename(file_path, new_file_path)
            print("figure was downloaded to %s" %(new_file_path))
            

            # file_path = download_image(image_url, download_folder)
            # print("图片已下载至：", file_path)


            # current_time = datetime.now(timezone.utc) + timedelta(hours=8)  
            # current_time_str = current_time.strftime("%Y%m%d-%H%M")

            # for i, image in enumerate(data):
            #     image_url = image["url"]
            #     file_name = current_time_str + f"-{str(i+1).zfill(3)}.png"
            #     file_path = download_image(image_url, download_folder)
            #     new_file_path = os.path.join(download_folder, file_name)
            #     os.rename(file_path, new_file_path)
            #     print("图片已下载至：", new_file_path)

        except requests.exceptions.HTTPError as err:
            print("Request Error: ", err.response.text)

        except Exception as e:
            print("Error: ", str(e))



############### utils of gpt ###############
def num_tokens_from_string(string: str, model_name="gpt-4") -> int:
    """
    Returns the number of tokens in a single text string.
    https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    """
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(string))
    return num_tokens

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in PRICING_MODELS.keys():
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.
    See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")

def extract_code(text, code_type):
    """
    #### function:
    - extract code from text
    #### input:
    - text: str, gpt's response
    - code_type: str, like "verilog"
    #### output:
    - list of found code blocks
    """
    code_type = code_type.lower()
    start = "```" + code_type
    end = "```"
    verilog_blocks = re.findall(start + r'\s*(.*?)'+ end, text, re.DOTALL)
    if verilog_blocks:
        return verilog_blocks
    else:
        # return [""]
        return [text]
    
def get_dict_from_gpt_json(gpt_json_string):
    """
    - this function is used to get the dict from the gpt json string
    """
    gpt_json_string = gpt_json_string.replace("```json", "").replace("```", "").strip()
    print(gpt_json_string)  
    return json.loads(gpt_json_string)

def cost_calculator(usages:list, model="gpt-4-0125-preview"):
    """
    - this function is used to calculate the price of gpt
    - usage: list of dicts, [{"completion_tokens": 17, "prompt_tokens": 57, "total_tokens": 74}, ...]

    """
    if model not in PRICING_MODELS:
        raise ValueError(f"model {model} is not supported in the pricing calculator.")
    price = 0
    for usage in usages:
        price += usage["prompt_tokens"] * PRICING_MODELS[model][0] / 1000.0 + usage["completion_tokens"] * PRICING_MODELS[model][1] / 1000.0
    return price

def message_to_conversation(messages):
    """
    - this function is used to convert messages to conversation
    """
    conversation = ""
    for message in messages:
        if message["role"] == "system":
            conversation += "############################## conversation begin ##############################\n"
        conversation += '########## %s ##########\n%s\n\n' % (message['role'], message['content'])
    return conversation

class LLM_Manager:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LLM_Manager, cls).__new__(cls)
        return cls._instance

    def __init__(self, api_key="config/key_API.json") -> None:
        if not self._initialized:
            # total
            self.tokens_in_total = 0
            self.tokens_out_total = 0
            self.tokens_both_total = 0
            self.cost_total = 0
            # section
            self.tokens_in_section = 0
            self.tokens_out_section = 0
            self.tokens_both_section = 0
            self.cost_section = 0
            # dict {"model1": {}, "model2": {}, ...}
            self.usage_info = {}
            # chat
            self._llm_model_now = None
            self._temperature = None
            self.messages = [{"role": "system", "content": DEFAULT_SYS_MESSAGE}]
            if not os.path.exists(api_key):
                raise ValueError(f"api key path {api_key} is not valid.")
            self._api_key_path = api_key

    def update_usage(self, tokens_in:int, tokens_out:int, model:str):
        cost = tokens_in * PRICING_MODELS[model][0] / 1000.0 + tokens_out * PRICING_MODELS[model][1] / 1000.0
        # dict
        if model not in self.usage_info.keys():
            self.usage_info[model] = {"tokens_in": 0, "tokens_out": 0, "tokens_both": 0, "cost": 0}
        self.usage_info[model]["tokens_in"] += tokens_in
        self.usage_info[model]["tokens_out"] += tokens_out
        self.usage_info[model]["tokens_both"] += tokens_in + tokens_out
        self.usage_info[model]["cost"] += cost
        # total
        self.tokens_in_total += tokens_in
        self.tokens_out_total += tokens_out
        self.tokens_both_total += tokens_in + tokens_out
        self.cost_total += cost
        # section
        self.tokens_in_section += tokens_in
        self.tokens_out_section += tokens_out
        self.tokens_both_section += tokens_in + tokens_out
        self.cost_section += cost

    def new_section(self):
        """
        new usage section (only reset the tokens and cost of the section)
        """
        self.tokens_in_section = 0
        self.tokens_out_section = 0
        self.tokens_both_section = 0
        self.cost_section = 0

    def set_model(self, model:str):
        self._llm_model_now = model

    def set_temperature(self, temperature:float):
        self._temperature = temperature

    def chat(self, prompt:str, clear_mem:bool=False, model:str=None, temperature:float=None, sys_prompt:str=DEFAULT_SYS_MESSAGE)->str:
        model = self._llm_model_now if model is None else model
        temperature = self._temperature if temperature is None else temperature
        if clear_mem:
            self.messages = [{"role": "system", "content": sys_prompt}]
        self.messages.append({"role": "user", "content": prompt})
        answer, other_infos = llm_call(
            input_messages = self.messages, 
            model = model, 
            api_key_path = self._api_key_path, 
            temperature = temperature
        ) # usage already updated in llm_call
        # update messages
        self.messages = other_infos["messages"]
        return answer
        

llm_manager = LLM_Manager()



if __name__ == "__main__":
    # print("GPT_call.py does not support running as a main file.")
    print('we are testing dalle3')
    dalle3()


"""
(see more in https://platform.openai.com/docs/guides/text-generation/chat-completions-api)
An example Chat Completions API response looks as follows:
{
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "content": "The 2020 World Series was played in Texas at Globe Life Field in Arlington.",
        "role": "assistant"
      }
    }
  ],
  "created": 1677664795,
  "id": "chatcmpl-7QyqpwdfhqwajicIEznoc6Q47XAyW",
  "model": "gpt-3.5-turbo-0613",
  "object": "chat.completion",
  "usage": {
    "completion_tokens": 17,
    "prompt_tokens": 57,
    "total_tokens": 74
  }
}
"""