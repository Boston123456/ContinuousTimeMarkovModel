import unittest
from scipy.stats import logistic
import numpy as np
from theano.tensor import as_tensor_variable
from pymc3 import Model, sample, Metropolis, Dirichlet, Potential, Binomial, Beta, Slice
import theano.tensor as TT
from ContinuousTimeMarkovModel.src.distributions import *
from ContinuousTimeMarkovModel.src.forwardS import *
from ContinuousTimeMarkovModel.src.forwardX import *
from theano import function

class logpTests(unittest.TestCase):
    def setUp(self):
        #test Claims
        N = 5 # Number of patients
        M = 3 # Number of hidden states
        self.M = M
        K = 2 # Number of comorbidities
        D = 20 # Number of claims
        Dd = 4 # Maximum number of claims that can occur at once
        min_obs = 2 # Minimum number of observed claims per patient
        max_obs = 4 # Maximum number of observed claims per patient
        #obs_jumps = np.ones((N,max_obs-1))
        obs_jumps = np.array([[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]])
        T = np.array([4,2,3,4,2])
        
        #O(4,4,5)
        O = np.zeros((Dd,max_obs,N))
        #import pdb; pdb.set_trace()
        O[[0,1,3,2,3,3],[0,1,3,2,3,3],[0,1,4,3,3,4]] = 1

        with Model() as self.model:
            self.pi = Dirichlet('pi', a = as_tensor_variable([0.5, 0.5, 0.5]), shape=M)
            pi_min_potential = Potential('pi_min_potential', TT.switch(TT.min(self.pi) < .1, -np.inf, 0))
            self.Q = DiscreteObsMJP_unif_prior('Q', M=M, lower=0.0, upper=1.0, shape=(M,M))
            self.S = DiscreteObsMJP('S', pi=self.pi, Q=self.Q, M=M, N=N, observed_jumps=obs_jumps, T=T, shape=(N,max_obs))
            self.B0 = Beta('B0', alpha = 1., beta = 1., shape=(K,M))
            self.B = Beta('B', alpha = 1., beta = 1., shape=(K,M))
            self.X = Comorbidities('X', S=self.S, B0=self.B0,B=self.B, T=T, shape=(K, max_obs, N))
            self.Z = Beta('Z', alpha = 0.1, beta = 1., shape=(K,D))
            self.L = Beta('L', alpha = 1., beta = 1., shape=D)
            #L = Beta('L', alpha = 0.1, beta = 1, shape=D, transform=None)
            #L = Uniform('L', left = 0.0, right = 1.0, shape=D, transform=None)
            #L = Uniform('L', lower = 0.0, upper = 1.0, shape=D)
            self.testClaims = Claims('O_obs', X=self.X, Z=self.Z, L=self.L, T=T, D=D, max_obs=max_obs, O_input=O, shape=(Dd,max_obs,N), observed=O)

            self.forS = ForwardS(vars=[self.S], N=N, T=T, max_obs=max_obs, observed_jumps=obs_jumps)
            self.forX = ForwardX(vars=[self.X], N=N, T=T, K=K, D=D,Dd=Dd, O=O, max_obs=max_obs)

        #import pdb; pdb.set_trace()
        self.myTestPoint = {'Z_logodds': np.array([[-2.30258509, -2.30258509, -2.30258509, -2.30258509, -2.30258509,
    -2.30258509, -2.30258509, -2.30258509, -2.30258509, -2.30258509,
    -2.30258509, -2.30258509, -2.30258509, -2.30258509, -2.30258509,
    -2.30258509, -2.30258509, -2.30258509, -2.30258509, -2.30258509],
   [-2.30258509, -2.30258509, -2.30258509, -2.30258509, -2.30258509,
    -2.30258509, -2.30258509, -2.30258509, -2.30258509, -2.30258509,
    -2.30258509, -2.30258509, -2.30258509, -2.30258509, -2.30258509,
    -2.30258509, -2.30258509, -2.30258509, -2.30258509, -2.30258509]]), 'Q_ratematrixoneway': np.array([ 0.1,  0.1]), 'pi_stickbreaking': np.array([0.2,0.1]), 'S': np.array([[0, 0, 1, 1],
   [1, 1, 1, 1],
   [1, 1, 2, 2],
   [0, 2, 2, 2],
   [0, 0, 0, 1]], dtype=np.int32), 'B0_logodds': np.array([[ 0.,  1.,  0.],
   [ 0.,  0.,  1.]]), 'X': np.array([[[0, 1, 1, 1, 1],
    [0, 1, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1]],

   [[1, 1, 0, 0, 1],
    [1, 1, 0, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1]]], dtype=np.int8), 'L_logodds': np.array([ 0.1,  0.1,  0.1,  0.1,  0.01,  0.01,  0.01,  0.01,  0.0011,  0.0011,  0.0011,  0.0011,  0.0011,
    0.,  0.0101,  0.0101,  0.0101,  0.01,  0.01,  0.01]), 'B_logodds': np.array([[ 1.,  0.,  1.],
   [ 0.,  1.,  0.]])}
        #import pdb; pdb.set_trace()


    def test_claims_pi_same_as_old(self):
        pi_LL = self.pi.transformed.logp(self.myTestPoint)
        pi_LL_Correct = -3.493851901732915
        np.testing.assert_almost_equal(pi_LL, pi_LL_Correct, decimal = 6, err_msg="logp of pi is incorrect")

    def test_claims_Q_same_as_old(self):
        with self.model:
            Q_LL = self.Q.transformed.logp(self.myTestPoint)
            Q_LL_Correct = -2.7775866402942837
            np.testing.assert_almost_equal(Q_LL, Q_LL_Correct, decimal = 6, err_msg="logp of Q is incorrect")

    def test_claims_S_same_as_old(self):
        with self.model:
            S_LL = self.S.logp(self.myTestPoint)
            S_LL_Correct = -12.165383116823502
            np.testing.assert_almost_equal(S_LL, S_LL_Correct, decimal = 6, err_msg="logp of S is incorrect")

    def test_claims_B0_same_as_old(self):
        with self.model:
            B0_LL = self.B0.transformed.logp(self.myTestPoint)
            B0_LL_Correct = -8.798224194552454
            np.testing.assert_almost_equal(B0_LL, B0_LL_Correct, decimal = 6, err_msg="logp of B0 is incorrect")

    def test_claims_B_same_as_old(self):
        with self.model:
            B_LL = self.B.transformed.logp(self.myTestPoint)
            B_LL_Correct = -9.038453208469008
            np.testing.assert_almost_equal(B_LL, B_LL_Correct, decimal = 6, err_msg="logp of B is incorrect")

    def test_claims_Z_same_as_old(self):
        with self.model:
            Z_LL = self.Z.transformed.logp(self.myTestPoint)
            Z_LL_Correct = -105.50739200312837
            np.testing.assert_almost_equal(Z_LL, Z_LL_Correct, decimal = 6, err_msg="logp of Z is incorrect")

    def test_claims_X_same_as_old(self):
        with self.model:
            X_LL = self.X.logp(self.myTestPoint)
            #import pdb; pdb.set_trace()
            X_LL_Correct = -8.2511423611958445
            #X_LL_Correct = -13.10317262511546
            np.testing.assert_almost_equal(X_LL, X_LL_Correct, decimal = 6, err_msg="logp of X is incorrect")

    def test_claims_L_same_as_old(self):
        with self.model:
            L_LL = self.L.transformed.logp(self.myTestPoint)
            L_LL_Correct = -27.736136077452397
            np.testing.assert_almost_equal(L_LL, L_LL_Correct, decimal = 6, err_msg="logp of O is incorrect")

    def test_claims_O_same_as_old(self):
        with self.model:
            defaultVal = self.testClaims.logp(self.model.test_point)
            defaultCorrect = -258.46778148992826
            claims_LL = self.testClaims.logp(self.myTestPoint)
            claims_LL_Correct = -252.1491658970591

            np.testing.assert_almost_equal(defaultVal, defaultCorrect, decimal = 6, err_msg="logp of O is incorrect for default input")
            np.testing.assert_almost_equal(claims_LL, claims_LL_Correct, decimal = 6, err_msg="logp of O is incorrect")

    def test_forwardS_same_as_old(self):
        #import pdb; pdb.set_trace()
        Qtest = np.array([[-3.,2.,1.],[3.,-6.,3.],[1.,1.,-2.]])
        pS_Test = self.forS.compute_pS(Qtest,self.M)
        pS_Correct = np.array([[[ 0.36139104,  0.19639045,  0.44221851],[ 0.34890514,  0.19355079,  0.45754407],[ 0.33357958,  0.18872767,  0.47769275]]])
        np.testing.assert_array_almost_equal(pS_Test, pS_Correct, err_msg="forwardS test off",decimal = 6)
#        with self.model:
#            #import pdb; pdb.set_trace()
#            np.random.seed(1933)
#            stepS_Test = self.forS.astep(self.myTestPoint)
#            stepS_Correct = np.array([[ 0,  2,  2,  2],[ 0,  0, -1, -1],[ 2,  2,  2, -1],[ 0,  2,  2,  2],[ 0,  0, -1, -1]], dtype=np.int8)
#            np.testing.assert_array_equal(stepS_Test, stepS_Correct, err_msg="first forwardS test off")
#
#            np.random.seed(13)
#            stepS_Test = self.forS.astep(self.myTestPoint)
#            stepS_Correct = np.array([[ 2,  2,  2,  2],[ 0,  1, -1, -1],[ 2,  2,  2, -1],[ 2,  2,  2,  2],[ 2,  2, -1, -1]], dtype=np.int8)
#            np.testing.assert_array_equal(stepS_Test, stepS_Correct, err_msg="second forwardS test off")

    def test_forwardX_same_as_old(self):
        pX_Test = self.forX.computeLikelihoodOfXk(0,self.myTestPoint['X'],logistic.cdf(self.myTestPoint['Z_logodds']),logistic.cdf(self.myTestPoint['L_logodds']))
        pX_Correct = np.array([[[ 0.1042057 ,  0.02448445],[ 0.1042057 ,  0.02225859],[ 0.1042057 ,  0.02225859],[ 0.1042057 ,  0.02225859]],
       [[ 0.1042057 ,  0.02225859],[ 0.1042057 ,  0.02448445],[ 0.1042057 ,  0.02225859],[ 0.1042057 ,  0.02225859]],
       [[ 0.07595709,  0.01703846],[ 0.07595709,  0.01703846],[ 0.1042057 ,  0.02225859],[ 0.1042057 ,  0.02225859]],
       [[ 0.07595709,  0.01703846],[ 0.1042057 ,  0.02225859],[ 0.1042057 ,  0.02448445],[ 0.1042057 ,  0.02448445]],
       [[ 0.1042057 ,  0.02225859],[ 0.1042057 ,  0.02225859],[ 0.1042057 ,  0.02225859],[ 0.1042057 ,  0.02448445]]])
        np.testing.assert_array_almost_equal(pX_Test, pX_Correct, err_msg="forwardX likelihood test off",decimal = 6)
#        with self.model:
#            np.random.seed(1933)
#            stepX_Test = self.forX.step(self.myTestPoint)['X']
#            stepX_Correct = np.array([[[0, 0, 0, 0, 0],
#        [0, 0, 0, 0, 0],
#        [0, 0, 0, 0, 0],
#        [0, 0, 0, 0, 1]],
#
#       [[0, 0, 0, 0, 0],
#        [0, 0, 0, 0, 0],
#        [1, 0, 0, 0, 0],
#        [1, 0, 0, 0, 0]]], dtype=np.int8) 
#            np.testing.assert_array_equal(stepX_Test, stepX_Correct, err_msg="first forwardX test off")
#
#            np.random.seed(19)
#            stepX_Test = self.forX.step(self.myTestPoint)['X']
#            stepX_Correct = np.array([[[0, 0, 0, 0, 0],
#        [0, 0, 0, 1, 0],
#        [0, 0, 0, 1, 0],
#        [0, 0, 0, 1, 0]],
#
#       [[0, 1, 0, 0, 0],
#        [0, 1, 0, 0, 0],
#        [0, 1, 0, 0, 0],
#        [0, 1, 0, 0, 1]]], dtype=np.int8)
#            np.testing.assert_array_equal(stepX_Test, stepX_Correct, err_msg="second forwardX test off")

if __name__ == '__main__':
    unittest.main()
