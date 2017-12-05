''' Version 1.000
 Code provided by Daniel Jiwoong Im and Chris Dongjoo Kim
 Permission is granted for anyone to copy, use, modify, or distribute this
 program and accompanying programs and documents for any purpose, provided
 this copyright notice is retained and prominently displayed, along with
 a note saying that the original programs are available from our
 web page.
 The programs and documents are distributed without any warranty, express or
 implied.  As the programs were written for research purposes only, they have
 not been tested to the degree that would be advisable in any important
 application.  All use of these programs is entirely at the user's own risk.'''

'''Demo of Generating images with recurrent adversarial networks.
For more information, see: http://arxiv.org/abs/1602.05110
'''


import sys, os
import numpy as np
import theano
import theano.tensor as T

from subnets.layers.utils import floatX


class Optimize():

    def __init__(self, opt_params):

        self.batch_sz, self.epsilon_gen, self.epsilon_dis, self.momentum, \
                self.num_epoch, self.N, self.Nv, self.Nt = opt_params      



    def ADAM(self, params, gparams, lr, beta1 = 0.1,beta2 = 0.001,epsilon = 1e-8, l = 1e-8):

        '''ADAM Code from 
            https://github.com/danfischetti/deep-recurrent-attentive-writer/blob/master/DRAW/adam.py
        '''
        self.m = [theano.shared(name = 'm', \
                value = np.zeros(param.get_value().shape,dtype=theano.config.floatX)) for param in params]
        self.v = [theano.shared(name = 'v', \
        	value = np.zeros(param.get_value().shape,dtype=theano.config.floatX)) for param in params]
        self.t = theano.shared(name = 't',value = np.asarray(1).astype(theano.config.floatX))
        updates = [(self.t,self.t+1)] 

        for param, gparam,m,v in zip(params, gparams, self.m, self.v):

            b1_t = 1-(1-beta1)*(l**(self.t-1)) 
            m_t = b1_t*gparam + (1-b1_t)*m
            updates.append((m,m_t))
            v_t = beta2*(gparam**2)+(1-beta2)*v
            updates.append((v,v_t))
            m_t_bias = m_t/(1-(1-beta1)**self.t)	
            v_t_bias = v_t/(1-(1-beta2)**self.t)
            updates.append((param,param - lr*m_t_bias/(T.sqrt(v_t_bias)+epsilon)))		

        return updates


    def ADAM2(self, params, grads, lr=0.0001, b1=0.0, b2=0.999, e=1e-8, l=1-1e-8):
        updates = []
        t = theano.shared(floatX(1.))
        b1_t = b1*l**(t-1)
   
        for p, g in zip(params, grads):
           m = theano.shared(p.get_value() * 0.)
           v = theano.shared(p.get_value() * 0.)
   
           m_t = b1_t*m + (1 - b1_t)*g
           v_t = b2*v + (1 - b2)*g**2
           m_c = m_t / (1-b1**t)
           v_c = v_t / (1-b2**t)
           p_t = p - (lr * m_c) / (T.sqrt(v_c) + e)
           updates.append((m, m_t))
           updates.append((v, v_t))
           updates.append((p, p_t) )
        updates.append((t, t + 1.))
        return updates


    def MGD(self, params, gparams, lr):

        #Update momentum
        for param in model.params:
            init = np.zeros(param.get_value(borrow=True).shape,
                            dtype=theano.config.floatX)
            deltaWs[param] = theano.shared(init)

        for param in model.params:
            updates_mom.append((param, param + deltaWs[param] * \
                            T.cast(mom, dtype=theano.config.floatX)))

        for param, gparam in zip(model.params, gparams):

            deltaV = T.cast(mom, dtype=theano.config.floatX)\
                    * deltaWs[param] - gparam * T.cast(lr, dtype=theano.config.floatX)     #new momentum

            update_grads.append((deltaWs[param], deltaV))
            new_param = param + deltaV

            update_grads.append((param, new_param))

        return update_grads


    def inspect_inputs(i, node, fn):
        print i, node, "input(s) value(s):", [input[0] for input in fn.inputs],


    def inspect_outputs(i, node, fn):
        print "output(s) value(s):", [output[0] for output in fn.outputs]


    def optimize_gan_hkl(self, model, lam1 = 0.00001):
        """
        optimizer for hkl packaged dataset. 
        Returns the updates for discirminator & generator and computed costs for the model.
        """

        # i = T.iscalar('i') 
        lr = T.fscalar('lr')
        Xu = T.fmatrix('X') 
       #  testing with real input
#         import hickle as hkl
        # data = hkl.load('/work/djkim117/lsun/church/preprocessed_toy_10/train_testing/0001.hkl') / 255.
        # data = data.astype('float32').transpose([3,0,1,2]);
        # a,b,c,d = data.shape
        # data = data.reshape(a,b*c*d)
        # Xu.tag.test_value = data 

        # we now have the error rate of the discriminator. (it requires output of generator so we have to include both) 
        
        cost_test, cost_sample  = model.cost_dis(Xu, self.batch_sz)
                                
        cost_disc = cost_test + cost_sample + lam1 * model.dis_network.weight_decay_l2()

        # pass to the gradient function the error rate and parameters for the discriminator
        cost_gen    = model.cost_gen(self.batch_sz) #\
                                #+ lam1 * model.gen_network.weight_decay_l2()

        gparams_gen = T.grad(cost_gen, model.gen_network.params)
        gparams_dis = T.grad(cost_disc, model.dis_network.params)
        
        import subnets.layers.someconfigs as someconfigs
        if someconfigs.clipg_gen==1:
            
            gparams_gen = self.clip_gradient(model.gen_network.params, gparams_gen, scalar=7)
            # print 'clip_gen'
        
        if someconfigs.clipg_dis==1:
            
            gparams_dis = self.clip_gradient(model.dis_network.params, gparams_dis, scalar=7)
            # print 'clip_dis'
        

        updates_dis = self.ADAM2(model.dis_network.params, gparams_dis, lr)
        # print("updates_dis: ", updates_dis)
        updates_gen = self.ADAM2(model.gen_network.params, gparams_gen, lr)
        
        # disc_update contains the cost_disc value
        #discriminator_update = theano.function([Xu, lr],\
        #                     outputs=cost_disc, updates=updates_dis, \
        #                     givens=[(Xu, self.shared_x), (lr, self.shared_lr_dis)])
        discriminator_update = theano.function([Xu, theano.In(lr,value=self.epsilon_dis)],\
                                    outputs=[cost_test, cost_sample],updates=updates_dis)

        generator_update = theano.function([theano.In(lr,value=self.epsilon_gen)],\
                outputs=cost_gen, updates=updates_gen)


        get_valid_cost   = theano.function([Xu], outputs=[cost_test,cost_sample,cost_gen])

        get_test_cost   = None #theano.function([Xu], outputs=[cost_disc, cost_gen])


        return discriminator_update, generator_update, get_valid_cost, get_test_cost


    def get_samples(self, model):

        num_sam = T.iscalar('i'); 
        return theano.function([num_sam], model.get_samples(num_sam))


    def get_seq_drawing(self, model):
        
        num_sam = T.iscalar('i'); 
        return theano.function([num_sam], model.sequential_drawing(num_sam))
        
    def clip_gradient(self, params, gparams, scalar=5, check_nanF=True):
            """
                Sequence to sequence
            """
            num_params = len(gparams)
            g_norm = 0.
            for i in xrange(num_params):
                gparam = gparams[i]
                g_norm += (gparam**2).sum()
            if check_nanF:
                not_finite = T.or_(T.isnan(g_norm), T.isinf(g_norm))
            g_norm = T.sqrt(g_norm)
            scalar = scalar / T.maximum(scalar, g_norm)
            if check_nanF:
                for i in xrange(num_params):
                    param = params[i]
                    gparams[i] = T.switch(not_finite, 0.1 * param, gparams[i] * scalar)
            else:
                for i in xrange(num_params):
                    gparams[i]  = gparams[i] * scalar

            return gparams
