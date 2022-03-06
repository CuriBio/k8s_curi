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
arg('--orig_path', type=str, default='', help='path with original images')
arg('--acceptable_noise', type=int, default=50, help='acceptable number of pixels for images with no labeled object')
arg('--labels', type=str, default='0,1', help='For example 0,1,2 to list labels of interest')
arg('--sub_string', type=str, help='channel name to evaluate performance for')
arg('--log-file', default='evaluate.log', type=str, help='the log file')
arg('--outputfile', default='evaluate.csv', type=str, help='csv output file')

def jaccard(y_true, y_pred, acceptable_noise):

    if y_true.sum() == 0:
        if y_pred.sum() <= acceptable_noise:
            return 1

    epsilon = 1e-15
    intersection = (y_true * y_pred).sum()
    union = y_true.sum() + y_pred.sum() - intersection
    return ((intersection + epsilon) / (union  + epsilon))

def dice(y_true, y_pred, acceptable_noise):
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
    sub_string = args.sub_string # channel name
    outfile = args.outputfile

    result_dice_signal = []
    result_dice_diff = []
    imageNames =[]
    filenames = (Path(args.true_path)).glob('*')
    print("Filename, #orig, #gt, #pred, dice_signal, dice_noise", file=open(outfile, "a"))
    for file_name in filenames:
        if sub_string in str(file_name):

            y_true = (cv2.imread(str(file_name), 0) > 0).astype(np.uint8)
            pred_file_name = Path(args.pred_path) / file_name.name
            orig_file_name = Path(args.orig_path) / file_name.name
            x_true = (cv2.imread(str(orig_file_name), 0) > 0).astype(np.uint8)
            diff_true = x_true - y_true

            if len(labels) == 2 :
                y_pred = (cv2.imread(str(pred_file_name), 0) > 255 * 0.5).astype(np.uint8)
                diff_pred = x_true - y_pred
                dice_signal = dice(y_true, y_pred, acceptable_noise)
                dice_diff = dice(diff_true, diff_pred, acceptable_noise)
            else:
                y_pred = cv2.imread(str(pred_file_name), 0)
                diff_pred = x_true - y_pred
                dice_signal = general_dice(y_true, y_pred, labels)
                dice_diff = general_dice(diff_true, diff_pred, labels)

            print("{0},  {1}, {2}, {3}, {4:.2f}, {5:.2f}".format(file_name.name, x_true.sum(), y_true.sum(), y_pred.sum(), 100*dice_signal, 100*dice_diff))
            print("{0},  {1}, {2}, {3}, {4:.2f}, {5:.2f}".format(file_name.name, x_true.sum(), y_true.sum(), y_pred.sum(), 100*dice_signal, 100*dice_diff), file=open(outfile, "a"))
            result_dice_signal += [dice_signal]
            result_dice_diff += [dice_diff]
            imageNames.append(str(file_name))

    print('Dice Signal= {0:.2f}'.format(100*np.mean(result_dice_signal)))
    print('Dice Noise = {0:.2f}'.format(100*np.mean(result_dice_diff)))
    print("Ave Dice Signal," +sub_string+ ", ","{0:.2f}".format(100*np.mean(result_dice_signal)),file=open(outfile, "a"))
    print("Ave Dice Noise," +sub_string+ ", ","{0:.2f}".format(100*np.mean(result_dice_diff)),file=open(outfile, "a"))
    #return(imageNames, (np.mean(result_dice), np.std(result_dice)), (np.mean(result_jaccard), np.std(result_jaccard)), result_dice, result_jaccard)


if __name__ == '__main__':
    main(sys.argv[1:])
