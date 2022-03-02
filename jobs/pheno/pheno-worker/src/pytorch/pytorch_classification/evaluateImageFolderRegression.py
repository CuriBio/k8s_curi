import argparse
import numpy as np
import os
import sys
import shutil
import time
import csv
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
import classifyImageFolder

model_names = sorted(name for name in models.__dict__
    if name.islower() and not name.startswith("__")
    and callable(models.__dict__[name]))

parser = argparse.ArgumentParser(description='Evaluation')
arg=parser.add_argument
arg('data', metavar='DIR', help='path to dataset')
arg('--arch', '-a', default='resnet50', choices=model_names, help='model architecture: ' +' | '.join(model_names) + ' (default: resnet50)')
arg('--mode', default='categorical', choices=['categorical', 'regression'])
arg('-c', '--precrop-size', default=224, type=int, help='pre crop image size (default: 224)')
arg('-pr', '--patch_rows', default=1, type=int, help='number of patches along rows (default: 1)')
arg('-pc', '--patch_cols', default=1, type=int, help='number of patches along columns (default: 1)')
arg('--maskfolder', default=None, type=str, help='path to mask folder for patching')
arg('-pw','--patch_width', default=224, type=int, help='patch width, applied only if maskfolder is set')
arg('--noscale', default='false', type=str, help='keep the original intensity of patch')
arg('--convert2gray', default='false', type=str, help='convert to grayscale if set to true')
arg('--checkpoint', default='', type=str,  help='path to latest checkpoint (default: none)')
arg('--workers', default=0, type=int, help='number of data loading workers (default: 0)')
arg('--outputfile', default='evaluate.csv', type=str, help='output file')
arg('--trainorval', default= 'Val', choices=['Train', 'Val'], help='Train or Val')
arg('--log-file', default='evaluate.log', type=str, help='the log file')
arg('--cpu', dest='cpu', action='store_true', help='use CPU only')

def main(argsIn):
    global args
    args = parser.parse_args(argsIn)
    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered evaluate')
    logging.info("evaluation setup={}".format(args))

    inputFolder = args.data
    OUTPUT_FN = args.outputfile
    classes, class_to_idx= folder.find_classes(inputFolder)
    logging.info("classes={}".format(classes))
    num_classes = len(classes)

    # calculate zscore or not
    CALC_Z_SCORE = False

    f = open(OUTPUT_FN, 'a', newline='')
    writer = csv.writer(f, delimiter=';')
    header = 'Filename, Train/Val, Class, Model Output'
    writer.writerow([header])

    logging.info("classifying images")
    ncorects = 0
    ntotal = 0
    for i, clas in enumerate(classes):
        # get all images in the class, absolute path
        subFolder = os.path.join(inputFolder, clas)
        if(len(os.listdir(subFolder))>0):
            if args.maskfolder is not None:
                classMaskFolder = os.path.join(str(args.maskfolder),clas)
                classifyPatchArgs = ['--patch_width', str(args.patch_width),'--maskfolder', classMaskFolder]
            else:
                classifyPatchArgs = ['--patches-rows', str(args.patch_rows),'--patches-cols', str(args.patch_cols)]

            # classify images
            classifyArgs = [subFolder,
                    '--arch', args.arch,
                    '--mode', args.mode,
                    '--checkpoint', args.checkpoint,
                    '--precrop-size', str(args.precrop_size),
                    '--noscale', str(args.noscale),
                    '--convert2gray', str(args.convert2gray),
                    '--num-classes', str(num_classes),
                    '--log-file', args.log_file]
            if args.cpu:
                classifyArgs.append('--cpu')

            classifyArgs = classifyArgs + classifyPatchArgs

            allprobs, imageNames, patchProbs, patchNames = classifyImageFolder.main(classifyArgs)

            # compare to class labels
            for k, probs in enumerate(allprobs):
                #print(k, prob)
                prob = np.sum(probs, axis=0)/probs.shape[0]
                probList = ["{:0.2f}".format(x) for x in prob]

                ntotal += 1
                # should be float(class) later
                if abs(prob - float(i)) <= 0.5:
                    ncorects += 1


                #print("Filename: {}, true label: {}, prediction: {}".format(imageNames[k], clas, classes[ind]),file=open(summaryfile, "a"))
                logging.info("Filename: {}, true label: {}, prediction: {}".format(imageNames[k], clas, probList[0]))

                # write to csv
                writer.writerow([ imageNames[k] + ',' + args.trainorval + ',' + clas + ',' + probList[0] ])

    f.close()

    zscore = None
    accuracy = 100*float(ncorects)/ntotal
    # # calculate and update final acccuracies
    # accuracy = 100*float(numTrainAcc)/float(numTrainTotal)
    accuracyStr = '{0:.1f}'.format(accuracy)
    logging.info("Accuracy: {}".format(accuracyStr))
    #
    # # per class accuracies
    per_class_accuracies = []
    for i, clas in enumerate(classes):
         class_accuracy = -1 #100*float(per_class_accuracy[i])/float(class_total[i])
         per_class_accuracies.append(class_accuracy)
    #     class_accuracy_Str = '{0:.1f}'.format(class_accuracy)
    #     print("class: {}, accuracy:{}".format(clas, class_accuracy_Str)) #,file=open(summaryfile, "a"))
    #     logging.info("class: {}, accuracy:{}".format(clas, class_accuracy_Str))

    return accuracy, zscore, per_class_accuracies

if __name__ == '__main__':
    main(sys.argv[1:])
