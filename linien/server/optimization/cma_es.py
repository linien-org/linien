# License: MIT
# the following code was translated from pseudocode on
# https://www.wikiwand.com/en/CMA-ES to python by Julien Kluge.
import numpy as np
from math import floor, log, sqrt, exp
from random import uniform

from .general import Optimizer, Individual


class CMAES(Optimizer):
    """Covariance matrix adapting evolutionary strategy"""

    def __init__(self):
        super().__init__()
        #start parameters
        self.x0 = []
        self.sigma = 0.3
        self.lamb = 0 # λ
        self.mu = 0 # μ

        #procedure parameters
        self.n = 0
        self.xmean = []
        self.xold = []
        self.weights = []
        self.mueff = 0 # μ_{effective}
        self.cc = 0
        self.cs = 0
        self.c1 = 0
        self.cmu = 0
        self.damps = 0
        self.pc = []
        self.ps = []
        self.B = [[]]
        self.D = []
        self.C = [[]]
        self.invsqrtC = [[]]
        self.eigeneval = 0
        self.chiN = 0
        self.counteval = 0
        self.ar = []
        self.currentX = None

        #state machine
        self.initialized = False
        self.stateIndex = 0


    #request method
    def request_parameter_set(self):
        if not self.initialized:
            self.initialized = True
            self.initializeAlgorithm()

        self.counteval += 1 #increase evaluation counter
        # FIXME: uniform? Or use the fix of automatix code?
        xd = np.matmul(self.B, [dd * uniform(-1, 1) for dd in self.D])
        xc = [xm + self.sigma * xgd for xm, xgd in zip(self.xmean, xd)]
        xc = self._truncate_parameters(xc)
        self.currentX = xc.copy()
        return xc


    #answer method
    def insert_fitness_value(self, f, set):
        self.ar[self.stateIndex].x = self.currentX
        self.ar[self.stateIndex].fitness = f

        self.stateIndex += 1
        if self.stateIndex == self.lamb:
            self.advanceGeneration()


    def advanceGeneration(self):
        self.stateIndex = 0
        self._generation += 1

        self.ar.sort()
        xnew = [self.ar[i].x for i in range(0, self.mu)]

        self.xold = self.xmean.copy()
        self.xmean = np.matmul(np.transpose(xnew), self.weights) #MAGIC
        self.xmean = self._truncate_parameters(self.xmean)

        #ps = (1 - cs) * ps+Sqrt[cs*(2-cs)*mueff]*invsqrtC.(xmean-xold)/sigma;
        xd = [(x1 - x2) / self.sigma for x1, x2 in zip(self.xmean, self.xold)]
        psdx = np.dot(sqrt(self.cs * (2 - self.cs) * self.mueff), np.matmul(self.invsqrtC, xd))
        self.ps = [(1 - self.cs) * tps + ps2 for tps, ps2 in zip(self.ps, psdx)]

        #hsig=Boole[Norm[ps]/Sqrt[1-(1-cs)^(2*counteval/lambda)]/chiN<1.4+2/(n+1)];
        hsigVal = np.linalg.norm(self.ps) / sqrt(1 - (1 - self.cs)**(2 * self.counteval / self.lamb))
        if hsigVal < 1.4 + 2 / (self.n + 1):
            self.hsig = 1
        else:
            self.hsig = 0

        #pc=(1-cc)*pc+hsig*Sqrt[cc*(2-cc)*mueff]*(xmean-xold)/sigma;
        self.pc = [(1 - self.cc) * pc1 + self.hsig * sqrt(self.cc * (2 - self.cc) * self.mueff) * xd1 for pc1, xd1 in zip(self.pc, xd)]

        #artmp=(1/sigma)*(Transpose[xnew[[1;;mu,All]]]-Transpose[ConstantArray[xold,mu]]);
        artmp = np.dot(1 / self.sigma, np.transpose(xnew) - np.transpose([self.xold for _ in range(0, self.mu)]))

        #CC=(1-c1-cmu)*CC
        # +c1*(Transpose[{pc}].{pc}+(1-hsig)*cc*(2-cc)*CC)
        # +cmu*(artmp.DiagonalMatrix[weights].Transpose[artmp]);
        C1 = np.dot(1 - self.c1 - self.cmu, self.C)
        C21 = np.dot(self.c1, np.outer(self.pc, self.pc))
        C22 = np.dot(self.c1 * (1 - self.hsig) * self.cc * (2 - self.cc), self.C)
        C3 = np.dot(self.cmu, np.matmul(np.matmul(artmp, np.diag(self.weights)), np.transpose(artmp)))
        self.C = C1 + C21 + C22 + C3

        #sigma = sigma*Exp[(cs/damps)*(Norm[ps]/chiN - 1)];
        self.sigma = self.sigma * exp((self.cs / self.damps) * (np.linalg.norm(self.ps) / self.chiN - 1))

        if self.counteval - self.eigeneval > self.lamb / (self.c1 + self.cmu) / self.n / 10:
            self.eigeneval = self.counteval
            self.C = np.triu(self.C) + np.transpose(np.triu(self.C, 1))
            w, v = np.linalg.eigh(self.C)

            self.B = [np.dot(1 / np.linalg.norm(vx), vx) for vx in v]
            self.D = [sqrt(wx) for wx in w]
            dInv = [1 / sqrt(wx) for wx in w]
            self.invsqrtC = np.matmul(np.matmul(self.B, np.diag(dInv)), np.transpose(self.B))


    def request_results(self):
        return [self.xmean]

    def initializeAlgorithm(self):
        self.xmean = self.x0.copy()
        self.xmean = self._truncate_parameters(self.xmean)
        self.n = len(self.xmean)
        if self.n < 2:
            raise ValueError('Dimension of initial point needs to be bigger than 1')
        self.xold = [0 for _ in range(0, self.n)]

        if self.lamb == 0: #if lambda is still default
            self.lamb = 2 + floor(3 * log(self.n))
        if self.lamb < 2:
            raise ValueError('Lambda ´lamb´ needs to be greater than 1')
        if self.mu == 0: #if mu is still default
            self.mu = self.lamb / 2
        self.weights = [log(self.mu + 0.5) - log(x) for x in range(1, floor(self.mu + 1))]
        self.mu = floor(self.mu)
        if self.mu < 1:
            raise ValueError('Mu ´mu´ needs to be greater than 0')
        weightsSum = sum(self.weights)
        self.weights = [x / weightsSum for x in self.weights] #norm to 1-sum
        self.mueff = sum(self.weights)**2 / sum([x * x for x in self.weights])

        self.cc = (4 + self.mueff / self.n) / (self.n + 4 + 2 * self.mueff / self.n)
        self.cs = (self.mueff + 2) / (self.n + self.mueff + 5)
        self.c1 = 2 / ((self.n + 1.3)**2 + self.mueff)
        self.cmu = min(1 - self.c1, 2 * (self.mueff - 2 + 1 / self.mueff) / ((self.n + 2)**2 + self.mueff))
        self.damps = 1 + 2**max(0, sqrt((self.mueff - 1) / (self.n + 1)) - 1) + self.cs

        self.pc = [0 for _ in range(0, self.n)]
        self.ps = [0 for _ in range(0, self.n)]
        self.B = np.identity(self.n)
        self.D = [1 for _ in range(0, self.n)]
        self.C = np.identity(self.n)
        self.invsqrtC = np.identity(self.n)
        self.eigeneval = 0
        self.chiN = sqrt(self.n) * (1 - 1 / (4 * self.n) + 1 / (21 * self.n**2))
        self.counteval = 0

        self.ar = [Individual([0 for __ in range(0, self.n)], 0) for _ in range(0, self.lamb)]
