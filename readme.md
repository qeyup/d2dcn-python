# Device to device comunication network

MAIN USAGES
- Register device service commands on the network so that other devices can call them.
- Obtain a list of commands from the services of the devices registered in the network.
- Call commands from registered device services in the network.
- Update information about device services on the network.
- Get updates of information about device services.


# Examples

## Register command

```bash
sudo docker run -it --rm -v $PWD:/home/docker/workspace d2dcn_dwi workspace/example/command_publish.py
```

## Call command

```bash
sudo docker run -it --rm -v $PWD:/home/docker/workspace d2dcn_dwi workspace/example/command_call.py
```

## Publish info

```bash
sudo docker run -it --rm -v $PWD:/home/docker/workspace d2dcn_dwi workspace/example/info_publish.py
```

## Read info

```bash
sudo docker run -it --rm -v $PWD:/home/docker/workspace d2dcn_dwi workspace/example/info_read.py
```