from GCP_Guardrail_Runner import GuardrailRunner
from typing import Dict, Any, Optional
import json


def check_configs(config_path: str, input_text: str, generated_text: Optional[str] = None, 
                  user_name: str = "simpplr", enable_logging: bool = False):
    """
    Run guardrail checks on input text and optionally generated text.
    
    Args:
        config_path: Path to the config JSON file
        input_text: User input text to check (for input phase)
        generated_text: Model-generated response to check (for output phase, optional)
        user_name: User name for logging
        enable_logging: Whether to enable logging
    """
    runner = GuardrailRunner(config_path=config_path, user_name=user_name, enable_logging=enable_logging)
    print("\nGuardrail initialized successfully!")
    print(f"  Log file: {runner.get_log_file_path()}")
    result = runner.run(input_text, generated_text=generated_text)
    print("Result:")
   
    if result.get("summary", {}).get("passed"):
        print("\nAll checks PASSED")
    else:
        print("\nSome checks FAILED")
    return result


"""
# Check for config type 1
config_path = "test_config_folder/config_type_1.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_1.json", "w") as f:
    json.dump(result1, f, indent=2)



# Check for config type 2
config_path = "test_config_folder/config_type_2.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_2.json", "w") as f:
    json.dump(result1, f, indent=2)




# Check for config type 3
config_path = "test_config_folder/config_type_3.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_3.json", "w") as f:
    json.dump(result1, f, indent=2)



# Check for config type 4
config_path = "test_config_folder/config_type_4.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_4.json", "w") as f:
    json.dump(result1, f, indent=2)



# Check for config type 5
config_path = "test_config_folder/config_type_5.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_5.json", "w") as f:
    json.dump(result1, f, indent=2)



# Check for config type 6
config_path = "test_config_folder/config_type_6.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_6.json", "w") as f:
    json.dump(result1, f, indent=2)



# Check for config type 7
config_path = "test_config_folder/config_type_7.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_7.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 8
config_path = "test_config_folder/config_type_8.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_8.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 9
config_path = "test_config_folder/config_type_9.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_9.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 10
config_path = "test_config_folder/config_type_10.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_10.json", "w") as f:
    json.dump(result1, f, indent=2)
    

# Check for config type 11
config_path = "test_config_folder/config_type_11.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_11.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 12
config_path = "test_config_folder/config_type_12.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_12.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 13
config_path = "test_config_folder/config_type_13.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_13.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 14
config_path = "test_config_folder/config_type_14.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_14.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 15
config_path = "test_config_folder/config_type_15.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_15.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 16
config_path = "test_config_folder/config_type_16.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_16.json", "w") as f:
    json.dump(result1, f, indent=2)



# Check for config type 17
config_path = "test_config_folder/config_type_17.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_17.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 18
config_path = "test_config_folder/config_type_18.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_18.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 19
config_path = "test_config_folder/config_type_19.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_19.json", "w") as f:
    json.dump(result1, f, indent=2)

# Check for config type 20
config_path = "test_config_folder/config_type_20.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_20.json", "w") as f:
    json.dump(result1, f, indent=2)

# Check for config type 21
config_path = "test_config_folder/config_type_21.json"
test_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, test_text)
with open("test_config_results/result_type_21.json", "w") as f:
    json.dump(result1, f, indent=2)


# Check for config type 22 (has output phase - need generated_text)
config_path = "test_config_folder/config_type_22.json"
input_text = "Hello, I am not happy as I killed someone."
generated_text = "I understand you're feeling upset. Violence is never the answer. Please consider seeking help from a mental health professional."
result1 = check_configs(config_path, input_text, generated_text=generated_text)
with open("test_config_results/result_type_22.json", "w") as f:
    json.dump(result1, f, indent=2)

# Check for config type 23 (has output phase - need generated_text)
config_path = "test_config_folder/config_type_23.json"
input_text = "Hello, I am not happy as I killed someone."
generated_text = "I'm sorry to hear that. It sounds like you're going through a difficult time. Please reach out to local authorities or a counselor."
result1 = check_configs(config_path, input_text, generated_text=generated_text)
with open("test_config_results/result_type_23.json", "w") as f:
    json.dump(result1, f, indent=2)

# Check for config type 24 (has output phase - need generated_text)
config_path = "test_config_folder/config_type_24.json"
input_text = "Hello, I am not happy as I killed someone."
generated_text = "This is a serious matter. I recommend contacting emergency services or a legal professional immediately."
result1 = check_configs(config_path, input_text, generated_text=generated_text)
with open("test_config_results/result_type_24.json", "w") as f:
    json.dump(result1, f, indent=2)

# Check for config type 25 (has output phase - need generated_text)
config_path = "test_config_folder/config_type_25.json"
input_text = "Hello, I am not happy as I killed someone."
generated_text = "Go to hell."
result1 = check_configs(config_path, input_text, generated_text=generated_text)
with open("test_config_results/result_type_25.json", "w") as f:
    json.dump(result1, f, indent=2)

# Check for config type 26 (input only - USER_PROMPT)
config_path = "test_config_folder/config_type_26.json"
input_text = "Hello, I am not happy as I killed someone."
result1 = check_configs(config_path, input_text)
with open("test_config_results/result_type_26.json", "w") as f:
    json.dump(result1, f, indent=2)
"""


# Check for config type 27 (output only - MODEL_RESPONSE, need generated_text)
config_path = "test_config_folder/config_type_27.json"
input_text = "Tell me a joke"
generated_text = "Here's a joke: Why did the programmer quit his job? Because he didn't get arrays! Call me at 555-123-4567 for more jokes."
result1 = check_configs(config_path, input_text, generated_text=generated_text, enable_logging=True)
with open("test_config_results/result_type_27.json", "w") as f:
    json.dump(result1, f, indent=2)