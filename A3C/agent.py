import argparse
import multiprocessing
import os
import threading
import time
from queue import Queue

import gym
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

import a3c
import config

# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # or any {'0', '1', '2'}

# Check GPU
# print('Num GPUs Available: ', len(tf.config.list_physical_devices('GPU')))

# Check CPU-GPU physical devices
# visible_devices = tf.config.get_visible_devices()
# for devices in visible_devices:
#   print(devices)

# Set GPU. Check before previous line. If not, set correctly the corresponding number in next line
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

parser = argparse.ArgumentParser(description='Run A3C algorithm.')
# parser.add_argument('--algorithm', default='a3c', type=str,
#                     help='Choose between \'a3c\' and \'random\'.')
# parser.add_argument('--environment', default='media', type=str,
#                     help='Choose between \'a2c\' and \'random\'.')
parser.add_argument(
	'-t', '--train', dest='train', action='store_true', help='Train the model.'
)
parser.add_argument(
	'--lr', default=0.001, help='Learning rate for the shared optimizer.'
)
parser.add_argument(
	'-u', '--update-freq', default=20, type=int,help='How often to update the global model.'
)
parser.add_argument(
	'-n',
	'--num-workers',
	default=multiprocessing.cpu_count(),
	type=int,
	help='Number of parallel workers to train the model.'
)
parser.add_argument(
	'-m',
	'--max-eps',
	default=500,
	type=int,
	help='Global maximum number of episodes to run.'
)
parser.add_argument(
	'-g', '--gamma', default=0.99, help='Discount factor of rewards.'
)
args = parser.parse_args()


def train(env, global_model):
	res_queue = Queue()

	opt = tf.compat.v1.train.AdamOptimizer(args.lr, use_locking=True)

	if os.path.isdir(config.training['save_path']):
		os.system('rm ' + config.training['save_path'] + 'events.*')

	writer = tf.summary.create_file_writer(config.training['save_path'])

	workers = [
		Worker(env, global_model, opt, res_queue, i, writer)
		for i in range(args.num_workers)
	]

	for i, worker in enumerate(workers):
		print('Starting worker {}'.format(i))
		worker.start()

	average_rewards = []  # record episode reward to plot
	while True:
		reward = res_queue.get()
		# print(reward)
		if reward is not None:
			average_rewards.append(reward)
		else:
			break
	[w.join() for w in workers]

	# Plot Reward Average over steps
	plt.plot(average_rewards)
	plt.ylabel('Episode Reward')
	plt.xlabel('Step')
	plt.savefig(os.path.join(config.training['save_path'], 'Reward Average.png'))

	# plt.show()
	plt.close()


def play(global_model):
	workers = [WorkerPlay(global_model, i) for i in range(args.num_workers)]

	for i, worker in enumerate(workers):
		print('Starting worker {}'.format(i))
		worker.start()

	time.sleep(1)
	[w.join() for w in workers]


class Memory:
	def __init__(self):
		self.states = []
		self.actions = []
		self.rewards = []

	def store(self, state, action, reward):
		self.states.append(state)
		self.actions.append(action)
		self.rewards.append(reward)

	def clear(self):
		self.states = []
		self.actions = []
		self.rewards = []


class Worker(threading.Thread):
	# Set up global variables across different threads
	global_episode = 0
	# Moving average reward
	global_average_reward = 0
	best_score = 0
	save_lock = threading.Lock()

	def __init__(self, env, global_model, opt, result_queue, idx, writer):
		super(Worker, self).__init__()
		self.state_size = env.observation_space.shape[0]
		self.action_size = env.action_space.n
		self.result_queue = result_queue
		self.global_model = global_model
		self.opt = opt
		self.local_model = a3c.ActorCriticModel(self.state_size, self.action_size)
		self.worker_idx = idx
		if config.training['env_name'] == 'A3C.envs.eve:Eve-v0':
			self.env = gym.make(config.training['env_name']).unwrapped
		else:
			self.env = gym.make(config.training['env_name']).unwrapped
		self.writer = writer
		self.ep_loss = 0.0

	def run(self):
		total_step = 1
		mem = Memory()

		while Worker.global_episode < args.max_eps:
			current_state = self.env.reset()
			mem.clear()
			ep_reward = 0.
			ep_steps = 0
			self.ep_loss = 0

			time_count = 0
			done = False
			while not done:
				# print('Current State', current_state[None, :])
				logits, _ = self.local_model(
					tf.convert_to_tensor(current_state[None, :], dtype=tf.float32)
				)
				probs = tf.nn.softmax(logits)

				# print('Logits', logits)
				# print('Probs', probs)
				action = np.random.choice(self.action_size, p=probs.numpy()[0])
				# print('Selected action', action)
				new_state, reward, done, info = self.env.step(action)
				# print(new_state[None, :])
				# print('Reward', reward)
				# print(done)
				# print(info)
				ep_reward += reward
				mem.store(current_state, action, reward)

				if time_count == args.update_freq or done:
					# Calculate gradient wrt to local model. We do so by tracking the
					# variables involved in computing the loss by using tf.GradientTape
					with tf.GradientTape() as tape:
						total_loss, total_entropy = self.compute_loss(done, new_state, mem, args.gamma)

					self.ep_loss += total_loss
					# Calculate local gradients
					grads = tape.gradient(total_loss, self.local_model.trainable_weights)
					# Push local gradients to global model
					self.opt.apply_gradients(zip(grads, self.global_model.trainable_weights))
					# Update local model with new weights
					self.local_model.set_weights(self.global_model.get_weights())

					mem.clear()
					time_count = 0

					if done:  # done and print information
						Worker.global_average_reward = a3c.record(
							Worker.global_episode,
							ep_reward,
							self.worker_idx,
							Worker.global_average_reward,
							self.result_queue,
							self.ep_loss,
							ep_steps,
						)

						with self.writer.as_default():
							tf.summary.scalar('Total_Reward', ep_reward, step=Worker.global_episode)

						self.writer.flush()

						# We must use a lock to save our model and to print to prevent data races.
						if ep_reward > Worker.best_score:
							with Worker.save_lock:
								print(
									'Saving best model to {}, '
									'episode score: {}'.format(config.training['save_path'], ep_reward)
								)
								self.global_model.save_weights(
									os.path.join(config.training['save_path'], 'A3C_model.h5')
								)
								# TODO: Print best score at the end of the training
								Worker.best_score = ep_reward
						else:
							with Worker.save_lock:
								print(
									'Saving actual model to {}, '
									'episode score: {}'.format(config.training['save_path'], ep_reward)
								)
								self.global_model.save_weights(
									os.path.join(config.training['save_path'], 'A3C_model_partial.h5')
								)
						Worker.global_episode += 1
				ep_steps += 1

				time_count += 1
				current_state = new_state
				total_step += 1
		self.result_queue.put(None)

	def compute_loss(self, done, new_state, memory, gamma=args.gamma):
		if done:
			reward_sum = 0.  # terminal
		else:
			reward_sum = self.local_model(
				tf.convert_to_tensor(new_state[None, :], dtype=tf.float32)
			)[-1].numpy()[0]

		# Get discounted rewards
		discounted_rewards = []
		for reward in memory.rewards[::-1]:  # reverse buffer r
			reward_sum = reward + gamma * reward_sum
			discounted_rewards.append(reward_sum)
		discounted_rewards.reverse()

		logits, values = self.local_model(
			tf.convert_to_tensor(np.vstack(memory.states), dtype=tf.float32)
		)

		# Get our advantages
		advantage = (
				tf.convert_to_tensor(np.array(discounted_rewards)[:, None], dtype=tf.float32)
				- values
		)

		# Value loss
		value_loss = advantage ** 2

		# Calculate our policy loss
		policy = tf.nn.softmax(logits)
		entropy = tf.nn.softmax_cross_entropy_with_logits(labels=policy, logits=logits)

		policy_loss = tf.nn.sparse_softmax_cross_entropy_with_logits(
			labels=memory.actions, logits=logits
		)

		policy_loss *= tf.stop_gradient(advantage)
		policy_loss -= 0.01 * entropy
		total_loss = tf.reduce_mean((0.5 * value_loss + policy_loss))
		return total_loss, entropy


class WorkerPlay(threading.Thread):
	def __init__(self, global_model, idx):
		super(WorkerPlay, self).__init__()
		self.idx = idx
		if config.training['env_name'] == 'A3C.envs.media:Eve-v0':
			self.env = gym.make(config.training['env_name'], self.idx).unwrapped
		else:
			self.env = gym.make(config.training['env_name']).unwrapped
		self.global_model = global_model
		self.step_counter = 0
		self.action = None

	def run(self):
		state = self.env.reset()
		done = False
		reward_sum = 0

		try:
			model_path = os.path.join(config.training['save_path'], 'A3C_model.h5')
			# print('Loading model from: {}'.format(model_path))
			self.global_model.load_weights(model_path)

			while True:

				while not done:
					if args.num_workers == 1 and config.training['env_name'] == 'CartPole-v0':
						self.env.render()
					policy, value = self.global_model(tf.convert_to_tensor(state[None, :], dtype=tf.float32))
					policy = tf.nn.softmax(policy)
					self.action = np.argmax(policy)
					# print('Selected action', action)
					state, reward, done, _ = self.env.step(self.action)
					reward_sum += reward
					# print('{}. Reward: {}, action: {}'.format(step_counter, reward_sum, action))
					print(
						"{}. Reward: {}, action: {}, ID: {}, step: {}".format(
							self.step_counter, reward_sum, self.action, self.idx, self.step_counter
						)
					)
					self.step_counter += 1

				if done and config.training['env_name'] == 'CartPole-v0':
					print('Worker {} finished the job, with {} iterations'.format(self.idx, self.step_counter))
					# Uncomment to infinite play mode
					# state = self.env.reset()
					# done = False
					# self.step_counter = 0
					# reward_sum = 0
					# input('Press Enter to continue playing...')
					break

				if done and config.training['env_name'] == 'A3C.envs.eve:Eve-v0' or 'A3C.envs.energy:Energy-v0':
					state = self.env.reset()
					done = False
					self.step_counter = 0
					reward_sum = 0

		except KeyboardInterrupt:
			print('Received Keyboard Interrupt. Shutting down.')
		except OSError:
			print('Unable to load model. Check correct directories. Shutting down.')
		finally:
			self.env.close()


def main():
	if not os.path.exists(config.training['save_path']):
		os.makedirs(config.training['save_path'])

	# Starting environment only for information running purposes
	if config.training['env_name'] == 'A3C.envs.eve:Eve-v0':
		assert args.num_workers == len(config.transcoder['address']), 'One parallel worker per transcoder'
		env = gym.make(config.training['env_name'])
	else:
		env = gym.make(config.training['env_name'])
	state_size = env.observation_space.shape[0]
	action_size = env.action_space.n
	# env.close()

	# Initial information about training
	print('-------------------------------------')
	print('TRAINING INFORMATION')
	print('Environment name: {}'.format(config.training['env_name']))
	print('Number of states: {}. Number of actions: {}'.format(state_size, action_size))
	print('Training episodes: {}'.format(args.max_eps))
	print('-------------------------------------')

	# if config.api['enable']  == True:
	#     api_server = threading.Thread(target=start_api_server, daemon=True)  # daemon=False, to loop the API server
	#     print('API SERVER INFORMATION')
	#     api_server.start()
	#     time.sleep(1)
	#     print('-------------------------------------')

	global_model = a3c.ActorCriticModel(state_size, action_size)  # Global Network
	global_model(tf.convert_to_tensor(np.random.random((1, state_size)), dtype=tf.float32))

	if args.train:
		time.sleep(1)
		train(env, global_model)
		# time.sleep(2)
		print('------------TRAINING DONE------------')
	else:
		time.sleep(1)
		play(global_model)
		# time.sleep(2)
		print('------------PLAY MODE DONE-----------')


if __name__ == '__main__':
	print(args)
	main()
