import torch
import torch.nn as nn
import torch.optim as optim
import gym
from dqn import ReplayBuffer
from torch.distributions import Categorical
from torch.nn.functional import mse_loss
from plot_functions import plot_timesteps_and_rewards


# TODO : 
#  1. Experience replay 
#  2. Fixing target
#  3. Learning rate decay with a scheduler


class FunctionApproximation(nn.Module):
    def __init__(self, input_size, output_size, hidden_size=12):
        super(FunctionApproximation, self).__init__()
        self.layer1 = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU()
        )
        self.layer2 = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU()
        )
        self.output_layer = nn.Sequential(
            nn.Linear(hidden_size, output_size),
            # TODO : Try out log here if any numerical instability occurs
            nn.Softmax(dim=-1)
        )

    def forward(self, x):
        out = self.layer1(x)
        out = self.layer2(out)
        out = self.output_layer(out)
        return out

    def select_action(self, current_state):
        """
        selects an action as per some decided exploration
        :param current_state: the current state
        :return: the chosen action and the log probility of that chosen action
        """
        probs = self(current_state)
        # TODO : This can be made as gaussian exploration and then exploring action can be sampled from there
        m = Categorical(probs)
        action = m.sample()
        return action, m.log_prob(action)


class Q_Approximation(nn.Module):
    def __init__(self, input_size, output_size, hidden_size=12):
        super(Q_Approximation, self).__init__()
        self.layer1 = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU()
        )
        self.layer2 = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU()
        )
        self.output_layer = nn.Sequential(
            nn.Linear(hidden_size, output_size),
            # TODO : Try out log here if any numerical instability occurs
            nn.Softmax(dim=-1)
        )

    def forward(self, x):
        out = self.layer1(x)
        out = self.layer2(out)
        out = self.output_layer(out)
        return out


learning_rate = 0.01
env = gym.make('CartPole-v1')
actor = FunctionApproximation(input_size=env.observation_space.shape[0], output_size=env.action_space.n)
critic = Q_Approximation(input_size=env.observation_space.shape[0], output_size=env.action_space.n)
actor_optimizer = optim.Adam(actor.parameters(), lr=learning_rate)
critic_optimizer = optim.Adam(critic.parameters(), lr=learning_rate)

gamma = 0.95
epsilon = 0.05
avg_history = {'episodes': [], 'timesteps': [], 'reward': []}
agg_interval = 1
avg_reward = 0.0
avg_timestep = 0
running_loss1_mean = 0
running_loss2_mean = 0
loss1_history = []
loss2_history = []
# initialize policy and replay buffer
replay_buffer = ReplayBuffer()
start_episode = 0

# Play with a random policy and see
# run_current_policy(env.env, policy)

train_episodes = 200

# In[]:

# Train the network to predict actions for each of the states
for episode_i in range(start_episode, start_episode + train_episodes):
    episode_timestep = 0
    episode_reward = 0.0

    done = False

    cur_state = torch.Tensor(env.reset())

    while not done:
        # TODO : Use gaussian exploration for this
        action, log_prob = actor.select_action(cur_state)

        # take action in the environment
        next_state, reward, done, info = env.step(action.item())

        # Update parameters of critic by TD(0)
        # TODO : Use TD Lambda here and compare the performance
        q_values = critic(cur_state)
        target = reward + gamma * q_values
        critic_optimizer.zero_grad()
        loss1 = mse_loss(input=q_values, target=target)
        loss1.backward(retain_graph=True)
        running_loss1_mean += loss1.item()
        critic_optimizer.step()

        # Update parameters of actor by policy gradient
        actor_optimizer.zero_grad()
        # compute the gradient from the sampled log probability
        # TODO : Verify the computation here
        #  the log probability times the Q of the action that you just took in that state
        loss2 = -log_prob * q_values[action]
        loss2.backward()
        print('Actor Loss : ', loss2.item())
        running_loss2_mean += loss2.item()
        actor_optimizer.step()

        # add the transition to replay buffer
        # replay_buffer.add(cur_state, action, next_state, reward, done)

        # sample minibatch of transitions from the replay buffer
        # the sampling is done every timestep and not every episode
        # sample_transitions = replay_buffer.sample()

        # # update the policy using the sampled transitions
        # policy.update_policy(**sample_transitions)

        episode_reward += reward
        episode_timestep += 1

        cur_state = torch.Tensor(next_state)

    loss1_history.append(running_loss1_mean/episode_timestep)
    loss2_history.append(running_loss2_mean/episode_timestep)
    running_loss1_mean = 0
    running_loss2_mean = 0

    avg_reward += episode_reward
    avg_timestep += episode_timestep

    if (episode_i + 1) % agg_interval == 0:
        avg_history['episodes'].append(episode_i + 1)
        avg_history['timesteps'].append(avg_timestep / float(agg_interval))
        avg_history['reward'].append(avg_reward / float(agg_interval))
        avg_timestep = 0
        avg_reward = 0.0

# In[]:

import matplotlib.pyplot as plt
plt.figure(0)
plt.plot(loss1_history)
plt.figure(1)
plt.plot(loss2_history)

plot_timesteps_and_rewards(avg_history)


cur_state = env.reset()
total_step = 0
total_reward = 0.0
done = False
while not done:
    action, probs = actor.select_action(torch.Tensor(cur_state))
    next_state, reward, done, info = env.step(action.item())
    total_reward += reward
    env.render(mode='rgb_array')
    total_step += 1
    cur_state = next_state
print("Total timesteps = {}, total reward = {}".format(total_step, total_reward))
