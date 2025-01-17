
# Dependancies

"""# Import packages"""

from __future__ import print_function
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.optim as optim
import torch.utils.data
import torchvision.datasets as dset
import torchvision.transforms as transforms
import torchvision.utils as vutils
from torch.autograd import Variable
from torch import save
from torch import load

from torchvision.datasets import FashionMNIST
from torch.utils.data import DataLoader

import numpy as np
import matplotlib.pyplot as plt

from PIL import Image
from torchvision.utils import make_grid


print('PyTorch version:', torch.__version__)

"""# Load the datasets"""

batchSize = 64
imageSize = 28

# transform for the training data
transform = transforms.Compose([transforms.Resize(imageSize,imageSize),transforms.ToTensor(), transforms.Normalize(mean=[0.5], std=[0.5])])

# load datasets, downloading if needed
train_set = FashionMNIST('~/.pytorch/F_MNIST_data/', train=True, download=True, transform=transform)

print(train_set.train_data.shape)

"""# Preview the data"""

plt.figure(figsize=(10,10))

sample = train_set.train_data[:64]
# shape (64, 28, 28)
sample = sample.reshape(8,8,28,28)
# shape (8, 8, 28, 28)
sample = sample.permute(0,2,1,3)
# shape (8, 28, 8, 28)
sample = sample.reshape(8*28,8*28)
# shape (8*28, 8*28)
plt.imshow(sample)
plt.xticks([])
plt.yticks([])
plt.grid(False)
plt.title('First 64 MNIST digits in training set')
plt.show()

print('Labels:', train_set.train_labels[:64].numpy())

"""# Setup the data loaders"""

dataloader = DataLoader(train_set, batch_size=batchSize, shuffle=True, num_workers = 2)

"""# Weights Initialisation"""

def weights_init(m):
  classname = m.__class__.__name__
  if classname.find('Conv') != -1:
    m.weight.data.normal_(0.0, 0.02)
  elif classname.find('BatchNorm') != -1:
    m.weight.data.normal_(1.0, 0.02)
    m.bias.data.fill_(0)

"""# Generator Network"""

class G(nn.Module):

  def __init__(self):
    super(G, self).__init__()
    self.main = nn.Sequential(
            nn.Linear(100, 256),
            nn.ReLU(),
            nn.Linear(256, 512),
            nn.ReLU(),
            nn.Linear(512, 1024),
            nn.ReLU(),
            nn.Linear(1024,(28*28)),
            nn.Tanh()
        )

  def forward(self, input):
    input = input.view(input.size(0), 100)
    output = self.main(input)
    return output.view(output.size(0), 28, 28)

netG = G().cuda()
netG.apply(weights_init)

"""# Descriminator Network"""

class D(nn.Module):

  def __init__(self):
    super(D, self).__init__()
    self.main = nn.Sequential(
            nn.Linear((28*28), 1024),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 1),
            nn.Sigmoid()

        )

  def forward(self, input):
    input = input.view(input.size(0), 784)
    output = self.main(input)
    return output.squeeze()

netD = D().cuda()
netD.apply(weights_init)

"""# Train the DCGANs"""

criterion = nn.BCELoss().cuda()
optimizerD = optim.Adam(netD.parameters(), lr=0.0002, betas =(0.5,0.999))
optimizerG =optim.Adam(netG.parameters(), lr=0.0002, betas =(0.5,0.999))

num_epochs = 50

for epoch in range(num_epochs):

  for i, data in enumerate(dataloader, 0): #data -> mini batchs

    # ----- Train Descriminator ------
    netD.zero_grad() #Initialise to 0 the Grad of the netD


    #Train Descriminator w/ Real Images
    real,_ = data
    input = Variable(real).cuda()
    target = Variable(torch.ones(input.size()[0])).cuda() #real images -> label = 1
    output = netD(input)
    lossD_real = criterion(output, target)

    #Train Descriminator w/ fake Images
    noise = Variable(torch.randn(input.size()[0], 100, 1, 1)).cuda()
    fake = netG(noise).unsqueeze(1)
    target = Variable(torch.zeros(input.size()[0])).cuda() #fake images -> label = 0
    output = netD(fake.detach())
    lossD_fake = criterion(output, target)

    #Descriminator Backpropagation
    lossD = lossD_real + lossD_fake
    lossD.backward()
    optimizerD.step() #Update the weights of the Descriminator


    # ----- Train Generator ------
    netG.zero_grad() #Initialise to 0 the Grad of the netG
    target = Variable(torch.ones(input.size()[0])).cuda()
    output = netD(fake) #check btw 0 and 1 validity of the generated image
    lossG = criterion(output, target)

    #Generator Backpropagation
    lossG.backward()
    optimizerG.step() #Update the weights of the Generator


    # ----- Visualize the trainning -----
    print("[Epoch %d/%d] [Batch %d/%d] [D loss: %f] [G loss: %f]"
#             % (epoch, num_epochs, i, len(dataloader), lossD.data, lossG.data))


    if i % 200 == 0:
        vutils.save_image(real, '%s/Real_samples.png' % "./results", normalize = True)
        fake = netG(noise).unsqueeze(1).data.cpu()
        vutils.save_image(fake.data, '%s/fake_samples_epoch_%03d_batch_%d.png' % ("./results", epoch,i), normalize=True)
        grid = make_grid(fake, normalize=True).permute(1,2,0).numpy()
        plt.imshow(grid)
        plt.show()

"""# Save the Model"""

# Save trained models
save(netG.state_dict(), './saved_models/netG.weight')
save(netD.state_dict(), './saved_models/netD.weight')

"""# Load the Model / Test"""

netG_test = G()
netG_test.load_state_dict(load('./saved_models/netG.weight'))
noise = Variable(torch.randn(input.size()[0], 100, 1, 1))

output_test = netG_test(noise)

for image in output_test:
    image = image.view(28,28).data
    plt.imshow(image, cmap='Greys')
    plt.axis('off')
plt.show()
