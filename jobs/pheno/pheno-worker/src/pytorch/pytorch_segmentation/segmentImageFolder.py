"""
Script generates predictions, splitting original images into tiles, and assembling prediction back together
"""
import argparse
import sys
from .dataset import SegmentationDataset
import cv2
from .models import UNet16, LinkNet34, UNet11, UNet, AlbuNet34
import torch
from pathlib import Path
from tqdm import tqdm
import numpy as np
import logging
from .patchImageFolder import image2patches
import math
import os
import time

from torch.utils.data import DataLoader
from torchvision.transforms import ToTensor, Normalize, Compose

parser = argparse.ArgumentParser()
arg = parser.add_argument
arg("--data", metavar="DIR", help="path to dataset")
arg("--model_path", type=str, default="", help="path to model folder")
arg(
    "--model_type",
    type=str,
    default="UNet",
    help="network architecture",
    choices=["UNet", "UNet11", "UNet16", "LinkNet34", "AlbuNet"],
)
arg("--output_path", type=str, help="path to save images", default=".")
arg("--batch-size", type=int, default=4)
arg("--patch-size", default=512, type=int, help="patch size (default: 512)")
arg("--noscale", default="true", type=str, help="keep the original intensity of patch")
arg("--center-crop", type=int, default=-1)
arg("--labels", type=str, default="0,1", help="For example 0,1,2 to list labels of interest")
arg("--workers", type=int, default=0)
arg(
    "--output_mask_type",
    type=str,
    default="Overlay",
    choices=["Mask", "MaskedImage", "Overlay", "IonPath", "BoundingBox"],
)
arg("--channels", type=str, default="all", help="channel the given model has trained on")
arg("--log-file", default="segment.log", type=str, help="the log file")

IMG_EXTENSIONS = [
    ".jpg",
    ".JPG",
    ".jpeg",
    ".JPEG",
    ".png",
    ".PNG",
    ".ppm",
    ".PPM",
    ".bmp",
    ".BMP",
    ".tif",
    ".tiff",
    ".TIF",
    ".TIFF",
]


def is_image_file(filename):
    return any(filename.endswith(extension) for extension in IMG_EXTENSIONS)


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split("([0-9]+)", key)]
    return sorted(l, key=alphanum_key)


def mask_overlay(image, mask, alpha, labels, color=(0, 0, 1)):
    """
    Helper function to visualize mask on the top of the image
    """
    if len(labels) == 2:
        color = (0, 0, 1)
        mask = np.dstack((mask, mask, mask)) * np.array(color)
        mask = mask.astype(np.uint8)
        if np.max(image) > 256:
            image = image / 256
        weighted_sum = cv2.addWeighted(mask, alpha, image.astype(np.uint8), 1 - alpha, 0.0)
        img = image.copy()
        ind = mask[:, :, 2] > 128  # show mask for pixels of mask with intensity> 256/2
        img[ind] = weighted_sum[ind]
        return img
    else:
        image = image.astype(np.uint8)
        img = image.copy()
        for i, l in enumerate(labels[1:]):
            msk = mask.copy()
            msk = mask == l
            if i == 0:
                msk = np.dstack((msk, msk, msk)) * np.array((255, 0, 0))
                msk = msk.astype(np.uint8)
                weighted_sum = cv2.addWeighted(msk, alpha, image, 1 - alpha, 0.0)
                ind = msk[:, :, 0] > 0
            else:
                msk = np.dstack((msk, msk, msk)) * np.array((0, 0, 255))
                msk = msk.astype(np.uint8)
                weighted_sum = cv2.addWeighted(msk, alpha, image, 1 - alpha, 0.0)
                ind = msk[:, :, 2] > 0

            img[ind] = weighted_sum[ind]
        return img


def patches2image(patches, n, m, center_crop=-1):

    patch_size = patches[0].shape[0]
    mask = np.zeros((m, n))

    # re-calc patches rows and cols
    nb_rows = math.ceil(float(m) / float(patch_size))
    nb_cols = math.ceil(float(n) / float(patch_size))

    if len(patches) == 1 and center_crop > 0:
        st_h = int((m - center_crop) / 2.0)
        st_w = int((n - center_crop) / 2.0)
        mask[st_h : st_h + patch_size, st_w : st_w + patch_size] = patches[0]
        return mask

    # get the offsets
    if nb_cols == 1:
        cols_offset = 0
    else:
        cols_offset = math.ceil((float(patch_size) * float(nb_cols) - float(n)) / float(nb_cols - 1))

    if nb_rows == 1:
        rows_offset = 0
    else:
        rows_offset = math.ceil((float(patch_size) * float(nb_rows) - float(m)) / float(nb_rows - 1))

    co = int(cols_offset / 2)
    ro = int(rows_offset / 2)

    pInd = 0
    for i in range(0, nb_rows):
        for j in range(0, nb_cols):
            temp = patches[pInd]
            i1 = 0 if i == 0 else 1
            j1 = 0 if j == 0 else 1
            i2 = 0 if i == (nb_rows - 1) else 1
            j2 = 0 if j == (nb_cols - 1) else 1
            mask[
                -1 * i * rows_offset
                + i * patch_size
                + ro * i1 : -1 * i * rows_offset
                + (i + 1) * patch_size
                - ro * i2,
                -1 * j * cols_offset
                + j * patch_size
                + co * j1 : -1 * j * cols_offset
                + (j + 1) * patch_size
                - co * j2,
            ] = temp[ro * i1 : patch_size - ro * i2, co * j1 : patch_size - co * j2]
            pInd = pInd + 1

    return mask


def get_model(model_path, model_type="UNet16", num_classes=1):

    if model_type == "UNet16":
        model = UNet16(num_classes=num_classes)
    elif model_type == "UNet11":
        model = UNet11(num_classes=num_classes)
    elif model_type == "LinkNet34":
        model = LinkNet34(num_classes=num_classes)
    elif model_type == "AlbuNet":
        model = AlbuNet34(num_classes=num_classes)
    elif model_type == "UNet":
        model = UNet(num_classes=num_classes)

    if torch.cuda.is_available():
        state = torch.load(str(model_path))
    else:
        state = torch.load(str(model_path), map_location="cpu")
    state = {key.replace("module.", ""): value for key, value in state["model"].items()}
    model.load_state_dict(state)

    if torch.cuda.is_available():
        return model.cuda()

    model.eval()

    return model


def predict(model, from_file_names, ps, cc, to_path, normalize_patch, output_mask_type, labels, channels):

    from transforms import ImageOnly, Normalize, CenterCropImage, DualCompose

    loader = DataLoader(
        dataset=SegmentationDataset(from_file_names, transform=None, mode="patch-predict"),
        shuffle=False,
        batch_size=1,
        num_workers=args.workers,
        pin_memory=torch.cuda.is_available(),
    )

    if cc > 0:
        img_transform = DualCompose([ImageOnly(CenterCropImage((cc, cc))), ImageOnly(Normalize())])
    else:
        img_transform = ImageOnly(Normalize())
    for batch_num, (inputs, paths) in enumerate(tqdm(loader)):
        for i, image_name in enumerate(paths):
            img = inputs[i].data.numpy()
            if channels != "all" and len(img.shape) > 2:
                channel = int(channels)

                # account for RGB to BGR that happens in openCV
                if channel == 0:
                    channel = 2
                elif channel == 2:
                    channel = 0

                img_ch = img[..., channel]
                img = np.dstack((img_ch, img_ch, img_ch))

            img_patches = image2patches(img, ps, normalize_patch)
            # predict for each patch
            masks = []
            for p, apatch in enumerate(img_patches):
                # start = time.time()
                with torch.no_grad():
                    # apply the transform
                    new_patch, _mask = img_transform(np.copy(apatch))
                    # convert to tensor
                    new_patch = torch.from_numpy(np.moveaxis(new_patch, -1, 0)).float()
                    if torch.cuda.is_available():
                        new_patch = torch.unsqueeze(new_patch.cuda(), dim=0)
                    else:
                        new_patch = torch.unsqueeze(new_patch, dim=0)
                    mask_patch = model(new_patch)
                    if len(labels) == 2:
                        mask_array = (torch.sigmoid(mask_patch).data[0].cpu().numpy()[0] * 255).astype(
                            np.uint8
                        )
                    else:
                        out = (mask_patch[i].data.cpu().numpy().argmax(axis=0)).astype(np.uint8)
                        mask_mapped = np.zeros(out.shape)
                        for l, label in enumerate(labels):
                            mask_mapped[out == l] = label
                        mask_array = mask_mapped

                    masks.append(mask_array)
                # elapsed = time.time() - start
                # logging.info("Patch processing time: {}".format(elapsed))

            fullmask = patches2image(masks, img.shape[1], img.shape[0], cc)

            filepath, imfilename = os.path.split(image_name)
            noextfn, ext = os.path.splitext(imfilename)

            if output_mask_type == "IonPath":
                # write the mask
                logging.info(" {},max:,{}".format(imfilename, np.max(img)))
                cv2.imwrite(str(to_path / (noextfn + ".png")), fullmask)

                # write denoise image (0.5):
                denoised_image = img.copy()
                denoised_image[fullmask <= 128] = 0
                logging.info(" {},max:,{}".format(imfilename, np.max(denoised_image)))
                cv2.imwrite(str(to_path / (noextfn + "_0.5.png")), denoised_image.astype(np.uint16))

            elif output_mask_type == "Overlay":
                cv2.imwrite(str(to_path / (noextfn + ".png")), fullmask)
                overlay = mask_overlay(img, fullmask, 0.3, labels)
                cv2.imwrite(str(to_path / (noextfn + "_overlay.png")), overlay)

            elif output_mask_type == "BoundingBox":
                logging.info("{}".format(noextfn))
                m, n = fullmask.shape[0], fullmask.shape[1]
                # params
                border = 5
                toosmallarea = 225
                smallarea = 300

                # find the connected componets
                fullmask_binary = (fullmask > 127).astype("uint8")
                nlabels, cclabels, stats, centroids = cv2.connectedComponentsWithStats(fullmask_binary)
                for label in range(1, nlabels):
                    x = stats[label, cv2.CC_STAT_LEFT]
                    y = stats[label, cv2.CC_STAT_TOP]
                    w_x = stats[label, cv2.CC_STAT_WIDTH]
                    w_y = stats[label, cv2.CC_STAT_HEIGHT]
                    area = stats[label, cv2.CC_STAT_AREA]
                    logging.info("ROI,{},{},{},{},{},{}".format(label, x, y, w_x, w_y, area))
                    # filtering
                    if area < toosmallarea or w_x <= 15 or w_y <= 15:
                        continue
                    elif area < smallarea:
                        cv2.rectangle(img, (x, y), (x + w_x, y + w_y), (0, 0, 255), 2)
                    elif x <= border or x + w_x >= n - border or y <= border or y + w_y >= m - border:
                        cv2.rectangle(img, (x, y), (x + w_x, y + w_y), (255, 0, 0), 2)
                    else:
                        cv2.rectangle(img, (x, y), (x + w_x, y + w_y), (0, 255, 0), 2)

                cv2.imwrite(str(to_path / (noextfn + "_overlay.png")), img)
                cv2.imwrite(str(to_path / (noextfn + ".png")), fullmask)

            else:
                cv2.imwrite(str(to_path / (noextfn + ".png")), fullmask)


def main(argsIn):
    global args
    args = parser.parse_args(argsIn)

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    logging.basicConfig(filename=args.log_file, level=logging.INFO)
    logging.info("entered image segmentation")

    print("Image segmentation setup={}".format(args))
    logging.info("Image segmentation setup={}".format(args))

    testdir = Path(args.data).glob("**/*")
    file_names = [x for x in testdir if is_image_file(str(x)) and "__MACOSX" not in str(x)]

    logging.info("Numer of images = {}".format(len(file_names)))

    output_path = Path(args.output_path)
    output_path.mkdir(exist_ok=True, parents=True)

    labels = list(map(int, args.labels.split(",")))
    if len(labels) == 2:
        num_classes = 1
    else:
        num_classes = len(labels)  # includes background

    if args.noscale == "true" or args.noscale == "True":
        normalize_patch = False
    else:
        normalize_patch = True

    model = get_model(
        str(Path(args.model_path).joinpath("checkpoint_best.pth.tar")), args.model_type, num_classes
    )

    predict(
        model,
        file_names,
        args.patch_size,
        args.center_crop,
        output_path,
        normalize_patch,
        args.output_mask_type,
        labels,
        args.channels,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
