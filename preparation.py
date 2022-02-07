# Prepare Python files to deployment

import os

while True:
    print('Select the project to prepare:')
    print('[1] 5G-EVE')
    print('[2] 5G-Energy')
    print('[3] Exit')
    project = int(input())

    if project == 1:
        print('5G-EVE selected')
        os.system('sudo rm -rf ./Deployment/a3c-eve/*')

        # input("Press Enter to copy...")
        os.system('cp ./A3C/a3c.py ./Deployment/a3c-eve')
        os.system('cp ./A3C/agent.py ./Deployment/a3c-eve')
        # os.system('cp ./A3C/config.py ./Deployment/a3c-eve')
        os.system('cp -r ./A3C/venv/ ./Deployment/a3c-eve')
        os.system('cp -r ./A3C/envs/ ./Deployment/a3c-eve')
        os.system('sudo rm -rf ./Deployment/a3c-eve/envs/energy')
        os.system('sudo rm -rf ./Deployment/a3c-eve/envs/__pycache__')
        os.system('sudo rm -rf ./Deployment/a3c-eve/envs/eve/__pycache__')

        # input("Press Enter to compile...")
        os.system('python3 -m py_compile Deployment/a3c-eve/a3c.py')
        os.system('python3 -m py_compile Deployment/a3c-eve/agent.py')
        # os.system('python3 -m py_compile Deployment/a3c-eve/config.py')

        # input("Press Enter to compile environment...")
        os.system('python3 -m py_compile Deployment/a3c-eve/envs/__init__.py')
        os.system('python3 -m py_compile Deployment/a3c-eve/envs/eve/__init__.py')
        os.system('python3 -m py_compile Deployment/a3c-eve/envs/eve/eve_env.py')
        os.system('python3 -m py_compile Deployment/a3c-eve/envs/eve/config.py')

        # input("Press Enter to remove files...")
        os.system('sudo rm ./Deployment/a3c-eve/a3c.py')
        os.system('sudo rm ./Deployment/a3c-eve/agent.py')
        # os.system('sudo rm ./Deployment/a3c-eve/config.py')
        os.system('sudo rm ./Deployment/a3c-eve/envs/__init__.py')
        os.system('sudo rm ./Deployment/a3c-eve/envs/eve/__init__.py')
        os.system('sudo rm ./Deployment/a3c-eve/envs/eve/eve_env.py')
        os.system('sudo rm ./Deployment/a3c-eve/envs/eve/config.py')

        # input("Press Enter to place files...")
        os.system('cp ./Deployment/a3c-eve/__pycache__/a3c* ./Deployment/a3c-eve/a3c.pyc')
        os.system('cp ./Deployment/a3c-eve/__pycache__/agent* ./Deployment/a3c-eve/agent.pyc')
        # os.system('cp ./Deployment/a3c-eve/__pycache__/api_server* ./Deployment/a3c-eve/api_server.pyc')
        # os.system('cp ./Deployment/a3c-eve/__pycache__/config* ./Deployment/a3c-eve/config.pyc')
        os.system('cp ./Deployment/a3c-eve/envs/__pycache__/__init__* ./Deployment/a3c-eve/envs/__init__.pyc')
        os.system('cp ./Deployment/a3c-eve/envs/eve/__pycache__/__init__* ./Deployment/a3c-eve/envs/eve/__init__.pyc')
        os.system('cp ./Deployment/a3c-eve/envs/eve/__pycache__/eve_env* ./Deployment/a3c-eve/envs/eve/eve_env.pyc')
        os.system('cp ./Deployment/a3c-eve/envs/eve/__pycache__/api_server* ./Deployment/a3c-eve/api_server.pyc')
        os.system('cp ./Deployment/a3c-eve/envs/eve/__pycache__/config* ./Deployment/a3c-eve/config.pyc')

        os.system('sudo rm -rf ./Deployment/a3c-eve/__pycache__')
        os.system('sudo rm -rf ./Deployment/a3c-eve/envs/__pycache__')
        os.system('sudo rm -rf ./Deployment/a3c-eve/envs/eve/__pycache__')

        # input("Press Enter to execute files...")
        # os.system('source /venv/bin/activate')
        # os.system('python3 ./Deployment/a3c-eve/agent.pyc --train --num-workers 1 --max-eps 100')
        print('5G-EVE prepared')
        break
    elif project == 2:
        print('5G-Energy selected')
        # os.system('rm ./Deployment/a3c-energy/*')
        break
    elif project == 3:
        print('Closing program...')
        break
    else:
        print('Select a correct option.')