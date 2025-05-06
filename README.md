# Internet Connection Splitting: What's Old is New Again

This repository contains the artifact for the ATC '25 paper "Internet Connection
Splitting: What's Old is New Again", by Gina Yuan, Thea Rossman, and Keith
Winstein from Stanford University. The artifact consists of all the raw data
from the paper, Jupyter notebooks for analyzing and plotting this data using
the _split throughput heuristic_, and scripts for automating data collection
for replicating the emulation experiments.

## Getting Started

To get started with this artifact, we recommend exploring the Jupyter notebooks
using the raw data from the paper. For further exploration, we then recommend
running emulations yourself and replicating some of the results of the emulation
throughput experiments.

### Setup

All experiments were run on CloudLab x86_64 `rs630` nodes in the Massachusetts
cluster, using Ubuntu 22.04. Any similar x86_64 machine would suffice. Clone
this repository into your home directory. Install dependencies, accepting any
prompts:

```
./deps/node0.sh
```

The instructions assume your working directory is `~/connection-splitting`. The
raw data from emulation benchmarks is written to `~/connection-splitting/data`.
The Jupyter notebooks assume that the raw data is located at
`~/connection-splitting/data`:

```
tar xvf 2025-01-15-data.tar.gz
```

Follow the instructions in [`notebook/`](https://github.com/StanfordSNR/connection-splitting/tree/main/notebook)
to setup your Jupyter notebook kernel and access it from your local machine.

### Explore notebooks

Confirm that you are able to execute all (non-hidden) cells in the following
notebooks to regenerate the figures and analysis in the paper:

* `parameter_exploration.ipynb`
	* Figure 4: Characterize TCP congestion control schemes at 10 Mbit/s.
	* Figure 5: Characterize QUIC congestion control schemes at 10 Mbit/s.
	* Figures 8-12 in the Appendix: Heatmaps of the full parameter space.
* `network_path_analysis.ipynb`
	* Table 3: Apply the heuristic to analyze theoretical split settings.
	* Figure 6: Apply the heuristic to reason about QUIC in split settings.
	* Figure 1 (heuristic only): Identify marquee network settings for Figure 1.
* `network_path_real_data.ipynb`: Figure 1
* `accuracy_analysis.ipynb`: Figure 7

The `network_path_analysis.ipynb` notebook relies purely on cached data to
apply the split throughput heuristic. Feel free to analyze this data yourself.
For further exploration, follow the detailed instructions below for how to
replicate the emulation experiments.

## Detailed Instructions

The measurement study consists of two parts:

1. Characterize various congestion control schemes in a wide parameter space of
_end-to-end_ network settings.
2. Apply the split throughput heuristic to analyze these congestion control
schemes in various _split_ network settings.

The "Getting Started" instructions describe Part 2, and in this section we
describe how to run the emulations for Part 1. The experiments also run
emulations with a real TCP PEP to evaluate the accuracy of the heuristic.

### Run a single emulation

These instructions assume you have followed the setup instructions in "Getting
Started" above. No more dependencies are needed unless you wish to evaluate TCP
BBRv2/3 (which require separate kernels) or Google QUIC (which uses up a lot
of disk space). However, instructions for installing these are available in
[`deps/`](https://github.com/StanfordSNR/connection-splitting/tree/main/deps).

Follow the "Example" instructions in [`emulation/`](https://github.com/StanfordSNR/connection-splitting/tree/main/emulation)
to a run a single emulation. The default network configuration has loss on the
path segment near the client who makes the HTTPS GET request.

### Collect heatmap data

Collect heatmap data for a few congestion control schemes in
`parameter_exploration.ipynb`. We recommend changing the configurations in
the third cell to:

```
NUM_TRIALS = 1
PDF = False
LOSSES = [0, 1, 2, 3, 4]
DELAYS = [1, 20, 40, 60, 80, 100]
BWS = [10]
```

Delete or move the `~/connection-splitting/data` directory so the notebooks
don't rely on the cached data. If a notebook cell states that data is missing
without running the emulation, change the `execute=False` argument to `True`.
Note that TCP BBRv2 and TCP BBRv3 require that you are on the correct Linux
kernel!
