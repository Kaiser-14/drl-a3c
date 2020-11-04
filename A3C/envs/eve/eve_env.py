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

    def __init__(self):

        self.consumer = KafkaConsumer(
            config.kafka['topic'],
            bootstrap_servers=[config.kafka['address']],
            auto_offset_reset='latest',  # Collect at the end of the log. To collect every message: 'earliest'
            enable_auto_commit=True,
            value_deserializer=lambda x: loads(x.decode('utf-8')))

        self.max_br = max(list(x.values())[0] for x in list(PROFILES.values()))
        self.ep_steps = 0

        self.metrics_logs = open(config.save['path'] + 'metrics_training', 'w')

        # Observation range for the set of states
        high = np.array([np.inf] * 4)  # TODO: Set correctly number of states
        self.observation_space = spaces.Box(-high, high, dtype=np.float32)

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

        # Execute action
        # self.take_action(action)
        # print(action)
        br_predicted = list(PROFILES[action].values())[0]
        while True:
            vce_req_post = requests.post('http://' + config.vce['address'] + ':' + config.vce['port'] +
                                         '/bitrate/' + str(br_predicted * 1000))
            # print('Successful bitrate change on vCE') if vce_req_post == 200 else print('Report to the vCE not found')
            if vce_req_post.status_code:  # if response:
                # print('Successful bitrate change on vCE.')
                break
            else:  # elif vce_req_post.status_code == 404:
                print('vCE not reachable. Not possible to change bitrate.')
                time.sleep(2)  # TODO: Think to add counter to avoid loop

        # Change randomly the traffic background
        # if args.train:  # TODO: Include only in case of training
        #     br_background = randint(1, config.traffic_manager['max_capacity'] / 1000 - 2)
        #     print('Background bitrate: ', br_background)
        #       requests.post('http://' + config.bg_tf['address'] + ':' + config.bg_tf['port'] +
        #               '/bitrate/' + str(br_background * 1000))

        time.sleep(3)  # TODO: Control sleep time

        while True:
            vce_req_get = requests.get('http://' + config.vce['address'] + ':' + config.vce['port']).json()

            if vce_req_get['status']:  # if response:
                # states['bitrate_in'] += vce_req_get['stats']['act_bitrate']['value']
                # states['max_bitrate'] = vce_req_get['stats']['max_bitrate']['value']
                # states['ram_in'] += vce_req_get['stats']['pid_ram']['value']
                # states['encoding_quality'] += vce_req_get['stats']['enc_quality']['value']
                break
            else:  # elif vce_req_get.status_code == 404:
                print('vCE not reachable. Not possible to get data.')
                time.sleep(2)

        time.sleep(2)  # Delay due to streaming buffer

        # Consume messages from Kafka server
        content = None
        for message in self.consumer:  # TODO: Think how to implement in a cleaning way
            content = message.value
            # states['resolution'] = content['value']['resolution']
            # states['frame_rate'] += float(content['value']['frame_rate'])
            # states['bitrate_out'] += float(content['value']['bitrate'])
            # states['duration'] += float(content['value']['duration'])
            # states['mos'] += float(content['value']['mos'])
            # states['timestamp'] = content['timestamp']
            break

        # TODO: Adapt observation space based on state dimensions
        self.state = [
            float(float(content['value']['bitrate'])) /
                 (vce_req_get['stats']['max_bitrate']['value'] * 1000),  # Bitrate ratio
            abs((float(vce_req_get['stats']['max_bitrate']['value']) -
                 float(vce_req_get['stats']['max_bitrate']['value']))) /
                 config.traffic_manager['max_capacity'],  # Loss rate. # FIXME: We do not have max capacity
            float(vce_req_get['stats']['enc_quality']['value']) / 69,  # Encoding quality # FIXME: I'd remove it
            float(vce_req_get['stats']['pid_ram']['value']) / 800000000.0,  # # Ram usage # FIXME: I'd remove it
            # Blur, block, and every other spec provided by the quality probe
            # FIXME: Think to include bitrate in the vCE: vce_req_get['stats']['act_bitrate']['value']
            # br_background / (MAX_CAPACITY/1000) # Background traffic
        ]

        # Reward functions
        # rewards = self.get_reward(action)
        rewards = []

        # Reward based on MOS
        if float(content['value']['mos']) > 2.5:
            mos_th = float(content['value']['mos']) - 2.5
            aux = 2.0
        else:
            mos_th = 2.5 - float(content['value']['mos'])
            aux = -2.0
        rew_mos = aux * math.exp(1.5 * mos_th)
        # Reward based on BR
        rew_br = -math.exp(2 * (1 + distance.canberra(float(vce_req_get['stats']['act_bitrate']['value'])
                                                      / 1000, float(content['value']['bitrate']) / 1000)))
        # Reward smooth
        rew_smooth = 12 * np.log(1 - distance.canberra(int(action) + 1, action + 1))  # FIXME: Check behaviour
        # Reward profile
        rew_profile = math.pow(2, (4 - action))

        reward = rew_mos + rew_br + rew_smooth + rew_profile

        rewards.extend((rew_mos, rew_br, rew_smooth, rew_profile, reward))
        print(rewards)

        # info = {}
        done = False
        if self.ep_steps == config.training['report']:
            done = True
            self.ep_steps = 0

        self.metrics_logs.write(str(vce_req_get['stats']['max_bitrate']['value']) + '\t' +
                                str(vce_req_get['stats']['act_bitrate']['value']) + '\t' +
                                str(content['value']['bitrate']) + '\t' +
                                # str(ram_in) + '\t' +
                                # str(encoding_quality) + '\t' +
                                str(content['value']['mos']) + '\t' +
                                str(self.action) + '\t' +
                                str(action) + '\t' +
                                str(rewards[0]) + '\t' +
                                str(rewards[1]) + '\t' +
                                str(rewards[2]) + '\t' +
                                str(rewards[3]) + '\t' +
                                str(rewards[4]) + '\n'
                                )
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

        self.state = np.zeros(self.observation_space.shape[0])  # TODO: Set default bitrate, etc.
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


# Network profiles of the environment. They are composed by the resolution and the bitrate
# PROFILES = {
#     0: {1080: 10},
#     1: {1080: 7.5},
#     2: {1080: 5},
#     3: {720: 4},
#     4: {720: 2.5},
#     5: {720: 1},
# }
PROFILES = {
    0: {1080: 30},
    1: {1080: 10},
    2: {1080: 2},
}
