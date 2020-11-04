import config
from gym import spaces
import time
import gym
import numpy as np
import requests


class EnergyEnv(gym.Env):
    """
    Environment for Energy projects, following Gym interface
    """
    metadata = {'render.modes': ['human']}

    def __init__(self):
        # eSight data  # TODO: Remove Data once set the state
        # Network devices
        self.cpuUsage = 0.0  # NE average CPU usage
        self.memUsage = 0.0  # NE average Memory usage
        self.DeviceTemperature = 0.0  # Device Temperature
        self.neContrlableRate = 0.0  # Unreachable percentage in a day
        self.nePingRespTime = 0.0  # Responding duration
        self.diskUsage = 0.0  # NE Disk usage
        self.hwPowerConsumption = 0.0  # Power Consumption
        self.hwCurrentPower = 0.0 # Current Power
        self.hwRatedPower = 0.0  # Rated Power
        self.hwPowerConsumptionDelta = 0.0  # Power Consumption in Last Pe
        self.hwSecStatUsage = 0.0  # CPU usage
        self.hwSecStatMemUsage = 0.0  # Memory usage
        self.hwSecStatSessCount = 0.0  # Current CPU session count
        self.hwSecStatSessSpeed = 0.0  # Current CPU session setup rate
        self.cpuUsage = 0.0  # AC average CPU usage
        self.memUsage = 0.0  # AC average Memory usage
        self.diskUsage = 0.0  # AC Disk usage
        self.CpuUsage = 0.0  # Average CPU Usage
        self.ServerBytesIn = 0.0  # Server Inbound Rate
        self.ClientCurConns = 0.0  # Client Concurrent Connection
        self.ClientBytesIn = 0.0  # Client Inbound Rate
        self.ClientTotConns = 0.0  # Client Connection Rate
        self.ClientBytesOut = 0.0  # Client Outbound Rate
        self.ServerBytesOut = 0.0  # Server Outbound Rate
        self.MemUsage = 0.0  # Average Memory Usage


        # Virtual Resources
        self.CpuUsage = 0.0  # Average usage of the VM CPU in a collection period
        self.MemUsage = 0.0  # Average  usage  of  the  VM memory in a collection period
        self.NetOutputSpeed = 0.0  # Outbound network traffic of the VM in a collection period
        self.NetInputSpeed = 0.0  # Inbound network traffic of the VM in a collection period
        self.DiskIoInputSpeed = 0.0  # Total traffic written in the VM disk in a collection period
        self.DiskIoOutputSpeed = 0.0  # Total traffic read from the VM disk in a collection period
        self.DiskUsage = 0.0  # Average usage of the VM disk in a collection period
        self.DiskIoInputDelay = 0.0  # Delay  in  reading  data  from  a VM  disk  within  a  collection period
        self.DiskIoOutputDelay = 0.0  # Delay in writing data to a VM disk within a collection period
        self.DiskIoWriteFrequency = 0.0  # Number of times for the VM to write  data  in  the  disk  in  a collection period
        self.DiskIoReadFrequency = 0.0  # Number of times for the VM to read  data  from  the  disk  in  a collection period
        self.UsedMemorySize = 0.0  # Memory used by the VM
        self.FreeMemorySize = 0.0  # Memory not used by the VM

        # Probe
        self.voltage = 0.0  # Network voltage
        self.current = 0.0  # Current consumption (A)
        self.active_power = 0.0  # Power consumption (W)
        self.power_factor = 0.0  # Power factor

        self.ep_steps = 0

        self.metrics_logs = open(config.save['path'] + 'metrics_training', 'w')

        # # Observation range for the set of states
        high = np.array([np.inf] * 24)
        self.observation_space = spaces.Box(-high, high, dtype=np.float32)

        # TODO: Define it. # Maybe include in terms of matrix. For example, (1,1) -> Increase first Phoronix.
        # (2, 0) -> Decrease power in second Phoronix. Example in
        # https://github.com/openai/gym/blob/master/gym/envs/box2d/bipedal_walker.py
        # Discrete actions relative to network profiles
        self.action_space = spaces.Discrete(len(PROFILES))

        # Initialize states and actions
        self.state = None
        self.action = None

    def step(self, action):
        """
        Execute one time step within the environment

        :param action: Predicted action by the model
        :return: self.state: agent's observation of the current environment
        :return: rewards[0]: amount of reward returned after previous action
        :return: done: whether the episode has ended, in which case further step() calls will return undefined results
        :return: info: contains auxiliary diagnostic information
        """

        info = {}
        self.ep_steps += 1
        if self.ep_steps == config.training['report']:
            info = True
            self.ep_steps = 0

        # TODO: Execute action to Phoronix
        # self.take_action(action)
        # requests.post()
        # time.sleep(6)  # Think about not having every sensor data in next steps

        # Update states
        # self.update_states()

        # Get data from sources
        while True:
            api_req_get = requests.get('http://' + config.api['address'] + ':' + config.api['port'] + '/api/probe').json()
            # TODO: Enable request
            # esight_req_get = requests.get('http://' + config.esight['address'] + ':' + config.esight['port'],
            #                               auth=(config.esight['user'], config.esight['passw'])).json()

            # if esight_req_get.status_code and api_req_get['sensor6'] is not None:
            # while True:
            # for _, sensor in api_req_get.json().items():
            # for sensor in api_req_get.json().values():
            #     print(sensor)
            #     for key in sensor.keys():
            #         print(key)
            #         print(sensor[key])
            # if any(sensor[key] is None for key in sensor.keys() for sensor in api_req_get.json().values()):
            # TODO: Check in the same way with eSight request. Loop until every data sensor is filled
            if all(sensor[key] is not None for sensor in api_req_get.values() for key in sensor.keys()):
                break
            # if api_req_get.status_code == 200 and api_req_get.json()['sensor6']['voltage'] is not None:  # if response:
            #     break
            # elif api_req_get.json()['sensor6']['voltage'] is None:
            #     time.sleep(2.5)
            else:  # elif esight_req_get.status_code == 404:
                # print('Retrying to collect data...')
                time.sleep(2.5)  # Adjustment done based on physical probe

        # TODO: Adapt observation space based on state dimensions
        self.state = [
            float(api_req_get['sensor1']['voltage']),
            float(api_req_get['sensor1']['current']),
            float(api_req_get['sensor1']['active_power']),
            float(api_req_get['sensor1']['power_factor']),
            float(api_req_get['sensor2']['voltage']),
            float(api_req_get['sensor2']['current']),
            float(api_req_get['sensor2']['active_power']),
            float(api_req_get['sensor2']['power_factor']),
            float(api_req_get['sensor3']['voltage']),
            float(api_req_get['sensor3']['current']),
            float(api_req_get['sensor3']['active_power']),
            float(api_req_get['sensor3']['power_factor']),
            float(api_req_get['sensor4']['voltage']),
            float(api_req_get['sensor4']['current']),
            float(api_req_get['sensor4']['active_power']),
            float(api_req_get['sensor4']['power_factor']),
            float(api_req_get['sensor5']['voltage']),
            float(api_req_get['sensor5']['current']),
            float(api_req_get['sensor5']['active_power']),
            float(api_req_get['sensor5']['power_factor']),
            float(api_req_get['sensor6']['voltage']),
            float(api_req_get['sensor6']['current']),
            float(api_req_get['sensor6']['active_power']),
            float(api_req_get['sensor6']['power_factor']),
        ]

        # time.sleep(10)  # TODO: Think about sleep

        # TODO: Enable Free resources from API
        requests.delete('http://' + config.api['address'] + ':' + config.api['port'] + '/api/probe')

        # self.metrics_logs.write(str(self.cpu_usage) + '\t' +
        #                         str(self.curr_pwr) + '\t' +
        #                         str(self.rated_power) + '\t' +
        #                         str(self.mem_usage))

        # Reward functions
        rewards = []

        # Reward based on MOS
        rew_cpu = float(api_req_get['sensor1']['voltage'])
        rew_pwr = float(api_req_get['sensor2']['current'])
        rew_rat = float(api_req_get['sensor3']['active_power'])
        rew_mem = float(api_req_get['sensor4']['power_factor'])

        reward = rew_cpu + rew_pwr + rew_rat + rew_mem

        rewards.extend((rew_cpu, rew_pwr, rew_rat, rew_mem, reward))

        # info = {}
        done = False
        if self.ep_steps == config.training['report']:
            done = True
            self.ep_steps = 0

        # TODO: Modify logs based on created rewards
        self.metrics_logs.write(str(self.action) + '\t' +
                                str(action) + '\t' +
                                str(rewards[0]) + '\t' +
                                str(rewards[1]) + '\t' +
                                str(rewards[2]) + '\t' +
                                str(rewards[3]) + '\t' +
                                str(rewards[4]) + '\n')
        self.metrics_logs.flush()

        self.action = action

        return np.array(self.state), rewards[0], done, info

    def reset(self):
        """
        Reset the states of the environment to the initial states

        :return: self.state: Default state of the environment
        """

        # TODO: Define it. As continuos environment, it is not needed to clear states
        self.state = np.zeros(self.observation_space.shape[0])
        self.ep_steps = 0
        return np.array(self.state)

    def render(self, mode='human', close=False):
        """
        Render the environment to the screen

        :param mode:
        :param close:
        :return: None
        """
        # TODO: Think about to render some graphics
        # if not self.ep_steps == 0:
            # print('hw_pwr_consumption: '.format(self.hw_pwr_consumption))
            # print('cpu_usage: '.format(self.cpu_usage))
            # print('curr_pwr: '.format(self.curr_pwr))
        return None


# TODO: Define actions profile. Network profiles of the environment. They are composed by the resolution and the bitrate
PROFILES = {
    0: {1080: 10},
    1: {1080: 7.5},
    2: {1080: 5},
    3: {720: 4},
    4: {720: 2.5},
    5: {720: 1},
}
