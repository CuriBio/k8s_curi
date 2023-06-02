import argparse
import os
import shutil
import time
from .folder import is_image_file
from .folder import default_loader
from .patch import image2patches
from skimage import io, img_as_ubyte, img_as_float
from PIL import Image
import numpy as np
import sys
import torch
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
import logging
import re
from .train_new import getModelForFineTune
from .optimPatch import image2patches as images_to_optimPatches
import cv2

model_names = sorted(
    name
    for name in models.__dict__
    if name.islower() and not name.startswith("__") and callable(models.__dict__[name])
)

parser = argparse.ArgumentParser(description="PyTorch Image Classification")
arg = parser.add_argument
arg("inputfolder", help="path to image folder")
arg("--arch", "-a", metavar="ARCH", default="resnet50", help="model architectures" + " (default: resnet50)")
arg("--mode", default="categorical", choices=["categorical", "regression"])
arg("--checkpoint", default="", type=str, metavar="PATH", help="path to latest checkpoint (default: none)")
arg("-c", "--precrop-size", default=224, type=int, help="pre crop image size (default: 224)")
arg("-pr", "--patches-rows", default=1, type=int, help="number of patches along rows (default: 1)")
arg("-pc", "--patches-cols", default=1, type=int, help="number of patches along columns (default: 1)")
arg("--maskfolder", default=None, type=str, help="path to mask folder for patching")
arg("-pw", "--patch_width", default=224, type=int, help="patch width, applied only if maskfolder is set")
arg("--noscale", default="false", type=str, help="keep the original intensity of patch")
arg("--convert2gray", default="false", type=str, help="convert to grayscale if set to true")
arg("--num-classes", default=2, type=int, help="number of classes")
arg("--cpu", dest="cpu", action="store_true", help="use CPU only")
arg("--log-file", default="classify.log", type=str, help="the log file")
arg("--camfolder", default=None, type=str, help="optional output folder for cam images (default: None)")
arg(
    "--classnames",
    default=None,
    type=str,
    help="optional comma-separated classnames, used for cam output (default: None)",
)

# ------------------------------------------ #
class SaveFeatures:
    features = None

    def __init__(self, m):
        self.hook = m.register_forward_hook(self.hook_fn)

    def hook_fn(self, module, input, output):
        self.features = ((output.cpu()).data).numpy()

    def remove(self):
        self.hook.remove()


def getCAM(feature_conv, weight_fc, class_idx):
    _, nc, h, w = feature_conv.shape
    cam = weight_fc[class_idx].dot(feature_conv.reshape((nc, h * w)))
    cam = cam.reshape(h, w)
    cam = cam - np.min(cam)
    cam_img = cam / np.max(cam)
    cam_img = np.uint8(255 * cam_img)
    return [cam_img]


# ------------------------------------------ #
def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split("([0-9]+)", key)]
    return sorted(l, key=alphanum_key)


# ------------------------------------------ #
def main(argsIn):
    global args, GPU
    args = parser.parse_args(argsIn)
    GPU = not args.cpu

    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info("entered classify main")
    logging.info("classification setup={}".format(args))

    if args.arch == "inception_v3":
        input_image_size = 299
    else:
        input_image_size = 224
    logging.info("image dimension ={}".format(input_image_size))

    if args.precrop_size < input_image_size:
        args.precrop_size = input_image_size

    if args.noscale == "true" or args.noscale == "True":
        normalize = False
    else:
        normalize = True

    if args.convert2gray == "true" or args.convert2gray == "True":
        convert2gray = True
    else:
        convert2gray = False

    preprocess = transforms.Compose(
        [
            transforms.Resize(args.precrop_size),
            transforms.CenterCrop(input_image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    num_classes = args.num_classes

    if GPU:
        torch.cuda.empty_cache()

    # create model
    if os.path.isfile(args.checkpoint):
        logging.info("=> loading the checkpoint '{}'".format(args.checkpoint))
        model = models.__dict__[args.arch](pretrained=True)

        if args.mode == "categorical":
            model = getModelForFineTune(model, args.arch, num_classes)
        else:  # regression
            model = getModelForFineTune(model, args.arch, 1)

        checkpoint = torch.load(args.checkpoint)
        model.load_state_dict(checkpoint["state_dict"])
        logging.info("=> loaded checkpoint '{}' (epoch {})".format(args.checkpoint, checkpoint["epoch"]))
        if GPU:
            model.cuda()

    else:
        logging.info("checkpoint path is invalid - exiting")
        exit()

    model.eval()

    # cam only for resnet models
    if args.camfolder is not None and "resnet" in args.arch and args.mode == "categorical":
        final_layer = model._modules.get("layer4")
        activated_features = SaveFeatures(final_layer)
        classnames = args.classnames.split(",")

    # parse the input folder
    input_folder = args.inputfolder
    imagefiles = []
    for root, dirs, files in os.walk(input_folder):
        for fileName in files:
            relDir = os.path.relpath(root, input_folder)
            relFile = os.path.join(relDir, fileName)
            if "__MACOSX" not in relFile and is_image_file(fileName):
                imagefiles.append(relFile)
    imagefiles = [filename.replace("./", "") for filename in imagefiles]

    # sort
    imagefiles = natural_sort(imagefiles)

    all_probs = []
    all_patch_probs = []
    all_patch_names = []

    with torch.no_grad():

        for i, image_fn in enumerate(imagefiles):
            # read raw image
            imgPath = os.path.join(input_folder, image_fn)
            img = default_loader(imgPath)
            noextfn, ext = os.path.splitext(image_fn)

            # make patches
            image_patches = []
            if args.maskfolder is None:
                image_patches = image2patches(
                    img_as_ubyte(np.asarray(img)),
                    args.patches_rows,
                    args.patches_cols,
                    normalize,
                    convert2gray,
                )
            else:
                # load the mask
                # mask = cv2.imread(os.path.join(args.maskfolder, image_fn))
                mask = cv2.imread(os.path.join(args.maskfolder, noextfn + ".png"))
                image_patches = images_to_optimPatches(
                    img_as_ubyte(np.asarray(img)), mask, args.patch_width, normalize, convert2gray
                )

            if len(image_patches) > 0:
                # process patches and convert to tensor
                if args.mode == "categorical":
                    probs = np.zeros((len(image_patches), num_classes))
                else:
                    probs = np.zeros((len(image_patches), 1))
                for p, apatch in enumerate(image_patches):

                    patch_tensor = preprocess(Image.fromarray(img_as_ubyte(apatch)))
                    patch_tensor.unsqueeze_(0)

                    # run prediction
                    if GPU:
                        output = model(patch_tensor.cuda())
                        if args.mode == "categorical":
                            smax = nn.Softmax().cuda()
                            smax_out = smax(output)
                            prob_patch = smax_out.data.cpu().numpy()
                        else:  # "regression"
                            prob_patch = output.data.cpu()
                    else:
                        output = model(patch_tensor)
                        if args.mode == "categorical":
                            smax = nn.Softmax()
                            smax_out = smax(output)
                            prob_patch = smax_out.data
                        else:
                            prob_patch = output.data

                    probs[p, :] = prob_patch

                    # make patch outputs
                    all_patch_probs.append(prob_patch[0])
                    noextfn, ext = os.path.splitext(image_fn)
                    patch_fn = noextfn + "_{:02d}.png".format(p)
                    all_patch_names.append(patch_fn)

                    # cam only for resnet models
                    if args.camfolder is not None and "resnet" in args.arch and args.mode == "categorical":
                        try:
                            if GPU:
                                pred_probabilities = smax_out.data.cpu().squeeze()
                            else:
                                pred_probabilities = smax_out.data.squeeze()
                            weight_softmax_params = list(model._modules.get("fc").parameters())
                            weight_softmax = np.squeeze(weight_softmax_params[0].cpu().data.numpy())
                            class_idx = torch.topk(pred_probabilities, 1)[1].int()
                            overlay = getCAM(activated_features.features, weight_softmax, class_idx)
                            height, width, _ = apatch.shape
                            heatmap = cv2.applyColorMap(
                                cv2.resize(overlay[0], (width, height)), cv2.COLORMAP_JET
                            )
                            result = heatmap * 0.3 + apatch * 0.5
                            predClass = classnames[class_idx.item()]
                            outFile = os.path.join(
                                args.camfolder,
                                noextfn + "_patch{:02d}_pred{pred}.png".format(p, pred=predClass),
                            )
                            cv2.imwrite(outFile, result)
                        except Exception as e:
                            logging.info(e)

            else:
                if args.mode == "categorical":
                    probs = (-1) * np.ones((1, num_classes))
                else:
                    probs = (-1) * np.ones((1, 1))

            # write to file
            # logging.info(probs)
            prob = np.sum(probs, axis=0) / probs.shape[0]
            probList = ["{:0.2f}".format(x) for x in prob]
            logging.info("Filename: {}, probs: {}".format(imgPath, ",".join(probList)))

            # store the img probs
            all_probs.append(probs)

    return (all_probs, imagefiles, all_patch_probs, all_patch_names)


if __name__ == "__main__":
    main(sys.argv[1:])
