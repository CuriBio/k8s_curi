"""
Script splitting original images into patches
"""
import argparse
import sys
import os
from dataset import SegmentationDataset
import cv2
import torch
from pathlib import Path
from tqdm import tqdm
import numpy as np
import utils
from torch.utils.data import DataLoader
import math
from skimage import measure, transform, img_as_ubyte, img_as_float, exposure
import logging

parser = argparse.ArgumentParser(description='Patching')
arg = parser.add_argument
arg('data', help='path to dataset')
arg('--workers', default=2, type=int, help='number of data loading workers (default: 4)')
arg('-ps', '--patch-size', default=128, type=int, help='patch size (default: 128)')
arg('--noscale', default='true', type=str, help='keep the original intensity of patch')
arg('--excludeNeg', default='true', type=str, help="exclude patches with all-zero labels")
arg('--outputfolder', default='.', type=str, help='outputfolder')
arg('--log-file', default='patch.log', type=str, help='the log file')


def patch(from_file_names, to_path, patch_size, normalize_patch, exclude):

    loader = DataLoader(
        dataset=SegmentationDataset(from_file_names, transform=None, mode='patch'),
        shuffle=False,
        batch_size=1,
        num_workers=args.workers,
        pin_memory=torch.cuda.is_available()
    )
    for batch_num, (inputs, labels, filenames) in enumerate(loader):
        img, label, img_filename = inputs[0].data.numpy(), labels[0].data.numpy(), filenames[0] # batch size of 1
        img_patches = image2patches(img, patch_size, normalize_patch)
        label_patches = image2patches(label, patch_size, False)

        #write to disk
        filepath, imfilename = os.path.split(img_filename)
        noextfn, ext = os.path.splitext(imfilename)

        for i,patch in enumerate(img_patches):
            if (np.max(label_patches[i])>0 or not(exclude)): # mask is not empty:
                # write
                newname = noextfn + "_%03d.png" %(i)
                if np.max(img_patches[i])<=255:
                    cv2.imwrite(str(to_path / 'IMG' / newname), (img_patches[i]).astype(np.uint8))
                else:
                    cv2.imwrite(str(to_path / 'IMG' / newname), (img_patches[i]).astype(np.uint16))

                #TODO check this for multi-class segmentation
                cv2.imwrite(str(to_path / 'LABEL' / newname), (label_patches[i]).astype(np.uint8))


def image2patches(image, patch_size, normalize = True):

    try:
        m,n,k = image.shape
    except:
        m,n = image.shape
        k = 0

    # re-calc patches rows and cols
    nb_rows = math.ceil(float(m) / float(patch_size))
    nb_cols = math.ceil(float(n) / float(patch_size))

    # recalculate the offsets
    if nb_cols == 1:
        cols_offset = 0
    else:
        cols_offset = math.ceil( (float(patch_size) *  float(nb_cols) - float(n) ) / float(nb_cols-1) )

    if nb_rows == 1:
        rows_offset = 0
    else:
        rows_offset = math.ceil( (float(patch_size) *  float(nb_rows) - float(m) ) / float(nb_rows-1) )

    patches =[]
    for i in range(0,nb_rows):
        for j in range(0,nb_cols):
            if k>0:
                patch = image[-1*i*rows_offset+i*patch_size:-1*i*rows_offset+(i+1)*patch_size, -1*j*cols_offset+ j*patch_size:-1*j*cols_offset+(j+1)*patch_size,:]
            else:
                patch = image[-1*i*rows_offset+i*patch_size:-1*i*rows_offset+(i+1)*patch_size, -1*j*cols_offset+ j*patch_size:-1*j*cols_offset+(j+1)*patch_size]
            if normalize:
                patch = exposure.rescale_intensity(patch.astype(np.uint8))
                #histvals, histbins = exposure.histogram(patch)
                #if histbins[-1]==255:
                #    histvals = histvals[:-1]
                #    histbins = histbins[:-1]
                #total = np.sum(histvals)
                #cumsum = np.cumsum(histvals).astype(float)
                #inds = np.where(cumsum/total> 0.99)
                #satIntensity_2 = histbins[inds[0][0]]
                #if satIntensity_2>10:
                #    normalized_patch = patch.astype(float)/satIntensity_2
                #    normalized_patch[normalized_patch>1] = 1
                #    patch = img_as_ubyte(normalized_patch)
            patches.append(patch)
    return patches


def main(argsIn):
    global args
    args = parser.parse_args(argsIn)
    print("Patching setup={}".format(args))
    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered patching')
    logging.info("Patching setup={}".format(args))

    if args.noscale=='true' or args.noscale=='True':
        normalize_patch = False
    else:
        normalize_patch = True

    if args.excludeNeg=='true' or args.excludeNeg=='True':
        exclude = True
    else:
        exclude = False

    indir = Path(args.data)
    file_names = list((indir).glob('*'))

    print('num of files = {}'.format(len(file_names)))
    logging.info('num of files = {}'.format(len(file_names)))

    output_path = Path(args.outputfolder)
    outimgpath = output_path / 'IMG'
    outlabelpath = output_path / 'LABEL'
    outimgpath.mkdir(exist_ok=True, parents=True)
    outlabelpath.mkdir(exist_ok=True, parents=True)


    patch(file_names, output_path, args.patch_size, normalize_patch, exclude)


if __name__ == '__main__':
    main(sys.argv[1:])
