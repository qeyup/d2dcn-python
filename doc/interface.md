# MQTT data structure 


## Device info

- d2dcn/MAC/DeviceInfo:
    {
        "name": **DEVICE_NAME**
    }


## Device command API info

- d2dcn/MAC/**SERVICE_NAME**/command/**COMMAND_TYPE**/**COMMAND_NAME**:
    {
        "protocol": "json-udp",
        "ip": **IP**,
        "port": **XXXX**,
        "params": {
            "**PARAM_1**": "int",
            "**PARAM_2**": "string",
            "**PARAM_3**": "bool"
        },
        "response": {
            "**RESULT_1**": "bool",
            "**RESULT_2**": "string"
        }
    }


## Device shared data info

- d2dcn/MAC/**SERVICE_NAME**/info/**INFO_TYPE**/**PARAM_NAME**:
    {
        "value": **PARAM_NAME**,
        "type": "int",
        "epoch": **1703112113**
    }


## Types

- generic
- action
- config
- test