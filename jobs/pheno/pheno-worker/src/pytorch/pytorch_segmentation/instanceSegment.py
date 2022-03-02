#!/usr/bin/python
import sys
import os
import numpy as np
from pathlib import Path
import cv2
import argparse
import logging

parser = argparse.ArgumentParser(description='Instance Segmentation')
arg = parser.add_argument
arg('data', help='path to dataset')
arg('--outputfolder', default='.', type=str, help='outputfolder')
arg('--log-file', default='instancesegment.log', type=str, help='the log file')


def main(argsIn):
    global args
    args = parser.parse_args(argsIn)
    print("Instance segmentation setup={}".format(args))
    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered instance segementation')
    logging.info("Segmentation setup={}".format(args))

    input_path = Path(args.data)
    output_path = Path(args.outputfolder)
    #output_path.mkdir(exist_ok=True, parents=True)

    imgs = list(input_path.glob('*.*'))
    logging.info("number of imgs={}".format(len(imgs)))

    for file_name in imgs:
        img = cv2.imread(str(file_name))
        img_copy = img.copy()
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

        # # sure background area
        # sure_bg = np.uint8(255*(gray<255))

        # Finding sure foreground area using distance transform
        cell_body = np.uint8(255*(gray==255))
        dist_transform = cv2.distanceTransform(cell_body,cv2.DIST_L2,5)
        #print(np.max(dist_transform))
        ret, sure_fg = cv2.threshold(dist_transform,0.90*dist_transform.max(),255,0)

        # Finding unknown region
        sure_fg = np.uint8(sure_fg)
        unknown = cv2.subtract(cell_body,sure_fg)

        # Marker labelling
        ret, markers = cv2.connectedComponents(sure_fg)

        # Add one to all labels so that sure background is not 0, but 1
        markers = markers+1

        # Mark the unknown region with zero
        markers[unknown==255] = 0
        markers = cv2.watershed(img, markers)
        img[markers == -1] = [127,127,127]
        cv2.imwrite(str(output_path / file_name.name), img.astype(np.uint8))



if __name__ == '__main__':
    main(sys.argv[1:])
