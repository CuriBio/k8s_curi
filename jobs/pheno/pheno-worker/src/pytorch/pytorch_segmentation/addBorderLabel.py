from pathlib import Path
import cv2
import numpy as np
import sys

if __name__ == '__main__':
    args = sys.argv
    # 1st input is the path where the binary masks are located (e.g. output of segmentation model)
    # 2nd input is the path for 3-class output masks
    indir = Path(args[1])
    outdir = Path(args[2])

    outdir.mkdir(exist_ok=True, parents=True)

    binary_label_imgs = list(indir.glob('*'))
    kernel = np.ones((7,7),np.uint8)
    for file_name in binary_label_imgs:
        print(str(file_name))
        img = cv2.imread(str(file_name))
        eroded_label = cv2.erode(img, kernel, iterations = 1)
        border = img - eroded_label

        new_label = img
        new_label[border>0]= 127
        cv2.imwrite(str(outdir / file_name.name), new_label)
