# emulation

For all options, see:

```
sudo -E python3 emulation/main.py --help
```

## Run TCP benchmark

```
sudo -E python3 emulation/main.py -t 5 tcp -n 100K [--pep]
```

## Start mininet CLI

```
sudo -E python3 emulation/main.py cli
```

## Run tests

```
emulation$ sudo -E python -m unittest
```
