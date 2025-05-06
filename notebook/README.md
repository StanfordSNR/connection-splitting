# Notebook Setup

The instructions assume your working directory is `~/connection-splitting`. The
raw data from emulation benchmarks is written to `~/connection-splitting/data`.
Automated benchmark execution, data analysis, and plotting is all done in
Jupyter notebooks.

## PDF output directory

Make a directory for generating PDF figures:

```
mkdir notebook/output/
```

## Python dependencies

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

## Jupyter notebook

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

Click `parameter_exploration.ipynb` or a different notebook.
