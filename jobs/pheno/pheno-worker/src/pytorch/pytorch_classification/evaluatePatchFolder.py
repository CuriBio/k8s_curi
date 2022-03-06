import argparse
import os
import shutil
import time
import folder
from PIL import Image
import torch
import logging
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.distributed as dist
import torch.optim
import torch.utils.data
import torch.utils.data.distributed
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import torchvision.models as models
from train import getModelForFineTune

model_names = sorted(name for name in models.__dict__
    if name.islower() and not name.startswith("__")
    and callable(models.__dict__[name]))

parser = argparse.ArgumentParser(description='PyTorch ImageNet Training')
parser.add_argument('--data', metavar='DIR', help='path to dataset')
parser.add_argument('--arch', '-a', metavar='ARCH', default='resnet50', choices=model_names, help='model architecture: ' +' | '.join(model_names) + ' (default: resnet50)')
parser.add_argument('--num_classes', default=4, type=int, metavar='N', help='number of classes in the net (default: 4)')
parser.add_argument('-c', '--precrop-size', default=224, type=int, help='pre crop image size (default: 224)')
parser.add_argument('--checkpoint', default='', type=str, metavar='PATH', help='path to latest checkpoint (default: none)')
parser.add_argument('--cpu', dest='cpu', action='store_true', help='use CPU only')
parser.add_argument('--workers', default=2, type=int, help='number of data loading workers (default: 2)')
parser.add_argument('--outputfolder', default='./misclassified', type=str, metavar='PATH', help='outputfolder')
parser.add_argument('--log-file', default='evaluate.log', type=str, help='the log file')

def main():
    global args
    args = parser.parse_args()
    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered evaluate')
    logging.info("evaluation setup={}".format(args))

    if args.arch=='inception_v3':
        input_image_size = 299
    else:
        input_image_size = 224

    # load/define data
    testdir = os.path.join(args.data)
    preprocess = transforms.Compose([
                transforms.Resize(args.precrop_size),
                transforms.CenterCrop(input_image_size),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225])
                ])

    test_dataset = datasets.ImageFolder(testdir, preprocess)
    imgs = test_dataset.imgs
    test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=1, shuffle=False, num_workers=args.workers)
    num_classes = args.num_classes

    # create model
    if os.path.isfile(args.checkpoint):
        print("=> loading the checkpoint '{}'".format(args.checkpoint))
        model = models.__dict__[args.arch](pretrained=True)

        model = getModelForFineTune(model, args.arch, num_classes)

        checkpoint = torch.load(args.checkpoint)
        model.load_state_dict(checkpoint['state_dict'])
        print("=> loaded checkpoint '{}' (epoch {})".format(args.checkpoint, checkpoint['epoch']))
        model.cuda()

    else:
        print("checkpoint path is invalid")
        exit()


    # output dir
    if not os.path.exists(args.outputfolder):
        os.makedirs(args.outputfolder)
    results = os.path.join(args.outputfolder, "evaluation.txt")

    model.eval()
    c = 0
    with torch.no_grad():
        for i, (input, target) in enumerate(test_loader):

            filename, label = imgs[i]
            target = target.cuda(non_blocking=True)

            # compute output
            output = model(input.cuda())
            pred = output.data.cpu().numpy().argmax()

            print('{}\t True:{}\t Pred:{}'.format(filename, label, pred))
            print('{}\t True:{}\t Pred:{}'.format(filename, label, pred), file=open(results,"a"))

            if label==pred:
                c = c+1

    print('accuracy: {}'.format(100*float(c)/len(test_loader)))


if __name__ == '__main__':
    main()
