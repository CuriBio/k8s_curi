import argparse
import os
import shutil
import time
import sys
import logging
import tqdm
import re

import torch
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.distributed as dist
import torch.optim
import torch.utils.data
import torch.utils.data.distributed
from torchvision.transforms import Compose, Resize, RandomHorizontalFlip, ToTensor, CenterCrop, Normalize
import torchvision.datasets as datasets
import torchvision.models as models

from loss import LossRegression

from torch.optim import lr_scheduler

model_names = sorted(name for name in models.__dict__
    if name.islower() and not name.startswith("__")
    and callable(models.__dict__[name]))

parser = argparse.ArgumentParser(description='Dana PyTorch Training - Classification')
arg=parser.add_argument
arg('data', metavar='DIR', help='path to dataset')
arg('--arch', '-a', metavar='ARCH', default='resnet50',choices=model_names, help='model architecture: ' +' | '.join(model_names) +' (default: resnet18)')
arg('--mode', default='categorical', choices=['categorical', 'regression'])
arg('-j', '--workers', default=0, type=int, help='number of data loading workers (default: 0)')
arg('-c', '--precrop-size', default=224, type=int, help='pre crop image size (default: 224)')
arg('--epochs', default=90, type=int,  help='number of total epochs to run')
arg('--start-epoch', default=0, type=int,  help='manual epoch number (useful on restarts)')
arg('-b', '--batch-size', default=32, type=int,  help='mini-batch size (default: 256)')
arg('--lr', '--learning-rate', default=0.01, type=float,  help='initial learning rate')
arg('--momentum', default=0.9, type=float,  help='momentum')
arg('--max_iters_per_epoch', default=100000, type=int, help='maximum number of iterations in each epoch')
arg('--weight-decay', '--wd', default=1e-4, type=float, help='weight decay (default: 1e-4)')
arg('--print-freq', '-p', default=1000, type=int,  help='print frequency (default: 1000)')
arg('--checkpoint', default='', type=str, metavar='PATH', help='path to latest checkpoint (default: none)')
arg('--stopping-criteria', default='epochs', type=str,  help='when to stop training (epochs/time/accuarcy)')
arg('--transfer', dest='transfer', action='store_true', help='do transfer learning')
arg('--weighted_sampling', dest='weighted_sampling', action='store_true', help='use weighted sampling to balance sample sizes the net sees per class' )
arg('--reg_weight', default=10.0, type=float,help="penalty weight for regression")
arg('--cpu', dest='cpu', action='store_true', help='use CPU only')
arg('--augment', dest='augment', action='store_true', help='apply data augmentation (flipping)')
arg('--outputfolder', default='./output', type=str, metavar='PATH', help='outputfolder')
arg('--progress-upload-key', default='', type=str, help='aws object key for the progress file')
arg('--log-file', default='train.log', type=str, help='the log file')

class MetadataModel(nn.Module):
    def __init__(self, arch, lenMetadata):
        super(MetadataModel, self).__init__()
        self.cnn = models.__dict__[arch](pretrained=True)
        self.cnn.fc = nn.Linear(self.cnn.fc.in_features, 20)
        self.fc1 = nn.Linear(20 + lenMetadata, 60)
        self.fc2 = nn.Linear(60, 2)
    def forward(self, image, data):
        x1 = self.cnn(image)
        x2 = data
        x = torch.cat((x1, x2), dim=1)
        x = nn.functional.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class ImageFolderWithPaths(datasets.ImageFolder):
    def __getitem__(self, index):
        original_tuple = super(ImageFolderWithPaths, self).__getitem__(index)
        path = self.imgs[index][0]
        tuple_with_path = (original_tuple + (path,))
        return tuple_with_path

best_prec1 = 0
def make_weights_for_balanced_classes(images, nclasses):
    count = [0] * nclasses
    for item in images:
        count[item[1]] += 1
    weight_per_class = [0.] * nclasses
    N = float(sum(count))
    for i in range(nclasses):
        weight_per_class[i] = N/float(count[i])
    weight = [0] * len(images)
    for idx, val in enumerate(images):
        weight[idx] = weight_per_class[val[1]]
    return weight, count


def get_scheduler(optimizer, opt):
    if opt.lr_policy == 'lambda':
        def lambda_rule(epoch):
            lr_l = 1.0 - max(0, epoch + 1 + opt.epoch_count - opt.niter) / float(opt.niter_decay + 1)
            return lr_l
        scheduler = lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda_rule)
    elif opt.lr_policy == 'step':
        scheduler = lr_scheduler.StepLR(optimizer, step_size=opt.lr_decay_iters, gamma=0.1)
    elif opt.lr_policy == 'plateau':
        scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.2, threshold=0.01, patience=5)
    elif opt.lr_policy == 'cosine':
        scheduler = lr_scheduler.CosineAnnealingLR(optimizer, T_max=opt.niter, eta_min=0)
    else:
        return NotImplementedError('learning rate policy [%s] is not implemented', opt.lr_policy)
    return scheduler


def getModelForFineTune(model, arch, num_classes):

    if ('resnet' in arch) or ('inception' in arch):
        num_ftrs = model.fc.in_features
        model.fc = nn.Linear(num_ftrs, num_classes)

    elif 'vgg' in arch:
        num_ftrs = model.classifier[6].in_features
        feature_model = list(model.classifier.children())
        feature_model.pop()
        feature_model.append(nn.Linear(num_ftrs, num_classes))
        model.classifier = nn.Sequential(*feature_model)

    elif 'densenet' in arch:
        num_ftrs = model.classifier.in_features
        model.classifier = nn.Linear(num_ftrs, num_classes)

    elif 'squeezenet' in arch:
        in_ftrs = model.classifier[1].in_channels
        features = list(model.classifier.children())
        features[1] = nn.Conv2d(in_ftrs, num_classes, kernel_size=1)
        features[3] = nn.AvgPool2d(13, stride=1)
        model.classifier = nn.Sequential(*features)
        model.num_classes = num_classes

    return model


def main(argsIn):

    global args, best_prec1, GPU
    global metadata
    args = parser.parse_args(argsIn)
    do_weighted_sampling = args.weighted_sampling
    best_prec1 = 0

    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered train main')
    print("Training setup={}".format(args))
    logging.info("Training setup={}".format(args))

    # GPU or CPU
    GPU = not args.cpu

    if GPU:
       torch.cuda.empty_cache()


    # load/define data
    traindir = os.path.join(args.data, 'Train')
    valdir = os.path.join(args.data, 'Val')

    if not os.path.exists(args.outputfolder):
        os.makedirs(args.outputfolder)

    # transforms
    normalize = Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

    if args.arch=='inception_v3':
        input_image_size = 299
    else:
        input_image_size = 224

    if args.precrop_size < input_image_size:
        args.precrop_size = input_image_size

    if args.precrop_size==input_image_size:
        if args.augment:
            train_transforms = Compose([Resize(input_image_size),RandomHorizontalFlip(),ToTensor(),normalize])
        else:
            train_transforms = Compose([Resize(input_image_size),ToTensor(),normalize])
    else:
        if args.augment:
            train_transforms = Compose([Resize(args.precrop_size),CenterCrop(input_image_size),RandomHorizontalFlip(),ToTensor(),normalize])
        else:
            train_transforms = Compose([Resize(args.precrop_size),CenterCrop(input_image_size),ToTensor(),normalize])

    # train dataset
    train_dataset = datasets.ImageFolder(traindir, train_transforms)
    train_imgs = train_dataset.imgs
    classes = train_dataset.classes
    logging.info("classes: '{}'".format(classes))
    num_classes = len(classes)

    # val dataset
    val_dataset =  datasets.ImageFolder(valdir, Compose([Resize(args.precrop_size), CenterCrop(input_image_size), ToTensor(), normalize]))
    val_imgs = val_dataset.imgs

    # check for metadata in filename
    metadata = False
    if '_smeta_' in val_imgs[0][0] and 'resnet' in args.arch:
        logging.info("Using metadata")
        metadata = True
        mdata = re.search("smeta_(.*?)_emeta", val_imgs[0][0]).group(1)
        params = mdata.split("_")
        lenMetadata = len(params)
        logging.info("length of metadata: {}".format(lenMetadata))
        # datasets override to get paths
        train_dataset = ImageFolderWithPaths(traindir, train_transforms)
        val_dataset = ImageFolderWithPaths(valdir, Compose([Resize(args.precrop_size), CenterCrop(input_image_size), ToTensor(), normalize]))

    # if weighted sampling
    if do_weighted_sampling:
        weights, count = make_weights_for_balanced_classes(train_dataset.imgs, num_classes)
        logging.info("counts per class in train: {}".format(count))
        weights_train = torch.DoubleTensor(weights)
        sampler_train = torch.utils.data.sampler.WeightedRandomSampler(weights_train, len(weights_train))

        # do for val too?
        weights, count = make_weights_for_balanced_classes(val_dataset.imgs, num_classes)
        logging.info("counts per class in val: {}".format(count))
        weights_val = torch.DoubleTensor(weights)
        sampler_val = torch.utils.data.sampler.WeightedRandomSampler(weights_val, len(weights_val))

        shuffle = False
    else:
        sampler_train = None
        sampler_val = None
        shuffle = True

    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=args.batch_size, shuffle= shuffle, num_workers=args.workers, pin_memory=not args.cpu, sampler=sampler_train)

    val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, sampler=sampler_val, num_workers=args.workers, pin_memory=not args.cpu)

    if os.path.isfile(os.path.join(args.outputfolder, "model_best.pth.tar")):
        checkpoint_path = os.path.join(args.outputfolder, "model_best.pth.tar")
        print("=> loading the checkpoint '{}'".format(checkpoint_path))
        logging.info("=> loading the checkpoint '{}'".format(checkpoint_path))

        model = models.__dict__[args.arch]()
        if args.transfer:
            print("=> transfer learning")
            logging.info("=> transfer learning")
            for param in model.parameters():
                param.requires_grad = False

        checkpoint = torch.load(checkpoint_path)
        args.start_epoch = 0
        if 'ckp_num_classes' in checkpoint:
            num_classes = checkpoint['ckp_num_classes']
            logging.info("number of classes in loaded checkpoint is {}".format(num_classes))

            model = getModelForFineTune(model, args.arch, num_classes)

            model.load_state_dict(checkpoint['state_dict'])

    else:
        print("=> using pre-trained model '{}'".format(args.arch))
        logging.info("=> using pre-trained model '{}'".format(args.arch))

        model = models.__dict__[args.arch](pretrained=True)
        if args.transfer:
            print("=> transfer learning")
            logging.info("=> transfer learning")
            for name, child in model.named_children():
                if name in ['layer2','layer3','layer4']:
                    for param in child.parameters():
                        param.requires_grad = True

                else:
                    for param in child.parameters():
                        param.requires_grad = False

            # for param in model.parameters():
            #    param.requires_grad = False

        if args.mode == 'categorical':
            model = getModelForFineTune(model, args.arch, num_classes)
        else: # regression
            num_classes = 1
            model = getModelForFineTune(model, args.arch, 1)

    # if metadata override model
    if metadata:
        model = MetadataModel(args.arch, lenMetadata)

    ##### Training setup ##################################
    # GPU
    if GPU:
        model.cuda()
        print("=> using GPU")
        logging.info("=> using GPU")


    if args.transfer:
        # optimizer = torch.optim.SGD(model.fc.parameters(), args.lr,
        #                             momentum=args.momentum,
        #                             weight_decay=args.weight_decay)
        optimizer = torch.optim.SGD(filter(lambda p: p.requires_grad, model.parameters()), args.lr,
                                    momentum=args.momentum,
                                    weight_decay=args.weight_decay)


    else:
        optimizer = torch.optim.SGD(model.parameters(), args.lr,
                                    momentum=args.momentum,
                                    weight_decay=args.weight_decay)


    if args.mode == 'categorical':
        criterion = nn.CrossEntropyLoss()
        if GPU:
            criterion = criterion.cuda()
            cudnn.benchmark = True

    else: # regression

        criterion = LossRegression(reg_weight=args.reg_weight,out_min=-1.0,out_max=len(classes))


    print("=> testing on validation data")
    logging.info("=> testing on validation data")
    acc_0, loss_0 = validate(val_loader, model, criterion, args)
    train_accuracy = 0

    print("=> training")
    logging.info("=> training")
    progress = os.path.join(args.outputfolder, "progress.txt")
    print("epoch,training_accuracy,training_loss,val_accuracy,val_loss", file=open(progress, "w"))
    print("{0},{1:.4f},{2:.4f},{3:.4f},{4:.4f}".format(0,0.0,5.0,acc_0,loss_0), file=open(progress, "a"))

    if args.mode == 'categorical':
        scheduler = lr_scheduler.ExponentialLR(optimizer, gamma = 0.90)
    else:
        scheduler = lr_scheduler.ExponentialLR(optimizer, gamma = 1.0)

    for epoch in range(args.start_epoch, args.epochs):

        # train for one epoch
        prec1_train, loss_train = train(train_loader, model, criterion, optimizer, epoch, args)

        # evaluate on validation set
        prec1, loss_val = validate(val_loader, model, criterion, args)

        scheduler.step()

        # for param_group in optimizer.param_groups:
        #     print("learning rate is: ", param_group['lr'])

        # remember best prec@1 and save checkpoint
        is_best = prec1 >= best_prec1
        best_prec1 = max(prec1, best_prec1)
        if is_best:
            # keep the current train accuracy to report
            train_accuracy = prec1_train

        filename = 'checkpoint_last.pth.tar'
        save_checkpoint({
            'epoch': epoch + 1,
            'arch': args.arch,
            'state_dict': model.state_dict(),
            'best_prec1': best_prec1,
            'optimizer' : optimizer.state_dict(),
            'ckp_num_classes': num_classes,
        }, is_best, filename)


        print("{0},{1:.4f},{2:.4f},{3:.4f},{4:.4f}".format(epoch+1,prec1_train,loss_train,prec1,loss_val), file=open(progress, "a"))

        # upload progress
        if args.progress_upload_key:
            os.system('aws s3 cp '+progress+' s3://pheno-test/'+args.progress_upload_key)


def train(train_loader, model, criterion, optimizer, epoch, args):

    losses = AverageMeter()
    top1 = AverageMeter()
    top2 = AverageMeter()

    # switch to train mode
    model.train()

    end = time.time()
    for i, data in enumerate(train_loader):
        # get metadata for the batch
        if metadata:
            input, target, path = data
            train_metadata = []
            for fname in path:
                mdata = re.search("smeta_(.*?)_emeta", fname).group(1)
                params = mdata.split("_")
                train_metadata.append([float(val) for val in params])
            data = torch.tensor(train_metadata)
            if GPU:
                data = data.cuda()
        else:
            input, target = data

        if i<args.max_iters_per_epoch:

            sys.stdout.flush()

            if args.mode == 'regression':
                target = target.view(target.size(0),1).float()

            if GPU:
                target = target.cuda(non_blocking=True)
                input = input.cuda()

            # compute output
            if args.arch=='inception_v3':
                output, aux = model(input)
            else:
                if metadata:
                    output = model(input, data)
                else:
                    output = model(input)

            loss = criterion(output, target)
            losses.update(loss.item(), input.size(0))


            # measure accuracy and record loss
            if args.mode =='regression':
                prec1 = regression_accuracy(output.data, target)
                top1.update(prec1, input.size(0))
            else:
                prec1, prec2 = accuracy(output, target, topk=(1, 2))
                top1.update(prec1[0], input.size(0))

            # compute gradient and do SGD step
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            if i % args.print_freq == 0:
                logging.info('Epoch: [{0}][{1}/{2}]\t' 'Loss {loss.val:.4f} \t' 'Prec@1 {top1.val:.3f}'.format(epoch, i, len(train_loader), loss=losses, top1=top1))
        else:
            break


    logging.info('Train: Loss {losses.avg:.3f}\t Prec@1 {top1.avg:.3f}'.format(losses=losses, top1=top1))
    print('Train: Loss {losses.avg:.3f}\t Prec@1 {top1.avg:.3f}'.format(losses=losses, top1=top1))
    return top1.avg, losses.avg


def validate(val_loader, model, criterion, args):
    losses = AverageMeter()
    top1 = AverageMeter()
    top2 = AverageMeter()

    # switch to evaluate mode
    model.eval()

    with torch.no_grad():

        for i, data in enumerate(val_loader):
            # get metadata for the batch
            if metadata:
                input, target, path = data
                val_metadata = []
                for fname in path:
                    mdata = re.search("smeta_(.*?)_emeta", fname).group(1)
                    params = mdata.split("_")
                    val_metadata.append([float(val) for val in params])
                data = torch.tensor(val_metadata)
                if GPU:
                    data = data.cuda()
            else:
                input, target = data

            if args.mode == 'regression':
                target = target.view(target.size(0),1).float()

            if GPU:
                target = target.cuda(non_blocking=True)
                input = input.cuda()

            # compute output
            if metadata:
                output = model(input, data)
            else:
                output = model(input)
            loss = criterion(output, target)
            losses.update(loss.item(), input.size(0))

            # measure accuracy and record loss
            if args.mode =='regression':
                prec1 = regression_accuracy(output.data, target)
                top1.update(prec1, input.size(0))
            else:
                prec1, prec2 = accuracy(output.data, target, topk=(1, 2))
                top1.update(prec1[0], input.size(0))

        logging.info('Test: Loss {losses.avg:.3f}\t Prec@1 {top1.avg:.3f}'.format(losses=losses, top1=top1))
        print('Test: Loss {losses.avg:.3f}\t Prec@1 {top1.avg:.3f}'.format(losses=losses, top1=top1))

    return top1.avg, losses.avg


def save_checkpoint(state, is_best, filename):
    if not os.path.exists(args.outputfolder):
        os.makedirs(args.outputfolder)
    filename = os.path.join(args.outputfolder,filename)

    torch.save(state, filename)
    if is_best:
        shutil.copyfile(filename, os.path.join(args.outputfolder,'model_best.pth.tar'))


class AverageMeter(object):
    """Computes and stores the average and current value"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def accuracy(output, target, topk=(1,)):
    """Computes the precision@k for the specified values of k"""
    with torch.no_grad():
        maxk = max(topk)
        batch_size = target.size(0)

        _, pred = output.topk(maxk, 1, True, True)
        pred = pred.t()
        correct = pred.eq(target.view(1, -1).expand_as(pred))

        res = []
        for k in topk:
            correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)
            res.append(correct_k.mul_(100.0 / batch_size))
        return res


def regression_accuracy(output, target, pct_close=0.45):

    with torch.no_grad():
        batch_size = target.size(0)
        pred = output.view(batch_size,1)
        n_correct = torch.sum((torch.abs(pred - target) <= pct_close))
        acc = (n_correct.item() * 100.0 / batch_size)
        return acc


if __name__ == '__main__':
    main(sys.argv[1:])
