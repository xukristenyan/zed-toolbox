# Zed-Toolbox

This is a toolbox for connecting, streaming, visualizing, and recording a Zed camera in robotics research.

## Installation

#### Step 1

Download the SDK from [Zed official website](https://www.stereolabs.com/developers/release/5.1) according to your computer settings.

#### Step 2

Install the downloaded SDK following this [guide](https://www.stereolabs.com/docs/development/zed-sdk/linux).

#### Step 3

Build python API:

```
conda create -n zed python=3.10 && conda activate
cd /usr/local/zed
python get_python_api.py
```

#### Step 4

Install the api with the wheel built in Step 3: 
```
uv add /usr/local/zed/pyzed-5.1-cp310-cp310-linux_x86_64.whl
```

Or just run `uv sync`.