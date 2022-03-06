#!/usr/bin/python
import sys
import os
import numpy as np
from pathlib import Path
import cv2
import argparse
import logging

parser = argparse.ArgumentParser(description='Resizing')
arg = parser.add_argument
arg('data', help='path to dataset')
arg('--outputfolder', default='.', type=str, help='outputfolder')
arg('--log-file', default='resize.log', type=str, help='the log file')


def main(argsIn):
    global args
    args = parser.parse_args(argsIn)
    print("Resizing setup={}".format(args))
    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered data resizing')
    logging.info("Resizing setup={}".format(args))

    input_path = Path(args.data)
    output_path = Path(args.outputfolder)
    output_path.mkdir(exist_ok=True, parents=True)

    imgs = list(input_path.glob('*.*'))
    logging.info("number of imgs={}".format(len(imgs)))

    for file_name in imgs:
        img = cv2.imread(str(file_name),1|2)
        if np.max(img)<=255:
            saveas16bit=False
        else:
            saveas16bit=True

        # Resize
        #print(img.shape)
        m,n,k = img.shape
        img = img[:,:,0]
        dim = (int(n*512.0/m), 512)
        img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
        print(img.shape)
        if saveas16bit:
            cv2.imwrite(str(output_path / file_name.name), img.astype(np.uint16))
        else:
            cv2.imwrite(str(output_path / file_name.name), img.astype(np.uint8))



if __name__ == '__main__':
    main(sys.argv[1:])
