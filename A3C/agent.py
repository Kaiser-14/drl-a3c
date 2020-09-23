from A3C import config
from A3C import a3c

import os
import threading
import gym
import multiprocessing
import numpy as np
from queue import Queue
import argparse
import matplotlib.pyplot as plt
import time

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # or any {'0', '1', '2'}
import tensorflow as tf

os.environ["CUDA_VISIBLE_DEVICES"] = ""

parser = argparse.ArgumentParser(description='Run A3C algorithm on the game '
                                             'Cartpole.')
parser.add_argument('--algorithm', default='a3c', type=str,
                    help='Choose between \'a3c\' and \'random\'.')
# parser.add_argument('--environment', default='media', type=str,
#                     help='Choose between \'a2c\' and \'random\'.')
parser.add_argument('--train', dest='train', action='store_true',
                    help='Train our model.')
parser.add_argument('--lr', default=0.001,
                    help='Learning rate for the shared optimizer.')
parser.add_argument('--update-freq', default=10, type=int,
                    help='How often to update the global model.')
parser.add_argument('--num-workers', default=multiprocessing.cpu_count(), type=int,
                    help='Number of parallel workers to train the model.')
# parser.add_argument('--max-eps', default=1000, type=int,
#                     help='Global maximum number of episodes to run.')
parser.add_argument('--gamma', default=0.99,
                    help='Discount factor of rewards.')
# parser.add_argument('--save-dir', default='./', type=str,
#                     help='Directory in which you desire to save the model.')
args = parser.parse_args()


def train(env, global_model):
    res_queue = Queue()

    opt = tf.compat.v1.train.AdamOptimizer(args.lr, use_locking=True)
    os.system('rm ' + config.save['path'] +'events.*')
    writer = tf.summary.create_file_writer(config.save['path'])

    workers = [Worker(env,
                      global_model,
                      opt, res_queue,
                      i, writer) for i in range(args.num_workers)]

    for i, worker in enumerate(workers):
        print("Starting worker {}".format(i))
        worker.start()

    average_rewards = []  # record episode reward to plot
    while True:
        reward = res_queue.get()
        if reward is not None:
            average_rewards.append(reward)
        else:
            break
    [w.join() for w in workers]

    plt.plot(average_rewards)
    plt.ylabel('Episode Reward')
    plt.xlabel('Step')
    plt.savefig(os.path.join(config.save['path'],
                             'Reward Average.png'))
    plt.show()


def play(env, global_model):
    # env = gym.make(self.game_name).unwrapped
    env = env.unwrapped
    state = env.reset()
    model = global_model

    done = False
    step_counter = 0
    reward_sum = 0

    try:
        model_path = os.path.join(config.save['path'], 'A3C_model.h5')
        print('Trying to load model from: {}'.format(model_path))
        model.load_weights(model_path)

        while not done:
            env.render()
            policy, value = model(tf.convert_to_tensor(state[None, :], dtype=tf.float32))
            policy = tf.nn.softmax(policy)
            action = np.argmax(policy)
            # print('Selected action', action)
            state, reward, done, _ = env.step(action)
            reward_sum += reward
            print("{}. Reward: {}, action: {}".format(step_counter, reward_sum, action))
            step_counter += 1

            # Prepare Play mode to Media environment (infinite play)
            # if done:
            #     state = env.reset()
            #     done = False
            #     step_counter = 0
            #     reward_sum = 0

    except KeyboardInterrupt:
        print("Received Keyboard Interrupt. Shutting down.")
    # except:
    #     print("Unable to load model. Check correct directories. Shutting down.")
    except OSError:
        print("Unable to load model. Check correct directories. Shutting down.")
    finally:
        env.close()


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

    def __init__(self,
                 env,
                 # state_size,
                 # action_size,
                 global_model,
                 opt,
                 result_queue,
                 idx, writer):
        super(Worker, self).__init__()
        self.state_size = env.observation_space.shape[0]
        self.action_size = env.action_space.n
        self.result_queue = result_queue
        self.global_model = global_model
        self.opt = opt
        self.local_model = a3c.ActorCriticModel(self.state_size, self.action_size)
        self.worker_idx = idx
        self.env = gym.make(
            config.training['env_name']).unwrapped  # TODO: Check unwrapped in own environments
        self.ep_loss = 0.0
        self.ep_entropy = 0.0
        self.writer = writer

    def run(self):
        total_step = 1
        mem = Memory()

        while Worker.global_episode < config.training['max_eps']:
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
                    tf.convert_to_tensor(current_state[None, :],
                                         dtype=tf.float32))
                probs = tf.nn.softmax(logits)

                # entropy = self.compute_entropy(probs)  # TODO: Use entropy
                entropy = 0

                print('Logits', logits)
                print('Probs', probs)
                action = np.random.choice(self.action_size, p=probs.numpy()[0])
                # print('Selected action', action)
                new_state, reward, done, info = self.env.step(action)
                # print('Reward', reward)
                # if done:
                #     reward = -1
                ep_reward += reward
                mem.store(current_state, action, reward)

                if time_count == args.update_freq or done or info:
                    # Calculate gradient wrt to local model. We do so by tracking the
                    # variables involved in computing the loss by using tf.GradientTape
                    with tf.GradientTape() as tape:
                        total_loss, total_entropy = self.compute_loss(done,
                                                                      new_state,
                                                                      mem,
                                                                      args.gamma)
                    self.ep_loss += total_loss
                    # FIXME: Check behaviour based on 5g media training
                    self.ep_entropy += self.compute_entropy(total_entropy)

                    # Calculate local gradients
                    grads = tape.gradient(total_loss, self.local_model.trainable_weights)
                    # Push local gradients to global model
                    self.opt.apply_gradients(zip(grads,
                                                 self.global_model.trainable_weights))
                    # Update local model with new weights
                    self.local_model.set_weights(self.global_model.get_weights())

                    mem.clear()
                    time_count = 0

                    if done or info:  # done and print information
                        Worker.global_average_reward = \
                            a3c.record(Worker.global_episode, ep_reward, self.worker_idx,
                                         Worker.global_average_reward, self.result_queue,
                                         self.ep_loss, ep_steps)

                        with self.writer.as_default():
                            tf.summary.scalar("Total_Reward", ep_reward, step=Worker.global_episode)
                            tf.summary.scalar("TD_Loss", self.ep_loss, step=Worker.global_episode)
                            tf.summary.scalar("Entropy", self.ep_entropy, step=Worker.global_episode)

                        self.writer.flush()

                        # We must use a lock to save our model and to print to prevent data races.
                        if ep_reward > Worker.best_score:
                            with Worker.save_lock:
                                print("Saving best model to {}, "
                                      "episode score: {}".format(config.save['path'], ep_reward))
                                self.global_model.save_weights(
                                    os.path.join(config.save['path'],
                                                 'A3C_model.h5')
                                )
                                Worker.best_score = ep_reward
                        Worker.global_episode += 1
                ep_steps += 1

                time_count += 1
                current_state = new_state
                total_step += 1
        self.result_queue.put(None)

    def compute_loss(self,
                     done,
                     new_state,
                     memory,
                     gamma=0.99):
        if done:
            reward_sum = 0.  # terminal
        else:
            reward_sum = self.local_model(
                tf.convert_to_tensor(new_state[None, :],
                                     dtype=tf.float32))[-1].numpy()[0]

        # Get discounted rewards
        discounted_rewards = []
        for reward in memory.rewards[::-1]:  # reverse buffer r
            reward_sum = reward + gamma * reward_sum
            discounted_rewards.append(reward_sum)
        discounted_rewards.reverse()

        logits, values = self.local_model(
            tf.convert_to_tensor(np.vstack(memory.states),
                                 dtype=tf.float32))
        # Get our advantages
        advantage = tf.convert_to_tensor(np.array(discounted_rewards)[:, None],
                                         dtype=tf.float32) - values
        # Value loss
        value_loss = advantage ** 2

        # Calculate our policy loss
        policy = tf.nn.softmax(logits)
        entropy = tf.nn.softmax_cross_entropy_with_logits(labels=policy, logits=logits)

        policy_loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=memory.actions,
                                                                     logits=logits)
        policy_loss *= tf.stop_gradient(advantage)
        policy_loss -= 0.01 * entropy
        total_loss = tf.reduce_mean((0.5 * value_loss + policy_loss))
        return total_loss, entropy

    def compute_entropy(self, probs):  # FIXME: Adjust these values
        entropy = 0.0
        for i in range(len(probs)):
            if 0 < probs[i] < 1:
                entropy -= probs[i] * np.log(probs[i])
        return entropy


def main():
    if not os.path.exists(config.save['path']):
        os.makedirs(config.save['path'])

    env = gym.make(config.training['env_name'])
    state_size = env.observation_space.shape[0]
    action_size = env.action_space.n

    # Initial information about training
    print('-------------------------------------')
    print('TRAINING INFORMATION')
    print('Environment name: {}'.format(config.training['env_name']))
    print('Number of states: {}. Number of actions: {}'.format(state_size, action_size))
    print('Training episodes: {}'.format(config.training['max_eps']))
    print('-------------------------------------')

    global_model = a3c.ActorCriticModel(state_size, action_size)  # Global Network
    global_model(tf.convert_to_tensor(np.random.random((1, state_size)), dtype=tf.float32))

    if args.train:
        time.sleep(1)
        train(env, global_model)
        print("------------TRAINING DONE------------")
    else:
        play(env, global_model)
        print("------------PLAY MODE DONE-----------")


if __name__ == '__main__':
    print(args)
    main()
