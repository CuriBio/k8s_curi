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
arg('--log-file', default='augment.log', type=str, help='the log file')

def get_mask_filename(path):
    mask_folder = 'LABEL'
    mask_path = path.parents[1] / mask_folder
    mask_file_name_list = list(mask_path.glob(str(path.name)[:-4]+ '.*'))
    if len(mask_file_name_list)>0:
        mask_file_name = str(mask_file_name_list[0])
        return mask_file_name
    else:
        print('mask file not found')
        return None


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

    imgs = list(input_path.glob('*.*'))
    logging.info("number of imgs={}".format(len(imgs)))

    for file_name in imgs:
        img = cv2.imread(str(file_name),1|2)
        if np.max(img)<=255:
            saveas16bit=False
        else:
            saveas16bit=True

        if saveas16bit:
            cv2.imwrite(str(output_path / file_name.name), img.astype(np.uint16))
        else:
            cv2.imwrite(str(output_path / file_name.name), img.astype(np.uint8))

        for i in range(0,3):
            img_rotated = np.rot90(img, i)
            filename = 'r'+str(i)+'_'+file_name.name
            if saveas16bit:
                cv2.imwrite(str(output_path / filename), img_rotated.astype(np.uint16))
            else:
                cv2.imwrite(str(output_path / filename), img_rotated.astype(np.uint8))

        f_img = np.flipud(img)
        if saveas16bit:
            cv2.imwrite(str(output_path / ('f_'+ str(file_name.name))), f_img.astype(np.uint16))
        else:
            cv2.imwrite(str(output_path / ('f_'+ str(file_name.name))), f_img.astype(np.uint8))

        for i in range(0,3):
            fimg_rotated = np.rot90(f_img, i)
            filename = 'rf'+str(i)+'_'+file_name.name
            if saveas16bit:
                cv2.imwrite(str(output_path / filename), fimg_rotated.astype(np.uint16))
            else:
                cv2.imwrite(str(output_path / filename), fimg_rotated.astype(np.uint8))

        if True:
            # do the same for the mask
            output_path_mask = Path(str(output_path).replace('IMG','LABEL'))
            output_path_mask.mkdir(exist_ok=True, parents=True)
            mask_path = get_mask_filename(file_name)
            mask_img = cv2.imread(mask_path)
            cv2.imwrite(str(output_path_mask / file_name.name), mask_img)
            for i in range(0,3):
                mask_img_rotated = np.rot90(mask_img, i)
                filename = 'r'+str(i)+'_'+file_name.name
                cv2.imwrite(str(output_path_mask / filename), mask_img_rotated)
            f_mask_img = np.flipud(mask_img)
            cv2.imwrite(str(output_path_mask / ('f_'+ str(file_name.name))), f_mask_img)
            for i in range(0,3):
                f_mask_img_rotated = np.rot90(f_mask_img, i)
                filename = 'rf'+str(i)+'_'+file_name.name
                cv2.imwrite(str(output_path_mask / filename), f_mask_img_rotated)


if __name__ == '__main__':
    main(sys.argv[1:])
