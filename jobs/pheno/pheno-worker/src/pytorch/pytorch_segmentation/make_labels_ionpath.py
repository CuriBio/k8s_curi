from pathlib import Path
import cv2
import numpy as np
import sys

if __name__ == '__main__':
    args = sys.argv
    indir = Path(args[1])
    outdir = Path(args[2])

    outdir.mkdir(exist_ok=True, parents=True)

    imgs = list(indir.glob('*'))

    for file_name in imgs:
        img = cv2.imread(str(file_name))
        label = 255*(img>0)
        label = label.astype(int)
        cv2.imwrite(str(outdir / file_name.name), label)
