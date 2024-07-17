# ChatziFISH

Source code used to analyse smFISH data in Chatzitheodoridou et al. 2024

# System requirements
Windows 10 64 bit, macOS > 10

# Installation
## Typical installation time: 20 minutes
1. Install [Anaconda](https://www.anaconda.com/products/individual) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) for **Python 3.9**.
*IMPORTANT: For Windows make sure to choose the **64 bit** version*.
2. Open a terminal and navigate to ChatziFISH folder (this folder)
3. Update conda with `conda update conda`. Optionally, consider removing unused packages with the command `conda clean --all`
4. Update pip with `python -m pip install --upgrade pip`
5. Create a virtual environment with the command `conda create -n chatzi python=3.9`
6. Activate the environment with the command `conda activate chatzi`
7. Install all the dependencies with `pip install -r requirements.txt`




