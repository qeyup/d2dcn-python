# MQTT data structure

## Device info

- d2dcn/**MAC**/device:

```json
{
    "name": **DEVICE_NAME**,
    "epoch": **XXXXXXXXXX**
}
```


## Device command API info

- d2dcn/**MAC**/**SERVICE_NAME**/command/**TYPE**/**COMMAND_NAME**:

```json
{
    "transport": "udp/tcp",
    "ip": **IP**,
    "port": **XXXX**,
    "api": "json/raw"
    "input": {
        "**FIELD_NAME_1**": {
            "type": "**FIELD_TYPE**",
            "optional": true/false
        },
        "**FIELD_NAME_2**": {
            "type": "**FIELD_TYPE**",
            "optional": true/false
        },
        ...
    },
    "output": {
        "**FIELD_NAME_1**": {
            "type": "**FIELD_TYPE**",
            "optional": true/false
        },
        "**FIELD_NAME_2**": {
            "type": "**FIELD_TYPE**",
            "optional": true/false
        },
        ...
    }
}
```


## Device shared data info

- d2dcn/**MAC**/**SERVICE_NAME**/info/**TYPE**/**FIELD_NAME**:

```json
{
    "value": **FIELD_VALUE**,
    "type": "**FIELD_TYPE**",
    "epoch": **XXXXXXXXXX**
}
```


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
