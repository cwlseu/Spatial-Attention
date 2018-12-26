from __future__ import print_function, absolute_import
import time

import torch
from torch.autograd import Variable

from .evaluation_metrics import accuracy
from .utils.meters import AverageMeter
from .utils import Bar
from torch.nn import functional as F

class BaseTrainer(object):
    def __init__(self, model, criterion, X, Y, SMLoss_mode=0):
        super(BaseTrainer, self).__init__()
        self.model = model
        self.criterion = criterion

    def train(self, epoch, data_loader, optimizer, print_freq=1):
        self.model.train()


        batch_time = AverageMeter()
        data_time = AverageMeter()
        losses = AverageMeter()
        precisions = AverageMeter()
        end = time.time()

        bar = Bar('Processing', max=len(data_loader))
        for i, inputs in enumerate(data_loader):
            data_time.update(time.time() - end)

            inputs, targets = self._parse_data(inputs)
            loss_layer4, prec1 = self._forward(inputs, targets)
#===================================================================================
            loss = loss_layer4
            losses.update(loss.data[0], targets.size(0))
            precisions.update(prec1, targets.size(0))

            optimizer.zero_grad()
            torch.autograd.backward([ loss_layer4],[torch.ones(1).cuda(), torch.ones(1).cuda()])
            optimizer.step()

            batch_time.update(time.time() - end)
            end = time.time()

            # plot progress
            bar.suffix = 'Epoch: [{N_epoch}][{N_batch}/{N_size}] | Time {N_bt:.3f} {N_bta:.3f} | Data {N_dt:.3f} {N_dta:.3f} | Loss {N_loss:.3f} {N_lossa:.3f} | Prec {N_prec:.2f} {N_preca:.2f}'.format(
                      N_epoch=epoch, N_batch=i + 1, N_size=len(data_loader),
                              N_bt=batch_time.val, N_bta=batch_time.avg,
                              N_dt=data_time.val, N_dta=data_time.avg,
                              N_loss=losses.val, N_lossa=losses.avg,
                              N_prec=precisions.val, N_preca=precisions.avg,
							  )
            bar.next()
        bar.finish()



    def _parse_data(self, inputs):
        raise NotImplementedError

    def _forward(self, inputs, targets):
        raise NotImplementedError


class Trainer(BaseTrainer):
    def _parse_data(self, inputs):
        imgs, _, pids, _ = inputs
        inputs = [Variable(imgs)]
        targets = Variable(pids.cuda())
        return inputs, targets

    def _forward(self, inputs, targets):
        outputs = self.model(*inputs)
        index = (targets-751).data.nonzero().squeeze_()
		
        if isinstance(self.criterion, torch.nn.CrossEntropyLoss):
            loss_layer4 = self.criterion(outputs[1], targets)

            prec, = accuracy(outputs[1].data, targets.data)
            prec = prec[0]
                        
        elif isinstance(self.criterion, OIMLoss):
            loss, outputs = self.criterion(outputs, targets)
            prec, = accuracy(outputs.data, targets.data)
            prec = prec[0]
        elif isinstance(self.criterion, TripletLoss):
            loss, prec = self.criterion(outputs, targets)
        else:
            raise ValueError("Unsupported loss:", self.criterion)
        return loss_layer4, prec
