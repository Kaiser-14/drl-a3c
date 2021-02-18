# Asynchronous Advantage Actor-Critic implementation for specific environments

## Introduction

This repository implements a Deep Reinforcement Learning algorithm called A3C.  It can be used with different gym environments from cartpole, but they are also developed some personal environments for specific projects.

This project has only be tested 

## Installation

Recommended to install in virtual environment.

### Development environment

#### Clone the repository
```bash
git clone https://github.com/Kaiser-14/drl-a3c.git
cd /drl-a3c/
```
#### Setup virtual environment (skip to install locally)
[Linux/Mac]
```bash
python -m venv venv
source /venv/bin/activate
```

[Windows]
```bash
\venv\Scripts\activate
```

#### Install dependencies
```bash
pip install -r requirements.txt
```

#### Install personal gym environments
```bash
pip install -e .
```

#### Setup gym
```bash
python setup.py install
```


### Execution

#### Setup working directory
```bash
cd /A3C/
```

#### Training mode
```bash
python agent.py --train --num-workers 1
```

#### Play mode
```bash
python agent.py --num-workers 1
```
