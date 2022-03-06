import argparse
import os
import shutil
import time
import folder
import patch
from skimage import io, img_as_ubyte, img_as_float
from PIL import Image
import numpy as np
import sys
import torch
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
import logging
import re
from train import getModelForFineTune
import optimPatch
import cv2

model_names = sorted(name for name in models.__dict__
    if name.islower() and not name.startswith("__")
    and callable(models.__dict__[name]))

parser = argparse.ArgumentParser(description='PyTorch Image Classification')
arg=parser.add_argument
arg('inputfolder', help='path to image folder')
arg('--arch', '-a', metavar='ARCH', default='resnet50', help='model architectures'+' (default: resnet50)')
arg('--checkpoint', default='', type=str, metavar='PATH', help='path to latest checkpoint (default: none)')
arg('-c', '--precrop-size', default=224, type=int, help='pre crop image size (default: 224)')
arg('-pr', '--patches-rows', default=1, type=int, help='number of patches along rows (default: 1)')
arg('-pc', '--patches-cols', default=1, type=int, help='number of patches along columns (default: 1)')
arg('--maskfolder', default=None, type=str, help='path to mask folder for patching')
arg('-pw','--patch_width', default=224, type=int, help='patch width, applied only if maskfolder is set')
arg('--noscale', default='false', type=str, help='keep the original intensity of patch')
arg('--convert2gray', default='false', type=str, help='convert to grayscale if set to true')
arg('--num-classes', default=2, type=int, help='number of classes')
arg('--cpu', dest='cpu', action='store_true', help='use CPU only')
arg('--log-file', default='classify.log', type=str, help='the log file')

# ------------------------------------------ #
def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
    return sorted(l, key = alphanum_key)

# ------------------------------------------ #
def main(argsIn):
    global args, GPU
    args = parser.parse_args(argsIn)
    GPU = not args.cpu

    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered classify main')
    logging.info("classification setup={}".format(args))

    if args.arch=='inception_v3':
        input_image_size = 299
    else:
        input_image_size = 224
    logging.info("image dimension ={}".format(input_image_size))

    if args.precrop_size < input_image_size:
        args.precrop_size = input_image_size

    if args.noscale=='true' or args.noscale=='True' :
        normalize=False
    else:
        normalize=True

    if args.convert2gray=='true' or args.convert2gray=='True':
        convert2gray = True
    else:
        convert2gray = False


    preprocess = transforms.Compose([
                transforms.Resize(args.precrop_size),
                transforms.CenterCrop(input_image_size),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225])
                ])

    num_classes = args.num_classes

    # create model
    if os.path.isfile(args.checkpoint):
        logging.info("=> loading the checkpoint '{}'".format(args.checkpoint))
        model = models.__dict__[args.arch](pretrained=True)

        model = getModelForFineTune(model, args.arch, num_classes)

        checkpoint = torch.load(args.checkpoint)
        model.load_state_dict(checkpoint['state_dict'])
        logging.info("=> loaded checkpoint '{}' (epoch {})".format(args.checkpoint, checkpoint['epoch']))
        if GPU:
            model.cuda()

    else:
        logging.info("checkpoint path is invalid - exiting")
        exit()


    model.eval()

    # parse the input folder
    input_folder = args.inputfolder
    imagefiles = []
    for root, dirs, files in os.walk(input_folder):
         for fileName in files:
            relDir = os.path.relpath(root, input_folder)
            relFile = os.path.join(relDir, fileName)
            if '__MACOSX' not in relFile and folder.is_image_file(fileName):
                imagefiles.append(relFile)
    imagefiles = [filename.replace('./','') for filename in imagefiles]

    # sort
    imagefiles = natural_sort(imagefiles)

    all_probs = []

    with torch.no_grad():

        for i, image_fn in enumerate(imagefiles):
            # read raw image
            imgPath = os.path.join(input_folder,image_fn)
            img = folder.default_loader(imgPath)

            # make patches
            image_patches =[]
            if args.maskfolder is None:
                image_patches = patch.image2patches(img_as_ubyte(np.asarray(img)), args.patches_rows, args.patches_cols, normalize, convert2gray)
            else:
                # load the mask
                mask = cv2.imread(os.path.join(args.maskfolder, image_fn))
                image_patches = optimPatch.image2patches(img_as_ubyte(np.asarray(img)), mask, args.patch_width, normalize, convert2gray)

            if len(image_patches)>0:
                # process patches and convert to tensor
                probs = np.zeros((len(image_patches),num_classes))
                for p, apatch in enumerate(image_patches):

                    patch_tensor = preprocess(Image.fromarray(img_as_ubyte(apatch)))
                    patch_tensor.unsqueeze_(0)

                    # run prediction
                    if GPU:
                        output = model(img_var.cuda())
                        smax = nn.Softmax().cuda()
                        smax_out = smax(output)
                        prob_patch = smax_out.data.cpu().numpy()
                    else:
                        output = model(img_var)
                        smax = nn.Softmax()
                        smax_out = smax(output)
                        prob_patch = smax_out.data.numpy()

                probs[p,:]= prob_patch
            else:
                probs = (-1)*np.ones((1, num_classes))

            # write to file
            prob = np.sum(probs, axis=0)/probs.shape[0]
            probList = ["{:0.2f}".format(x) for x in prob]
            logging.info("Filename: {}, probs: {}".format(imgPath, ','.join(probList)))

            # store the img probs
            all_probs.append(probs)

    return(all_probs, imagefiles)

if __name__ == '__main__':
    main(sys.argv[1:])
