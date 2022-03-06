#!/usr/bin/python
import sys
import os
import numpy as np
from pathlib import Path
import cv2
import argparse
import logging

parser = argparse.ArgumentParser(description='Augmenting')
arg = parser.add_argument
arg('data', help='path to dataset')
arg('--outputfolder', default='.', type=str, help='outputfolder')
arg('--mode', default='classification', type=str, choices= ['classification', 'segmentation'], help='application mode, default = classification')
arg('--log-file', default='augment.log', type=str, help='the log file')



def main(argsIn):
    global args
    args = parser.parse_args(argsIn)
    print("Augmentation setup={}".format(args))
    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered data augmentation')
    logging.info("Augmentation setup={}".format(args))

    input_path = Path(args.data)
    output_path = Path(args.outputfolder)
    output_path.mkdir(exist_ok=True, parents=True)

    imgs = list(input_path.glob('*/*'))

    for file_name in imgs:
        img = cv2.imread(str(file_name))
        parts = file_name.parts
        output_class_path = output_path / parts[-2]
        output_class_path.mkdir(exist_ok=True, parents=True)
        cv2.imwrite(str(output_class_path / file_name.name), img)
        for i in range(0,3):
            img_rotated = np.rot90(img, i)
            filename = 'r'+str(i)+'_'+file_name.name
            cv2.imwrite(str(output_class_path / file_name.name), img_rotated)
        f_img = np.flipud(img)
        cv2.imwrite(str(output_class_path / ('f_'+ str(file_name.name))), f_img)
        for i in range(0,3):
            fimg_rotated = np.rot90(f_img, i)
            filename = 'rf'+str(i)+'_'+file_name.name
            cv2.imwrite(str(output_class_path / filename), fimg_rotated)

if __name__ == '__main__':
    main(sys.argv[1:])
