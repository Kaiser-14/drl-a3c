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
# from random import randint
import random

from A3C import config


class EveEnv(gym.Env):
	"""
	Environment for Media projects involving virtual compressor and Kafka server, following Gym interface
	"""

	metadata = {'render.modes': ['human']}

	# FIXME: Support index in register environment
	def __init__(self, idx=0):

		assert len(config.probe['kafka']['address']) == len(config.probe['kafka']['topic'])

		self.idx = idx
		self.kafka = []
		# if idx is not None:
		if config.probe['data_plane'] == 'kafka':
			for topic in config.probe['kafka']['topic'][0]:
				# print(topic)
				consumer = KafkaConsumer(
					topic,
					bootstrap_servers=[config.probe['kafka']['address'][idx]],
					auto_offset_reset='latest',  # Collect at the end of the log. To collect every message: 'earliest'
					enable_auto_commit=True,
					value_deserializer=lambda x: loads(x.decode('utf-8')))
				self.kafka.append(consumer)

		self.profiles = config.transcoder['profile']
		self.ep_steps = 0
		self.br_background = 15

		self.metrics_logs = open(config.training['save_path'] + 'metrics_training_' + str(self.idx), 'w')

		# Observation range for the set of states
		self.n_states = 11
		high = np.array([np.inf] * self.n_states)
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

		# Time to stabilize bitrate in vCE
		time.sleep(5)  # TODO: Control sleep time

		# Get data from transcoders
		while True:
			# Information from server transcoder and site transcoder
			vce_server = requests.get(
				'http://' + config.transcoder['address'][0]
			)

			if vce_server.status_code == 200:
				break
			else:
				print('vCE not reachable. Not possible to get data.')
				time.sleep(2)

		vce_metrics = vce_server.json()

		# Time to analyze streaming content from probe
		time.sleep(15)

		# Probe metrics model
		probe_metrics = {
			'blockiness': None,
			'spatial_activity': None,
			'block_loss': None,
			'blur': None,
			'temporal_activity': None,
		}

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
			api_req_get = None
			while not api_req_get:
				api_req_get = requests.get(config.probe['rest']['address'][self.idx])
				probe_metrics = api_req_get.json()[self.idx]['value']
				if probe_metrics['blockiness'] is None:
					api_req_get = None
					time.sleep(5)

				print(probe_metrics)

		else:
			print('Check data consumption in config file')
			exit(0)

		# Quantize states
		self.state = [
			float(round(vce_metrics['stats']['act_bitrate']['value'], -3) / 1e+5),
			float(vce_metrics['stats']['max_bitrate']['value'] / 1e+5),
			float(vce_metrics['stats']['enc_quality']['value'] / 1e+2),
			float(round(vce_metrics['stats']['pid_cpu']['value'], 0) / 1e+3),
			float(round(vce_metrics['stats']['pid_ram']['value'], -6) / 1e+9),
			float(self.br_background/10),
			# float(vce_metrics['stats']['num_fps']['value'] / 100),
			# float(vce_site['stats']['act_bitrate']['value']),
			# float(vce_site['stats']['max_bitrate']['value']),
			# float(vce_site['stats']['enc_quality']['value']),
			# float(vce_site['stats']['pid_ram']['value']),
			# float(vce_site['stats']['num_fps']['value']),
			float(round(probe_metrics['blockiness'], 2)),
			float(round(probe_metrics['spatial_activity'], 0) / 1e+3),
			float(round(probe_metrics['block_loss'], 0) / 1e+3),
			float(round(probe_metrics['blur'], 2) / 1e+1),
			float(round(probe_metrics['temporal_activity'], 0) / 1e+3),
		]
		print(self.state)

		assert self.n_states == len(self.state), 'State should be equal number to defined number of states'

		rewards = []

		# print(float(probe_metrics['blockiness']))
		# print(float(probe_metrics['block_loss']))
		reward_blockiness = 110*math.tanh(probe_metrics['blockiness']-0.55)
		reward_blockloss = -min(max(0, probe_metrics['block_loss']-4), 20)
		reward_quality = reward_blockiness + reward_blockloss
		# reward_quality = 50*(
		# 		1/(1 + np.exp(-(float(probe_metrics['blockiness'])/float(probe_metrics['block_loss']+0.0001)-2.5))))

		reward_profile = 6.0 * action  # 6.0 * action

		# Enable in case of including several rewards
		# Total reward
		reward = reward_quality + reward_profile
		rewards.extend((reward, reward_quality, reward_profile))
		# print(rewards)

		self.metrics_logs.write(
			str(format(datetime.datetime.now().timestamp(), '.0f')) + '\t' +
			str(action) + '\t' +  # Predicted action
			str(format(self.state[0] * 1e+2, '.0f')) + '\t' +  # Actual bitrate site transcoder
			str(format(self.state[1] * 1e+2, '.0f')) + '\t' +  # Maximum bitrate site transcoder
			str(format(self.state[2] * 1e+2, '.0f')) + '\t' +  # Encoding quality site transcoder
			str(format(self.state[3] * 1e+3, '.0f')) + '\t' +  # CPU usage site transcoder
			str(format(self.state[4] * 1e+3, '.0f')) + '\t' +  # RAM usage site transcoder
			str(format(self.state[5] * 10, '.0f')) + '\t' +  # Bitrate of traffic background
			str(format(self.state[6], '.2f')) + '\t' +  # Blockiness
			str(format(self.state[7] * 1e+3, '.0f')) + '\t' +  # Spatial activity
			str(format(self.state[8] * 1e+3, '.0f')) + '\t' +  # Block loss
			str(format(self.state[9] * 1e+1, '.2f')) + '\t' +  # Blur
			str(format(self.state[10] * 1e+3, '.0f')) + '\t' +  # Temporal Activity
			str(format(rewards[0], '.2f')) + '\n'  # Total Rewards
		)
		self.metrics_logs.flush()

		# info = {}
		done = False
		if self.ep_steps == config.training['model_report']:
			done = True
			self.ep_steps = 0
			self.br_background = random.choice([0.5, 1, 2, 5, 7, 15])  # randint(1, 15)
			requests.post(
				'http://' + config.transcoder['background'][0] + '/bitrate/' + str(self.br_background * 1000)
			)
			print('Background bitrate changed to {} Mbps'.format(self.br_background))

		# self.action = action

		# Adapt in case of training with central transocder
		# Change profiles if it is not central transcoder, limited by the maximum bitrate
		# if self.idx != 0:
		#     self.profiles = {
		#         0: float(vce_req_get['stats']['max_bitrate']['value']),
		#         1: float(vce_req_get['stats']['max_bitrate']['value']) / 2,
		#         2: float(vce_req_get['stats']['max_bitrate']['value']) / 5
		#     }

		print('-------')

		return np.array(self.state), reward, done, info

	def reset(self):
		"""
		Reset the states of the environment to the initial states

		:return: self.state: Default state of the environment
		"""
		# Random uniform values, except for bitrate (actual and maximum)
		self.state = np.random.uniform(low=-0.01, high=0.01, size=(1, self.n_states))[0]

		# Refresh vCE
		requests.get(
			'http://' + config.transcoder['address'][self.idx] + '/refresh/'
		)

		# Time to restart ffmpeg in vCE
		time.sleep(7)

		# Reset site transcoder to maximum bitrate
		requests.post(
			'http://' + config.transcoder['address'][self.idx] + '/bitrate/' + str(self.profiles[2])
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
