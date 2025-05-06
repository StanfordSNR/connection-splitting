# Emulation

This code runs a single emulation benchmark in `mininet` with an HTTPS client
and server. The output of the benchmark includes the throughput of the data
transfer. There are simple wrappers for Linux TCP, as well as the Google,
Cloudflare, and `picoquic` implementations of QUIC.

Each experiment can be parameterized by the network configuration, the number of
bytes transferred in the GET request, and a supported congestion control
algorithm for the transport protocol implementation. For all options, see:

```
sudo -E python3 emulation/main.py --help
```

## Example

This is a simple example of a 10 MB data transfer using Linux TCP + CUBIC. The
default network configuration has loss on the near path segment, and we also
start a TCP connection-splitting PEP.

```
sudo -E python3 emulation/main.py --pep tcp -n 10M
{
    "inputs": {
        "label": "NO_LABEL",
        "protocol": "LINUX_TCP",
        "num_trials": 1,
        "start_time": "2025-05-05 17:56:33",
        "data_size": 10000000,
        "cca": "cubic",
        "pep": true
    },
    "outputs": [{
        "success": true,
        "timeout": false,
        "time_s": 9.873512565000055,
        "throughput_mbps": 8.102486270548393
    }]
}
```

## Tests

Run all tests (some tests will fail if the required dependencies for the HTTPS
implementation are not installed):

```
sudo -E python -m unittest -v
```

Filter for certain tests:

```
sudo -E python -m unittest -v -k test_network
```
