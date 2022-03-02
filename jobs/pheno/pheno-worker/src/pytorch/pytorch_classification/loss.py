import torch
from torch import nn
import numpy as np
import torch.nn.functional as F



class LossRegression:
    def __init__(self, reg_weight=0, out_min=-2, out_max=2):
        self.nll_loss = nn.MSELoss()
        self.reg_weight = reg_weight
        self.out_min = out_min
        self.out_max = out_max

    def __call__(self, outputs, targets):

        loss = self.nll_loss(outputs, targets) +  self.reg_weight*(F.relu(outputs - self.out_max) + F.relu(self.out_min - outputs)).mean()
        return loss
