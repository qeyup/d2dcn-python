# MQTT data structure 


## Device info

- d2dcn/**MAC**/device:
    {
        "name": **DEVICE_NAME**,
        "epoch": **XXXXXXXXXX**
    }


## Device command API info

- d2dcn/**MAC**/**SERVICE_NAME**/command/**TYPE**/**COMMAND_NAME**:
    {
        "transport": "udp/tcp",
        "ip": **IP**,
        "port": **XXXX**,
        "api": "json/raw"
        "parameter": {
            "**FIELD_NAME_1**": {
                "type": "**FIELD_TYPE**",
                "optional": "yes/no"
            },
            "**FIELD_NAME_2**": {
                "type": "**FIELD_TYPE**",
                "optional": "yes/no"
            },
            ...
        },
        "response": {
            "**FIELD_NAME_1**": {
                "type": "**FIELD_TYPE**",
                "optional": "yes/no"
            },
            "**FIELD_NAME_2**": {
                "type": "**FIELD_TYPE**",
                "optional": "yes/no"
            },
            ...
        }
    }


## Device shared data info

- d2dcn/**MAC**/**SERVICE_NAME**/info/**TYPE**/**FIELD_NAME**:
    {
        "value": **FIELD_VALUE**,
        "type": "**FIELD_TYPE**",
        "epoch": **XXXXXXXXXX**
    }


## Data types (**FIELD_TYPE**)
- int
- float
- string


## Command/Info types (**TYPE**)
- generic
- action
- config
- test
- runtime
