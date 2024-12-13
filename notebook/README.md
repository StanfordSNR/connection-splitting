# notebook

## Setup

Setup virtual environment:

```
virtualenv -p python3 env
source env/bin/activate
```

Install Python dependencies:

```
pip install jupyterlab
pip install matplotlib
```

## Jupyter notebook

In the remote server:

```
tmux
jupyterlab --no-browser
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
