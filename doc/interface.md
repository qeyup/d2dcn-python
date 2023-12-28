# MQTT data structure 


## Device info

- ServiceInfo/MAC/DeviceInfo:
    {
        "name": **DEVICE_NAME**
    }


## Device command API info

- ServiceInfo/MAC/**SERVICE_NAME**/Commands/**COMMAND_TYPE**/**COMMAND_NAME**:
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

- ServiceInfo/MAC/**SERVICE_NAME**/info/**INFO_TYPE**/**PARAM_NAME**:
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