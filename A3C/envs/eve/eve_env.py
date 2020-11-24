from A3C import config

from gym import spaces
from scipy.spatial import distance
from kafka import KafkaConsumer
from json import loads
from random import randint

import math
import time
import gym
# gym.logger.set_level(40)
import numpy as np
import requests


class EveEnv(gym.Env):
    """
    Environment for Media projects involving virtual compressor and Kafka server, following Gym interface
    """

    metadata = {'render.modes': ['human']}

    # def __init__(self):
    def __init__(self, idx=None):

        self.idx = idx
        self.kafka = []
        for topic in config.kafka[self.idx]:
            # print(topic)
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[config.kafka['address']],
                auto_offset_reset='latest',  # Collect at the end of the log. To collect every message: 'earliest'
                enable_auto_commit=True,
                value_deserializer=lambda x: loads(x.decode('utf-8')))
            self.kafka.append(consumer)

        # Included in reset
        self.profiles = {
            0: config.streaming[0],
            1: config.streaming[1],
            2: config.streaming[2]
        }
        self.ep_steps = 0

        self.metrics_logs = open(config.save['path'] + 'metrics_training', 'w')

        # Observation range for the set of states
        high = np.array([np.inf] * 6)
        self.observation_space = spaces.Box(-high, high, dtype=np.float32)

        # Discrete actions relative to network profiles
        self.action_space = spaces.Discrete(len(self.profiles))

        # Initialize states and actions
        self.state = self.reset()
        # self.action = 1

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

        # Execute action
        # print(action)
        while True:
            # vce_req_post = requests.post('http://' + config.vce['address'] + ':' + config.vce['port'] +
            #                              '/bitrate/' + str(self.profiles[action]))
            vce_req_post = requests.post(
                'http://' + config.transcoder[self.idx][0] + ':' + config.transcoder[self.idx][1] +
                '/bitrate/' + str(self.profiles[action]))
            # print('Successful bitrate change on vCE') if vce_req_post == 200 else print('Report to the vCE not found')
            if vce_req_post.status_code:  # if response:  # TODO: Maybe blocking statement. Test
                # print('Successful bitrate change on vCE.')
                break
            else:  # elif vce_req_post.status_code == 404:
                print('vCE not reachable. Not possible to change bitrate.')
                time.sleep(2)

        # Change randomly the traffic background
        # if args.train:  # TODO: Include only in case of training
        #     br_background = randint(1, config.traffic_manager['max_capacity'] / 1000 - 2)
        #     print('Background bitrate: ', br_background)
        #       requests.post('http://' + config.bg_tf['address'] + ':' + config.bg_tf['port'] +
        #               '/bitrate/' + str(br_background * 1000))

        time.sleep(3)  # TODO: Control sleep time

        while True:
            # Get data from transcoders
            if self.idx == 0:  # Information from Server transcoder and Site Transcoder
                # vce_req_get = requests.get('http://' + config.vce['address'] + ':' + config.vce['port']).json()
                # vce2_req_get = requests.get('http://' + config.vce['address'] + ':' + config.vce['port']).json()
                vce_req_get = requests.get(
                    'http://' + config.transcoder[self.idx][0] + ':' + config.transcoder[self.idx][1]).json()
                vce2_req_get = requests.get(
                    'http://' + config.transcoder[self.idx+1][0] + ':' + config.transcoder[self.idx][1]).json()

                if vce_req_get['status'] and vce2_req_get['status']:  # if response:
                    # states['bitrate_in'] += vce_req_get['stats']['act_bitrate']['value']
                    # states['max_bitrate'] = vce_req_get['stats']['max_bitrate']['value']
                    # states['ram_in'] += vce_req_get['stats']['pid_ram']['value']
                    # states['encoding_quality'] += vce_req_get['stats']['enc_quality']['value']
                    break
                else:  # elif vce_req_get.status_code == 404:
                    print('vCE not reachable. Not possible to get data.')
                    time.sleep(2)

            else:  # Information from Site Transcoder
                # vce_req_get = requests.get('http://' + config.vce['address'] + ':' + config.vce['port']).json()
                vce_req_get = requests.get(
                    'http://' + config.transcoder[self.idx][0] + ':' + config.transcoder[self.idx][1]).json()
                vce2_req_get = None
                if vce_req_get['status']:  # if response:
                    break
                else:  # elif vce_req_get.status_code == 404:
                    print('vCE not reachable. Not possible to get data.')
                    time.sleep(2)

        # time.sleep(2)  # Delay due to streaming buffer

        # Consume messages from Kafka server
        # content = []
        # for consumer in self.kafka:
        #     for message in consumer:
        #         message = message.value
        #         break
        #     content.append(message)

        content = []
        # Consume messages from API server
        api_req_get = requests.get(
            'http://' + config.api['address'] + ':' + config.api['port'] + '/api/probe/sensor' +
            str(self.idx + 1)).json()
        content.append(api_req_get)

        time.sleep(3)  # Correlation time between probes

        api_req_get = requests.get(
            'http://' + config.api['address'] + ':' + config.api['port'] + '/api/probe/sensor' +
            str(self.idx+2)).json()
        content.append(api_req_get)

        if self.idx == 0:
            self.state = [
                float(vce_req_get['stats']['bitrate']['value']),
                float(vce2_req_get['stats']['bitrate']['value']),
                float(vce_req_get['stats']['max_bitrate']['value']),
                float(vce_req_get['stats']['enc_quality']['value']),
                float(vce_req_get['stats']['pid_ram']['value']),
                # float(content[0]['value']['mos'])
                float(content[0]['mos'])
            ]
        else:
            self.state = [
                float(vce_req_get['stats']['bitrate']['value']),
                # float(content[1]['value']['bitrate']),
                float(content[1]['bitrate']),
                float(vce_req_get['stats']['max_bitrate']['value']),
                float(vce_req_get['stats']['enc_quality']['value']),
                float(vce_req_get['stats']['pid_ram']['value']),
                # float(content[0]['value']['mos'])
                float(content[0]['mos'])
            ]

        # Reward functions
        rewards = []

        # Reward based on MOS [0, 84.75]
        rew_mos = math.exp(4.5 * math.tanh(content[1]['mos'] - 2.5))

        # Reward profile [0, 16]
        rew_prof = 2.5 * (math.exp(2 - action)-1)

        # Total reward [0, 100]
        reward = rew_mos + rew_prof

        rewards.extend((reward, rew_mos, rew_prof))
        # print(rewards)

        # info = {}
        done = False
        if self.ep_steps == config.training['report']:
            done = True
            self.ep_steps = 0

        self.metrics_logs.write(
            str(self.state[0]) + '\t' +  # Bitrate in
            str(self.state[1]) + '\t' +  # Bitrate out
            str(self.state[2]) + '\t' +  # Max bitrate in
            str(self.state[3]) + '\t' +  # Encoding quality in
            str(self.state[4]) + '\t' +  # RAM in
            str(self.state[5]) + '\t' +  # MOS in
            str(content[0]['mos']) + '\t' +  # MOS out
            # str(self.action) + '\t' +  # Previous action
            str(action) + '\t' +  # Predicted action
            str(rewards[0]) + '\t' +  # Total Rewards
            str(rewards[1]) + '\t' +  # MOS rewards
            str(rewards[2]) + '\n'  # Profile rewards
                                )
        self.metrics_logs.flush()

        # self.action = action

        # Change profiles if it is not central transcoder, limited by the maximum bitrate
        if self.idx != 0:
            self.profiles = {
                0: float(vce_req_get['stats']['max_bitrate']['value']),
                1: float(vce_req_get['stats']['max_bitrate']['value']) / 2,
                2: float(vce_req_get['stats']['max_bitrate']['value']) / 5
            }

        return self.state, rewards[0], done, info

    def reset(self):
        """
        Reset the states of the environment to the initial states

        :return: self.state: Default state of the environment
        """

        # self.state = np.zeros(self.observation_space.shape[0])
        self.state = [
            float(20000),
            float(20000),
            float(20000),
            float(0),
            float(0),
            float(0)
        ]
        self.profiles = {
            0: config.streaming[0],
            1: config.streaming[1],
            2: config.streaming[2]
        }
        # requests.post(
        #     'http://' + config.vce['address'] + ':' + config.vce['port'] + '/bitrate/' + config.streaming[1])
        requests.post('http://' + config.transcoder[self.idx][0] + ':' + config.transcoder[self.idx][1])
        self.ep_steps = 0
        return np.array(self.state)

    def render(self, mode='human', close=False):
        """
        Render the environment to the screen

        :param mode:
        :param close:
        :return: None
        """
        # if not self.ep_steps == 0:  # TODO: Think to include it
        #     print('MOS: '.format(self.mos))
        #     print('Bitrate from vCE: '.format(self.bitrate_in))
        #     print('Bitrate from probe: '.format(self.bitrate_out))
        pass
