from pathlib import Path
import argparse
import cv2
import numpy as np
from tqdm import tqdm
import sys
import logging

parser = argparse.ArgumentParser()
arg = parser.add_argument
arg('--true_path', type=str, default='',
    help='path where train images with ground truth are located')
arg('--pred_path', type=str, default='', help='path with predictions')
arg('--acceptable_noise', type=int, default=50, help='acceptable number of pixels for images with no labeled object')
arg('--labels', type=str, default='0,1', help='For example 0,1,2 to list labels of interest')
arg('--log-file', default='evaluate.log', type=str, help='the log file')

def jaccard(y_true, y_pred, acceptable_noise=5):

    if y_true.sum() == 0:
        if y_pred.sum() <= acceptable_noise:
            return 1

    epsilon = 1e-15
    intersection = (y_true * y_pred).sum()
    union = y_true.sum() + y_pred.sum() - intersection
    return ((intersection + epsilon) / (union  + epsilon))

def dice(y_true, y_pred, acceptable_noise=5):
    if y_true.sum() == 0:
        if y_pred.sum() <= acceptable_noise:
            return 1

    return (2 * (y_true * y_pred).sum() + 1e-15) / (y_true.sum() + y_pred.sum() + 1e-15)


def general_dice(y_true, y_pred, labels):
    result = []

    if y_true.sum() == 0:
        if y_pred.sum() == 0:
            return 1
        else:
            return 0

    for id in set(y_true.flatten()):	
        if id == 0:
            continue
        if id in labels:
            result += [dice(y_true == id, y_pred == id)]

    return np.mean(result)


def general_jaccard(y_true, y_pred, labels):
    result = []

    if y_true.sum() == 0:
        if y_pred.sum() == 0:
            return 1
        else:
            return 0

    for id in set(y_true.flatten()):
        if id == 0:
            continue
        if id in labels:
            result += [jaccard(y_true == id, y_pred == id)]

    return np.mean(result)


#-----------------------------------
def main(argsIn):
    args = parser.parse_args(argsIn)
    acceptable_noise = args.acceptable_noise
    labels = list(map(int, args.labels.split(',')))
    
    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered evaluation')

    print("Evaluation setup={}".format(args))
    logging.info("Evaluation setup={}".format(args))


    result_dice = []
    result_jaccard = []
    imageNames =[]
    filenames = (Path(args.true_path)).glob('*')
    for file_name in filenames:

        pred_file_name = Path(args.pred_path) / file_name.name

        if len(labels)==2:
            y_true = (cv2.imread(str(file_name), 0) > 0).astype(np.uint8)
            y_pred = (cv2.imread(str(pred_file_name), 0) > 255 * 0.5).astype(np.uint8)
            dice_measure = dice(y_true, y_pred, acceptable_noise)
            jaccard_measure = jaccard(y_true, y_pred, acceptable_noise)
        else:
            y_true = (cv2.imread(str(file_name), 0)).astype(np.uint8)
            y_pred = (cv2.imread(str(pred_file_name), 0)).astype(np.uint8)
            dice_measure = general_dice(y_true, y_pred, labels)
            jaccard_measure = general_jaccard(y_true, y_pred, labels)
        print("{0},  y_true={1}, y_pred={2}, dice={3:.2f}, jaccard={4:.2f}".format(file_name.name, y_true.sum(), y_pred.sum(), 100*dice_measure, 100*jaccard_measure))

        logging.info("{0},  y_true={1}, y_pred={2}, dice={3:.2f}, jaccard={4:.2f}".format(file_name.name, y_true.sum(), y_pred.sum(), 100*dice_measure, 100*jaccard_measure))
        result_dice += [dice_measure]
        result_jaccard += [jaccard_measure]
        imageNames.append(str(file_name))


    print('Dice = ', 100*np.mean(result_dice))
    print('Jaccard = ',100* np.mean(result_jaccard))
    return(imageNames, (np.mean(result_dice), np.std(result_dice)), (np.mean(result_jaccard), np.std(result_jaccard)), result_dice, result_jaccard)


if __name__ == '__main__':
    main(sys.argv[1:])
