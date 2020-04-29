import models_goal

import numpy as np
import gym
from collections import deque
import random
import torch
import torch.autograd
from torch.autograd import Variable
from models_goal import *
from utils import *
import torch.optim as optim

class DDPGagentwithHER:
    def __init__(self, env, hidden_sizes, actor_learning_rate=1e-4, critic_learning_rate=1e-3, gamma=0.99, tau=1e-2,
                 max_memory_size=50000):
        # Params
        self.num_states = env.observation_space['observation'].shape[0]
        self.num_actions = env.action_space.shape[0]
        self.num_goals = env.observation_space['desired_goal'].shape[0]
        self.gamma = gamma
        self.tau = tau
        self.action_l2=0.001

        # Networks
        self.actor = Actor(self.num_states, self.num_actions, self.num_goals, hidden_sizes)
        self.actor_target = Actor(self.num_states, self.num_actions, self.num_goals, hidden_sizes)
        self.critic = Critic(self.num_states, self.num_actions, self.num_goals, hidden_sizes, self.num_actions)
        self.critic_target = Critic(self.num_states, self.num_actions, self.num_goals, hidden_sizes, self.num_actions)

        for target_param, param in zip(self.actor_target.parameters(), self.actor.parameters()):
            target_param.data.copy_(param.data)

        for target_param, param in zip(self.critic_target.parameters(), self.critic.parameters()):
            target_param.data.copy_(param.data)

        # Training
        self.memory = Memorywithgoal(max_memory_size)
        self.critic_criterion = nn.MSELoss()
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=actor_learning_rate)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=critic_learning_rate)

    def get_action(self, state, goal):
        state = Variable(torch.from_numpy(state).float().unsqueeze(0))
        goal = Variable(torch.from_numpy(goal).float().unsqueeze(0))
        action = self.actor.forward(state, goal)
        action = action.detach().numpy()[0, 0]
        return action

    def update(self, batch_size):
        states, actions, rewards, next_states, _, goal = self.memory.sample(batch_size)
        states = torch.FloatTensor(states)
        actions = torch.FloatTensor(actions)
        rewards = torch.FloatTensor(rewards)
        next_states = torch.FloatTensor(next_states)
        goals = torch.FloatTensor(goal)

        # Critic loss
        Qvals = self.critic.forward(states, actions, goals)
        next_actions = self.actor_target.forward(next_states, goals)
        next_Q = self.critic_target.forward(next_states, next_actions.detach(), goals)
        Qprime = rewards + self.gamma * next_Q
        critic_loss = self.critic_criterion(Qvals, Qprime)

        # Actor loss
        policy_loss = -self.critic.forward(states, self.actor.forward(states, goals), goals).mean()

        # update networks
        self.actor_optimizer.zero_grad()
        policy_loss.backward()
        self.actor_optimizer.step()

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        # update target networks
        for target_param, param in zip(self.actor_target.parameters(), self.actor.parameters()):
            target_param.data.copy_(param.data * self.tau + target_param.data * (1.0 - self.tau))

        for target_param, param in zip(self.critic_target.parameters(), self.critic.parameters()):
            target_param.data.copy_(param.data * self.tau + target_param.data * (1.0 - self.tau))
    
    def updateUsingHer(self, batch_size,episode_memory,length):
        states, actions, rewards, next_states, _, goals = self.memory.sample(batch_size)
        if length<50:
            bs=length
        else:
            bs=50
        states_ep, actions_ep, rewards_ep, next_states_ep, _, goal_ep = episode_memory.sample(bs)
        states = torch.FloatTensor(states)
        actions = torch.FloatTensor(actions)
        rewards = torch.FloatTensor(rewards)
        next_states = torch.FloatTensor(next_states)
        goals = torch.FloatTensor(goals)
        states_ep = torch.FloatTensor(states_ep)
        actions_ep = torch.FloatTensor(actions_ep)
        rewards_ep = torch.FloatTensor(rewards_ep)
        next_states_ep = torch.FloatTensor(next_states_ep)
        goals_ep = torch.FloatTensor(goal_ep)
        # Critic loss
        Qvals = self.critic.forward(states, actions, goals)
        next_actions = self.actor_target.forward(next_states, goals)
        next_Q = self.critic_target.forward(next_states, next_actions.detach(), goals)
        Qprime = rewards + self.gamma * next_Q
        critic_loss = self.critic_criterion(Qvals, Qprime)

        # Actor loss
        policy_loss = -self.critic.forward(states, self.actor.forward(states, goals), goals).mean()
        policy_loss += self.action_l2*(self.actor.forward(states, goals)**2).mean()
        # update networks
        self.actor_optimizer.zero_grad()
        policy_loss.backward()
        self.actor_optimizer.step()

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        Qvals = self.critic.forward(states_ep, actions_ep, goals_ep)
        next_actions = self.actor_target.forward(next_states_ep, goals_ep)
        next_Q = self.critic_target.forward(next_states_ep, next_actions.detach(), goals_ep)
        Qprime = rewards_ep + self.gamma * next_Q
        critic_loss = self.critic_criterion(Qvals, Qprime)

        # Actor loss
        policy_loss = -self.critic.forward(states_ep, self.actor.forward(states_ep, goals_ep), goals_ep).mean()
        policy_loss += self.action_l2 * (self.actor.forward(states_ep, goals_ep) ** 2).mean()
        # update networks
        self.actor_optimizer.zero_grad()
        policy_loss.backward()
        self.actor_optimizer.step()

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        # update target networks
        for target_param, param in zip(self.actor_target.parameters(), self.actor.parameters()):
            target_param.data.copy_(param.data * self.tau + target_param.data * (1.0 - self.tau))

        for target_param, param in zip(self.critic_target.parameters(), self.critic.parameters()):
            target_param.data.copy_(param.data * self.tau + target_param.data * (1.0 - self.tau))
                
