"""
Script generates predictions, splitting original images into tiles, and assembling prediction back together
"""
import argparse
import sys
from dataset import SegmentationDataset
import cv2
from models import UNet16, LinkNet34, UNet11, UNet, AlbuNet34
import torch
from pathlib import Path
from tqdm import tqdm
import numpy as np
import logging
import utils
from torch.utils.data import DataLoader
from transforms import (ImageOnly,
                        Normalize,
                        CenterCrop,
                        DualCompose)

parser = argparse.ArgumentParser()
arg = parser.add_argument
arg('--data', metavar='DIR',help='path to dataset')
arg('--model_path', type=str, default='', help='path to model folder')
arg('--model_type', type=str, default='UNet', help='network architecture',
    choices=['UNet', 'UNet11', 'UNet16', 'LinkNet34', 'AlbuNet'])
arg('--output_path', type=str, help='path to save images', default='.')
arg('--batch-size', type=int, default=4)
arg('--labels', type=str, default='0,1', help='For example 0,1,2 to list labels of interest')
arg('--workers', type=int, default=4)
arg('--log-file', default='temp.log', type=str, help='the log file')


def get_model(model_path, model_type='UNet16', num_classes=1):
    """
    :param model_path:
    :param model_type: 'UNet', 'UNet16', 'UNet11', 'LinkNet34', 'AlbuNet'
    """

    if model_type == 'UNet16':
        model = UNet16(num_classes=num_classes)
    elif model_type == 'UNet11':
        model = UNet11(num_classes=num_classes)
    elif model_type == 'LinkNet34':
        model = LinkNet34(num_classes=num_classes)
    elif model_type == 'AlbuNet':
        model = AlbuNet34(num_classes=num_classes)
    elif model_type == 'UNet':
        model = UNet(num_classes=num_classes)


    state = torch.load(str(model_path))
    state = {key.replace('module.', ''): value for key, value in state['model'].items()}
    model.load_state_dict(state)

    if torch.cuda.is_available():
        return model.cuda()

    model.eval()

    return model


def predict(model, from_file_names, batch_size, to_path, workers, labels):

    img_transform = DualCompose([
        ImageOnly(Normalize())
    ])

    loader = DataLoader(
        dataset=SegmentationDataset(from_file_names, transform=img_transform, mode='predict'),
        shuffle=False,
        batch_size=batch_size,
        num_workers=workers,
        pin_memory=torch.cuda.is_available()
    )

    with torch.no_grad():
        for batch_num, (inputs, paths) in enumerate(tqdm(loader, desc='Predict')):
            inputs = utils.cuda(inputs)
            outputs = model(inputs)
            for i, image_name in enumerate(paths):
                if len(labels) == 2:
                    mask = (torch.sigmoid(outputs[i, 0]).data.cpu().numpy() * 255).astype(np.uint8)
                else:
                    mask = (outputs[i].data.cpu().numpy().argmax(axis=0)).astype(np.uint8)
                # write binary mask
                #TODO map back to original labels
                cv2.imwrite(str(to_path / (Path(paths[i]).stem + '.png')), mask)


def main(argsIn):

    global args
    args = parser.parse_args(argsIn)

    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info('entered patch segmentation')

    print("Patch segmentation setup={}".format(args))
    logging.info("Patch segmentation setup={}".format(args))

    testdir = Path(args.data)
    file_names = list((testdir).glob('*'))

    logging.info('Numer of patches = {}'.format(len(file_names)))

    output_path = Path(args.output_path)
    output_path.mkdir(exist_ok=True, parents=True)

    labels = list(map(int, args.labels.split(',')))
    if len(labels) == 2:
        num_classes = 1
    else:
        num_classes = len(labels) # includes background

    model = get_model(str(Path(args.model_path).joinpath('checkpoint_best.pth.tar')), args.model_type, num_classes)
    predict(model, file_names, args.batch_size, output_path, args.workers, labels)


if __name__ == '__main__':
    main(sys.argv[1:])
