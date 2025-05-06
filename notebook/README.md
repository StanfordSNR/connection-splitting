# Measurement Study

The measurement study consists of two parts:

1. Characterize various congestion control schemes in a wide parameter space of
_end-to-end_ network settings.
2. Apply the split throughput heuristic to analyze these congestion control
schemes in various _split_ network settings.

We also measure congestion control schemes in settings with a real TCP PEP and
evaluate the accuracy of the split throughput heuristic.

The "Setup" and "Figure 1" instructions setup the Jupyter notebook
environment for data collection and analysis, and replicate the results in
Figure 1.

## Setup

The instructions assume your working directory is `~/connection-splitting`. The
raw data from emulation benchmarks is written to `~/connection-splitting/data`.
Automated benchmark execution, data analysis, and plotting is all done in
Jupyter notebooks.

### Python dependencies

Setup a virtual environment:

```
virtualenv -p python3 env
source env/bin/activate
```

Install Python dependencies:

```
pip install jupyterlab
pip install matplotlib
pip install pandas
```

### Jupyter notebook

In the remote server:

```
tmux
source env/bin/activate
jupyter lab --no-browser
```

In a separate shell, forward the SSH port to the local machine:

```
ssh -L 8888:localhost:8888 <USER>@<HOST>
```

In the local machine, copy and paste the URL as instructed:

```
http://localhost:8888/tree?token=<TOKEN>
```

Click `data_analysis.ipynb` or a different notebook.

## Figure 1
