import argparse
import sys
import json
import logging
import os
from pathlib import Path
from validation import validation_binary, validation_multi

import torch
from torch import nn
from torch.optim import Adam
from torch.utils.data import DataLoader
import torch.backends.cudnn as cudnn
import torch.backends.cudnn

from models import UNet, UNet11, UNet16, LinkNet34, AlbuNet34
from loss import LossBinary, LossMulti
from dataset import SegmentationDataset
import utils

from transforms import (DualCompose,
                        ImageOnly,
                        Normalize,
                        HorizontalFlip,
                        RandomRotate90,
                        CenterCrop,
                        Resize,
                        RandomHueSaturationValue,
                        VerticalFlip)

parser = argparse.ArgumentParser(description='Dana PyTorch Training - Segmentation')
parser.add_argument('data', help='path to dataset')
parser.add_argument('--model', type=str, default='UNet', choices=['UNet', 'UNet11', 'LinkNet34', 'UNet16', 'AlbuNet34'])
parser.add_argument('-j', '--workers', default=2, type=int, help='number of data loading workers (default: 4)')
parser.add_argument('-c', '--center-crop', default=-1, type=int, help='center crop image size (default: -1, no crop)')
parser.add_argument('--labels', type=str, default='0,1', help='For example 0,127,256 to list labels of interest')
parser.add_argument('--epochs', default=90, type=int, metavar='N', help='number of total epochs to run')
parser.add_argument('-b', '--batch-size', default=32, type=int, help='mini-batch size (default: 256)')
parser.add_argument('--lr', '--learning-rate', default=0.01, type=float, help='initial learning rate')
parser.add_argument('--momentum', default=0.9, type=float, help='momentum')
parser.add_argument('--weight-decay', '--wd', default=1e-4, type=float, help='weight decay (default: 1e-4)')
parser.add_argument('--checkpoint', default='', type=str, help='path to latest checkpoint (default: none)')
parser.add_argument('--cpu', dest='cpu', action='store_true', help='use CPU only')
parser.add_argument('--outputfolder', default='./results', type=str, help='outputfolder')
parser.add_argument('--progress-upload-key', default='', type=str,help='aws object key for the progress file')
parser.add_argument('--log-file', default='temp.log', type=str, help='the log file')
parser.add_argument('--jaccard-weight', default=1, type=float)
parser.add_argument('--device-ids', type=str, default='0', help='For example 0,1 to run on two GPUs')

def main(argsIn):

    global args, best_prec1, GPU
    args = parser.parse_args(argsIn)

    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered train main')

    print("Training setup={}".format(args))
    logging.info("Training setup={}".format(args))

    # load/define data
    data_path = Path(args.data)
    traindir = data_path / 'Train'
    valdir = data_path / 'Val'

    # output/checkpoint dir
    root = Path(args.outputfolder)
    root.mkdir(exist_ok=True, parents=True)

    labels = list(map(int, args.labels.split(',')))

    if len(labels) == 2:
        num_classes = 1
        type='binary'
    else:
        num_classes = len(labels) # includes background
        type='multi'

    # needs to be tested
    train_file_names = list((traindir / 'IMG').glob('*'))
    val_file_names = list((valdir / 'IMG').glob('*'))

    logging.info('num train = {}, num_val = {}, num_classes = {}'.format(len(train_file_names), len(val_file_names), num_classes))
    # transforms
    cc = int(args.center_crop)
    if cc > 0:
        train_transform = DualCompose([
            CenterCrop((cc,cc)),
            HorizontalFlip(),
            VerticalFlip(),
            RandomRotate90(),
            ImageOnly(Normalize())
        ])

        val_transform = DualCompose([
            CenterCrop((cc,cc)),
            ImageOnly(Normalize())
        ])
    else:
        train_transform = DualCompose([
            HorizontalFlip(),
            VerticalFlip(),
            RandomRotate90(),
            ImageOnly(Normalize())
        ])

        val_transform = DualCompose([
            ImageOnly(Normalize())
        ])

    train_loader = DataLoader(dataset=SegmentationDataset(train_file_names, transform=train_transform, labels = labels ),
            shuffle=True,
            num_workers=args.workers,
            batch_size=args.batch_size,
            pin_memory=torch.cuda.is_available())

    val_loader = DataLoader(dataset=SegmentationDataset(val_file_names, transform=val_transform, labels= labels ),
            shuffle=False,
            num_workers=args.workers,
            batch_size=args.batch_size,
            pin_memory=torch.cuda.is_available())

    ## model
    if args.model == 'UNet':
        model = UNet(num_classes=num_classes)
    elif args.model == 'UNet11':
        model = UNet11(num_classes=num_classes, pretrained='vgg')
    elif args.model == 'UNet16':
        model = UNet16(num_classes=num_classes, pretrained='vgg')
    elif args.model == 'LinkNet34':
        model = LinkNet34(num_classes=num_classes, pretrained=True)
    elif args.model == 'AlbuNet':
        model = AlbuNet34(num_classes=num_classes, pretrained=True)
    else:
        model = UNet(num_classes=num_classes, input_channels=3)

    if torch.cuda.is_available():
        if args.device_ids:
            device_ids = list(map(int, args.device_ids.split(',')))
        else:
            device_ids = None
        model = nn.DataParallel(model, device_ids=device_ids).cuda()

    if type == 'binary':
        loss = LossBinary(jaccard_weight=args.jaccard_weight)
        valid = validation_binary
    else:
        loss = LossMulti(num_classes=num_classes, jaccard_weight=args.jaccard_weight)
        valid = validation_multi

    cudnn.benchmark = True

    # train
    utils.train(
        init_optimizer=lambda lr: Adam(model.parameters(), lr=lr),
        args=args,
        model=model,
        criterion=loss,
        train_loader=train_loader,
        valid_loader=val_loader,
        validation=valid,
        num_classes=num_classes
    )


if __name__ == '__main__':
    main(sys.argv[1:])
