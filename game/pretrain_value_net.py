import numpy as np
import torch
import torch.nn as nn
from torch.autograd import Variable
from networks import Critic_Giraffe 
from logger import Logger
from datetime import datetime
import argparse
import os
import random

logger = Logger('./tb_logs1')

parser = argparse.ArgumentParser()
parser.add_argument("-g", "--gpu", help="use gpu", action="store_true")
parser.add_argument("--usegpu", help="set cuda visible devices", type=int, default=[0,1,2,3],nargs='+')
parser.add_argument('-lp', '--lrpm', help="lr for PM", type=float, default=1e-3)
args = parser.parse_args()

class my_trainer(object):
    def __init__(self):
        self.num_epochs = 100
        self.batch_size = 32
        self.value_model = Critic_Giraffe()

        if args.gpu == True and torch.cuda.is_available():
            self.device = torch.device("cuda")
            torch.set_default_tensor_type(torch.cuda.FloatTensor)
        else:
            self.device = torch.device("cpu")
            torch.set_default_tensor_type(torch.FloatTensor)

        if self.device == torch.device("cuda") and torch.cuda.device_count() > 1:
            print ("Use", torch.cuda.device_count(), 'GPUs')
            self.value_model = nn.DataParallel(self.value_model)
        else:
            print ("Use CPU")


        self.value_model.to(self.device)

        self.optimizer = torch.optim.Adam(list(self.value_model.parameters()), lr=args.lrpm)
        self.criterion = nn.MSELoss() 
        self.input_stuff = np.load('/home/sai/deep_pepper_chess/game/features.txt.npy')
        self.gt_output_stuff = np.load('/home/sai/deep_pepper_chess/game/values.txt.npy')
        sizee = self.gt_output_stuff.shape[0]
        # np.resize(a,(2,3))
        np.resize(self.gt_output_stuff, (sizee,1))
        print(self.gt_output_stuff.shape)
        self.gt_output_stuff = np.expand_dims(self.gt_output_stuff, axis=1)
        self.back_prop()

    def do_train(self, input_batch, target_batch, i):
        self.value_model.train()
        self.optimizer.zero_grad()
        output = self.value_model(input_batch)
        loss = self.criterion(output, target_batch)
        loss.backward()
        self.optimizer.step()
        info = {'likelihood_loss': loss.item()}
        for tag, value in info.items():
            logger.scalar_summary(tag, value, i)
        # for tag, value in self.value_model.named_parameters():
        #     tag = tag.replace('.', '/')
        #     logger.histo_summary(tag, value.data.cpu().numpy(), i)
        #     logger.histo_summary(tag+'/perceptual_grad', value.grad.data.cpu().numpy(), i)

    def do_test(self, input_batch, target_batch, i):
        self.value_model.eval()
        output = self.value_model(input_batch)
        loss = self.criterion(output, target_batch)
        print("test loss is ", loss)

    def back_prop(self):

        my_size = self.input_stuff.shape[0]
        num_batches = int(my_size / self.batch_size) 
        print("total samples = ", my_size)
        print("batch size = ", self.batch_size)
        print("num_batches = ", num_batches)
        print(self.gt_output_stuff.shape)
        for j in range(self.num_epochs):
            for i in range(num_batches):
                print(j * num_batches + i)
                input_batch = self.input_stuff[i * self.batch_size: (i+1) * self.batch_size, :]
                input_batch = Variable(torch.FloatTensor(input_batch))
                input_batch = input_batch.to(self.device)

                target_batch = self.gt_output_stuff[i * self.batch_size: (i+1) * self.batch_size, :] 
                target_batch = Variable(torch.FloatTensor(target_batch))
                target_batch = target_batch.to(self.device)

                self.do_train(input_batch, target_batch, j * num_batches + i)

            home = '/home/sai/deep_pepper_chess/'
            str_date_time = datetime.now().strftime('%Y%m%d-%H%M%S')
            self.logfile = 'val_output-%s.txt'%str_date_time
            modelfile='value_models/'+'model_'+self.logfile
            self.vn_filepath=os.path.join(home,modelfile)
            torch.save(self.value_model.state_dict(), self.vn_filepath)

        print("backprop done")
        torch.save(self.value_model.state_dict(), self.vn_filepath)
        print ('value network model saved at %s.'%self.vn_filepath)

my_trainer()