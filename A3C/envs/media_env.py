from A3C import config

from gym import spaces
from scipy.spatial import distance
from kafka import KafkaConsumer
from json import loads
from random import randint

import math
import time
import gym
import numpy as np
import requests


class MediaEnv(gym.Env):
    """
    Environment for Media projects involving virtual compressor and Kafka server, following Gym interface
    """

    metadata = {'render.modes': ['human']}

    def __init__(self):

        self.mos = 0
        self.bitrate_in = 0.0
        self.bitrate_out = 0.0

        self.consumer = KafkaConsumer(
            config.kafka['topic'],
            bootstrap_servers=[config.kafka['address']],
            auto_offset_reset='latest',  # Collect at the end of the log. To collect every message: 'earliest'
            enable_auto_commit=True,
            value_deserializer=lambda x: loads(x.decode('utf-8')))

        self.max_br = max(list(x.values())[0] for x in list(PROFILES.values()))
        self.ep_steps = 0

        self.metrics_logs = open(config.save['path'] + 'metrics_training', 'w')

        # Define action and observation spaces
        # Discrete actions relative to network profiles
        self.action_space = spaces.Discrete(len(PROFILES))

        # True observation range. Increase observation space values in order to have failing observations within bounds
        bitrate_ratio = np.array([0, self.max_br + 5]) / self.max_br
        loss_rate = np.array([0, self.max_br + 5]) / config.traffic_manager['max_capacity']
        encoding_qual = np.array([0, 69]) / 69
        ram_usage = np.array([0, 5000]) / 5.000
        # tf_bg = np.array([0, config.traffic_manager['max_capacity']]) / config.traffic_manager['max_capacity']

        low = np.array([bitrate_ratio[0], loss_rate[0], encoding_qual[0], ram_usage[0]])
        high = np.array([bitrate_ratio[1], loss_rate[1], encoding_qual[1], ram_usage[1]])
        self.observation_space = spaces.Box(low, high, dtype=np.float32)

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

        # Execute action
        self.take_action(action)

        # Update states
        self.update_states()

        # Reward functions
        rewards = self.get_reward(action)

        # info = {}
        done = False

        self.metrics_logs.write(str(self.action) + '\t' +
                                str(action) + '\t' +
                                str(rewards[0]) + '\t' +
                                str(rewards[1]) + '\t' +
                                str(rewards[2]) + '\t' +
                                str(rewards[3]) + '\t' +
                                str(rewards[4]) + '\n')
        self.metrics_logs.flush()

        self.action = action

        return self.state, rewards[0], done, info

    def reset(self):
        """
        Reset the states of the environment to the initial states

        :return: self.state: Default state of the environment
        """

        # Sending refresh each time will increase training time, as we have continuous training in this environment
        # requests.get('http://' + config.vce['address'] + ':' + config.vce['port'] + '/refresh/')
        # requests.get('http://' + config.bg_tf['address'] + ':' + config.bg_tf['port'] + '/refresh/')
        # requests.get('http://' + config.probe['address'] + ':' + config.probe['port'] + '/refresh/')
        # time.sleep(5)

        self.state = [np.zeros(self.observation_space.shape[0])]
        self.ep_steps = 0
        return self.state

    def render(self, mode='human', close=False):
        """
        Render the environment to the screen

        :param mode:
        :param close:
        :return: None
        """
        if not self.ep_steps == 0:
            print('MOS: '.format(self.mos))
            print('Bitrate from vCE: '.format(self.bitrate_in))
            print('Bitrate from probe: '.format(self.bitrate_out))

    def update_states(self):
        """
        Update the states of the model, making request to different components to obtain data

        :return: None
        """

        states = {'bitrate_in': 0, 'max_bitrate': 0, 'ram_in': 0, 'encoding_quality': 0, 'resolution': 0,
                  'frame_rate': 0, 'bitrate_out': 0, 'duration': 0, 'mos': 0, 'timestamp': None}

        for i in range(3):
            states = self.get_data(states)

        self.bitrate_in = states['bitrate_in'] / 3
        limiting_bitrate = states['max_bitrate']
        ram_in = states['ram_in'] / 3
        encoding_quality = states['encoding_quality'] / 3
        # self.resolution = states['resolution']
        # self.frame_rate = states['frame_rate'] / 3
        # frame_rate = self.frame_rate = states['frame_rate'] / 3
        self.bitrate_out = states['bitrate_out'] / 3
        # self.duration = states['duration'] / 3
        self.mos = states['mos'] / 3
        timestamp = states['timestamp']

        self.state[0] = float(self.bitrate_out) / self.max_br  # Bitrate ratio
        self.state[1] = abs((float(limiting_bitrate) - float(self.bitrate_out))) / \
            config.traffic_manager['max_capacity']  # Loss rate
        self.state[2] = float(encoding_quality) / 69  # Encoding quality
        self.state[3] = float(ram_in) / 5000.0  # Ram usage
        # self.state[4] =  br_background / (MAX_CAPACITY/1000) # Background traffic

        self.metrics_logs.write(str(timestamp) + '\t' +
                                str(limiting_bitrate) + '\t' +
                                str(self.bitrate_in) + '\t' +
                                str(self.bitrate_out) + '\t' +
                                str(ram_in) + '\t' +
                                str(encoding_quality) + '\t' +
                                str(self.mos) + '\t')

    def take_action(self, action):
        """
        Perform the action to the vCE in order to change the streaming bitrate

        :param action: Predicted action by the model
        :return: None
        """
        # Send API requests to change vCE
        br_predicted = list(PROFILES[action].values())[0]
        while True:
            vce_req_post = requests.post('http://' + config.vce['address'] + ':' + config.vce['port'] +
                                         '/bitrate/' + str(br_predicted * 1000))
            # print('Successful bitrate change on vCE') if vce_req_post == 200 else print('Report to the vCE not found')
            if vce_req_post.status_code == 200:  # if response:
                # print('Successful bitrate change on vCE.')
                break
            else:  # elif vce_req_post.status_code == 404:
                print('vCE not reachable. Not possible to change bitrate.')

        # Change randomly the traffic background
        br_background = randint(1, config.traffic_manager['max_capacity'] / 1000 - 2)
        requests.post('http://' + config.bg_tf['address'] + ':' + config.bg_tf['port'] +
                      '/bitrate/' + str(br_background * 1000))
        time.sleep(4)

    def get_reward(self, action):
        """
        Function to obtain the matrix composed of the defined reward functions

        :param action: Predicted action by the model
        :return: rewards: matrix composed by the values obtained in the reward functions
        """

        rewards = []

        # Reward based on MOS
        if float(self.mos) > 2.5:
            mos_th = float(self.mos) - 2.5
            aux = 2.0
        else:
            mos_th = 2.5 - float(self.mos)
            aux = -2.0
        rew_mos = aux * math.exp(1.5 * mos_th)
        # Reward based on BR
        rew_br = -math.exp(2 * (1 + distance.canberra(float(self.bitrate_in) / 1000, float(self.bitrate_out) / 1000)))
        # Reward smooth
        rew_smooth = 12 * np.log(1 - distance.canberra(action + 1, action + 1))
        # Reward profile
        rew_profile = math.pow(2, (4 - action))

        reward = rew_mos + rew_br + rew_smooth + rew_profile

        rewards.extend((rew_mos, rew_br, rew_smooth, rew_profile, reward))

        return rewards

    def get_data(self, states):
        """
        Function to gather data from components of the system: vCE and Kafka server respectively

        :param states: Matrix of actual states to accumulate 3 iterations of information
        :return: states : Same states input parameter but filled with new data
        """

        # API request to the vCE to gather data
        while True:
            vce_req_get = requests.get('http://' + config.vce['address'] + ':' + config.vce['port']).json()

            if vce_req_get.status_code == 200:  # if response:
                states['bitrate_in'] += vce_req_get['stats']['act_bitrate']['value']
                states['max_bitrate'] = vce_req_get['stats']['max_bitrate']['value']
                states['ram_in'] += vce_req_get['stats']['pid_ram']['value']
                states['encoding_quality'] += vce_req_get['stats']['enc_quality']['value']
                break
            else:  # elif vce_req_get.status_code == 404:
                print('vCE not reachable. Not possible to get data.')

        time.sleep(2)  # Delay due to streaming buffer

        # Consume messages from Kafka server
        for message in self.consumer:
            content = message.value
            states['resolution'] = content['value']['resolution']
            states['frame_rate'] += content['value']['frame_rate']
            states['bitrate_out'] += content['value']['bitrate']
            states['duration'] += content['value']['duration']
            states['mos'] += content['value']['mos']
            states['timestamp'] = content['timestamp']
            break

        return states


# Network profiles of the environment. They are composed by the resolution and the bitrate
PROFILES = {
    0: {1080: 10},
    1: {1080: 7.5},
    2: {1080: 5},
    3: {720: 4},
    4: {720: 2.5},
    5: {720: 1},
}
