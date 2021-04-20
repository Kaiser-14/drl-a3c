import datetime
import math
import time
from json import loads

import gym
# gym.logger.set_level(40)
import numpy as np
import requests
from gym import spaces
from kafka import KafkaConsumer

from A3C import config


class EveEnv(gym.Env):
    """
    Environment for Media projects involving virtual compressor and Kafka server, following Gym interface
    """

    metadata = {'render.modes': ['human']}

    # def __init__(self):
    def __init__(self, idx):

        # TODO: Add assert of every config parameter. For example, same lenght of rest address and number of parallel agents

        self.idx = idx
        self.kafka = []
        if idx is not None:
            for topic in config.probe['kafka']['topic'][0]:
                # print(topic)
                consumer = KafkaConsumer(
                    topic,
                    bootstrap_servers=[config.probe['kafka']['address'][idx]],
                    auto_offset_reset='latest',  # Collect at the end of the log. To collect every message: 'earliest'
                    enable_auto_commit=True,
                    value_deserializer=lambda x: loads(x.decode('utf-8')))
                self.kafka.append(consumer)

        # Included in reset
        # self.profiles = {
        #     0: config.streaming[0],
        #     1: config.streaming[1],
        #     2: config.streaming[2]
        # }
        self.profiles = config.transcoder['profile']
        self.ep_steps = 0

        self.metrics_logs = open(config.training['save_path'] + 'metrics_training_' + self.idx, 'w')

        # Observation range for the set of states
        high = np.array([np.inf] * 9)
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

        # Post request to transcoder to change bitrate based on action
        while True:
            # Change bitrate of site transcoder
            vce_br = requests.post(
                'http://' + config.transcoder['address'][self.idx] + '/bitrate/' + str(self.profiles[action])
            )

            # Break loop in case of received information
            if vce_br.status_code == 200:
                # print('Successful bitrate change on vCE.')
                break
            else:
                print('vCE not reachable. Not possible to change bitrate.')
                time.sleep(2)

        time.sleep(3)  # TODO: Control sleep time

        # Get data from transcoders
        while True:
            # Information from server transcoder and site transcoder
            vce_server = requests.get(
                'http://' + config.transcoder['address'][0]
            ).json()
            # FIXME: Control index
            vce_site = requests.get(
                'http://' + config.transcoder['address'][self.idx]
            ).json()

            # Break loop in case of received information
            if vce_server['status'] and vce_site['status'] == 200:
                break
            else:
                print('vCE not reachable. Not possible to get data.')
                time.sleep(2)

        # time.sleep(2)  # Delay due to streaming buffer

        # Probe metrics model
        probe_metrics = {'blockiness': None, 'spatial_activity': None, 'block_loss': None, 'blur': None,
                         'temporal_activity': None}

        # Consume messages from Kafka server
        if config.probe['data_plane'] == 'kafka':
            content = []
            for consumer in self.kafka:
                for message in consumer:
                    message = message.value
                    break
                content.append(message)

            for key, value in zip(probe_metrics.keys(), content):
                probe_metrics[key] = value

        # Consume messages from API server
        elif config.probe['data_plane'] == 'rest':
            api_req_get = requests.get(config.probe['rest']['address'][self.idx])
            probe_metrics = api_req_get.json()[self.idx]['value']

        else:
            print('Check data consumption in config file')
            exit(0)

        time.sleep(3)  # FIXME: Correlation time between probes

        # TODO: Add FPS from vCE
        # TODO: Cast Ram from bytes to MB
        self.state = [
            float(vce_server['stats']['act_bitrate']['value']),
            float(vce_server['stats']['max_bitrate']['value']),
            float(vce_server['stats']['enc_quality']['value']),
            float(vce_server['stats']['pid_ram']['value']),
            float(vce_site['stats']['act_bitrate']['value']),
            float(vce_site['stats']['max_bitrate']['value']),
            float(vce_site['stats']['enc_quality']['value']),
            float(vce_site['stats']['pid_ram']['value']),
            float(probe_metrics['blockiness']),
            float(probe_metrics['spatial_activity']),
            float(probe_metrics['block_loss']),
            float(probe_metrics['blur']),
            float(probe_metrics['temporal_activity']),
        ]

        # Reward functions
        # Game_5
        # Con Block Loss altos (errores), bajo SA (30), bajo Blockiness (0.058), bajo Blur (1.6)
        # Con Block Loss bajos (no errores), alto SA (62), alto Blockiness (0.75), alto Blur (2.3)

        # Game_10
        # Con Block Loss altos (errores), bajo SA (44), bajo Blockiness (0.009), bajo Blur (2.08)
        # Con Block Loss bajos (no errores), alto SA (60.97), alto Blockiness (0.79), alto Blur (2.78)

        # Game_30
        # Con Block Loss altos (errores) (14.26), bajo SA (20.83), bajo Blockiness (0.69), bajo Blur (3.16)
        # Con Block Loss bajos (no errores), alto SA (62), alto Blockiness (0.85), alto Blur (3.34)

        # Conclusiones, mantener formula de recompensa. Todos los de arriba pueden meterse como estados del modelo.
        # El blur puede servir como multiplicador de perfil, que en este caso quitariamos esa recompensa de anterior
        # algoritmo

        rewards = []

        # TODO: New rewards
        # FIXME: Possible to include blut to emphasize profiles
        # rew_qi = 50*(1/(1 + np.exp(-(blocking/block_loss-3.0))))

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
        if self.ep_steps == config.training['model_report']:
            done = True
            self.ep_steps = 0

        self.metrics_logs.write(
            # str(self.action) + '\t' +  # Previous action
            str(datetime.datetime.now().timestamp()) + 't' +
            str(action) + '\t' +  # Predicted action
            str(format(self.state[0], '.2f')) + '\t' +  # Actual bitrate site transcoder
            str(format(self.state[1], '.0f')) + '\t' +  # Maximum bitrate site transcoder
            str(format(self.state[2], '.40f')) + '\t' +  # Encoding quality site transcoder
            str(format(self.state[3], '.0f')) + '\t' +  # RAM usage site transcoder
            str(format(self.state[4], '.2f')) + '\t' +  # Actual bitrate server transcoder
            str(format(self.state[5], '.0f')) + '\t' +  # Maximum bitrate server transcoder
            str(format(self.state[6], '.0f')) + '\t' +  # Encoding quality server transcoder
            str(format(self.state[7], '.0f')) + '\t' +  # RAM usage server transcoder
            str(format(self.state[8], '.4f')) + '\t' +  # Blockiness
            str(format(self.state[9], '.4f')) + '\t' +  # Spatial activity
            str(format(self.state[10], '.4f')) + '\t' +  # Block loss
            str(format(self.state[11], '.4f')) + '\t' +  # Blur
            str(format(self.state[12], '.4f')) + '\t' +  # Temporal Activity
            str(format(rewards[0], '.2f')) + '\t' +  # Total Rewards
            str(format(rewards[1], '.2f')) + '\t' +  # MOS rewards
            str(format(rewards[2], '.2f')) + '\n'  # Profile rewards
        )
        self.metrics_logs.flush()

        # self.action = action

        # Change profiles if it is not central transcoder, limited by the maximum bitrate
        # TODO: Adapt
        # if self.idx != 0:
        #     self.profiles = {
        #         0: float(vce_req_get['stats']['max_bitrate']['value']),
        #         1: float(vce_req_get['stats']['max_bitrate']['value']) / 2,
        #         2: float(vce_req_get['stats']['max_bitrate']['value']) / 5
        #     }

        return self.state, rewards[0], done, info

    def reset(self):
        """
        Reset the states of the environment to the initial states

        :return: self.state: Default state of the environment
        """
        # Random uniform values, except for bitrate (actual and maximum)
        self.state = np.random.uniform(low=-0.01, high=0.01, size=(1, 13))[0]
        self.state[[0, 1, 4, 5]] = 25000

        # Reset site transcoder to maximum bitrate
        requests.post(
            'http://' + config.transcoder['address'][self.idx] + '/bitrate/' + str(self.profiles[0])
        )

        self.ep_steps = 0
        return np.array(self.state)

    def render(self, mode='human', close=False):
        """
        Render the environment to the screen

        :param mode:
        :param close:
        :return: None
        """
        pass
