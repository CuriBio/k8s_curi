import argparse
import os
import shutil
import time
import numpy as np
from skimage import measure, io, transform, img_as_ubyte, img_as_float, exposure, color
import sys
import math
import cv2
import torch.utils.data
import torchvision.transforms as transforms
import folder
import logging

parser = argparse.ArgumentParser(description='Patching')
arg = parser.add_argument
arg('data', metavar='DIR', help='path to images')
arg('maskfolder', metavar='DIR', help='path to mask images')
arg('-pw', '--patch_width', default=224, type=int, help='width of the patch')
arg('--outputfolder', default='./patches', type=str, metavar='PATH', help='output folder')
arg('--noscale', default='false', type=str, help='keep the original intensity of patch')
arg('--convert2gray', default='false', type=str, help='convert to grayscale if set to true')
arg('-j', '--workers', default=0, type=int,  help='number of data loading workers (default: 0)')
arg('--log-file', default='deepPatch.log', type=str, help='the log file')


def image2patches(image, mask, pw, normalize = True, convert2gray = False):

    m,n,k = image.shape

    if convert2gray:
        image_gray = color.rgb2gray(image.copy())
        image = np.dstack((image_gray, image_gray, image_gray))


    # find the connected componets
    mask = (mask>127).astype("uint8")
    nlabels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask[...,0])

    patches =[]
    for i in range(1,nlabels):
        cy, cx = centroids[i]
        cx_start = int(max(0,cx-pw/2))
        cy_start = int(max(0,cy-pw/2))
        if (cx+pw/2)>m:
            cx_start = m-pw
        if (cy+pw/2)>n:
            cy_start = n-pw

        patch = image[cx_start:cx_start+pw,cy_start:cy_start+pw,:]
        if normalize and np.max(patch)>0:
            patch = exposure.rescale_intensity(patch)

            # histvals, histbins = exposure.histogram(patch)
            # if histbins[-1]==255:
            #     histvals = histvals[:-1]
            #     histbins = histbins[:-1]
            # total = np.sum(histvals)
            # cumsum = np.cumsum(histvals).astype(float)
            # inds = np.where(cumsum/total> 0.99)
            # satIntensity_2 = histbins[inds[0][0]]
            # if satIntensity_2>10:
            #     normalized_patch = patch.astype(float)/satIntensity_2
            #     normalized_patch[normalized_patch>1] = 1
            #     patch = img_as_ubyte(normalized_patch)

        #maskPatch = labels[cx_start:cx_start+pw,cy_start:cy_start+pw]
        #patch[maskPatch!=i]=0

        patches.append(img_as_ubyte(patch))
    return patches

def makeWritePatches(image_loader, maskfolder, imgs, outputfolder, noscale, convert2gray):

    if noscale=='true' or noscale=='True' :
        normalize=False
    else:
        normalize=True

    if convert2gray=='true' or convert2gray=='True':
        convert2gray = True
    else:
        convert2gray = False

    for batch_i, (tensorImage, target) in enumerate(image_loader):
        # batch size is set to 1, so only 1 image is in each iteration of image_loader
        # tensor to numpy:
        image = tensorImage.numpy()
        image = np.transpose(np.squeeze(image[0,:,:,:]),(1,2,0))

        # parse filename
        image_filename, label = imgs[batch_i]
        filepath, imfilename = os.path.split(image_filename)
        rootpath, classname = os.path.split(filepath)
        noextfn, ext = os.path.splitext(imfilename)

        # load the mask
        mask = cv2.imread(os.path.join(maskfolder, classname, noextfn+'.png'))
        #mask = cv2.imread(os.path.join(maskfolder, classname, imfilename))

        # make patches
        image_patches = image2patches(img_as_ubyte(image), mask, args.patch_width, normalize, convert2gray)

        # write patches
        for i, patch in enumerate(image_patches):
            newname = noextfn + "_%02d.png" %(i)
            outPath = os.path.join(outputfolder, classname)
            if not os.path.exists(outPath):
                os.makedirs(outPath)
            io.imsave(os.path.join(outPath, newname), patch)


def main(argsIn):
    global args
    args = parser.parse_args(argsIn)
    print("Optimized patching setup={}".format(args))
    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered patching')
    logging.info("Optimized patching setup={}".format(args))

    # set input dir
    inputdir = args.data

    # parse input dir
    input_dataset = folder.ImageFolder(inputdir, transform=transforms.ToTensor())

    # get the list
    imgs = input_dataset.imgs
    logging.info('num of files = {}'.format(len(imgs)))


    # get the list of classes
    classes = input_dataset.classes
    print("classes: ",classes)
    logging.info('classes = {}'.format(classes))

    # make the output dir
    if not os.path.exists(args.outputfolder):
        os.makedirs(args.outputfolder)

    # set the data loader
    image_loader = torch.utils.data.DataLoader(input_dataset, batch_size=1, shuffle=False, num_workers=args.workers, pin_memory=torch.cuda.is_available())

    print("=> creating patches and writing to disk")
    makeWritePatches(image_loader, args.maskfolder, imgs, args.outputfolder, args.noscale, args.convert2gray)


if __name__ == '__main__':
    main(sys.argv[1:])
