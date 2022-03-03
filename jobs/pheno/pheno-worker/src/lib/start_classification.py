import sys
import os
import shutil
import numpy as np
import time
import tempfile
import re
import csv
import logging
import traceback

from .constants import TRAIN_CPU
from .constants import PHENO_BUCKET

from .utils import download_file_from_s3
from .utils import upload_directory_to_s3
from .utils import download_directory_from_s3
from .utils import email_user
from .utils import update_table_value


from pytorch.pytorch_classification import classifyImageFolder
from pytorch.pytorch_segmentation import segmentImageFolder

logger = logging.getLogger(__name__)

# ------------------------------------------ #
def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split("([0-9]+)", key)]
    return sorted(l, key=alphanum_key)


# ------------------------------------------ #


def start_classification(params, LOG_FILENAME):
    # config
    log_handlers = list()
    log_handlers.append(logging.FileHandler(LOG_FILENAME))
    log_handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s UTC] %(name)s-{%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
        handlers=log_handlers,
    )

    CPU = TRAIN_CPU
    CLASSIFICATION_TABLE = "experiments"

    # start time
    startTime = time.time()

    # get
    exp = params["exp"]
    training = params["training"]
    MAKE_SUM_CSV = params["makesumcsv"]
    MAKE_PATCH_CSV = params["makepatchcsv"]
    smartPatchSegModel = params["smartpatchsemodel"]
    filterModel = params["filtermodel"]

    # parse
    EXP_ID = str(exp["id"])
    EXP_NAME = str(exp["name"])
    USER_ID = str(exp["user_id"])
    REMOVE_OUT_FOCUS = str(exp["removeoutfocus"])
    MODEL_NAME = str(training["name"])
    MODEL_STUDY = str(training["study"])
    ARCH = str(training["arch"])
    MODE = str(training["mode"])
    PRECROP_SIZE = str(training["precropsize"])
    PATCH_DESCRIPTION = str(training["patches"])
    PATCH_SIZE = str(training["patchsize"])
    CLASS_NAMES = str(training["classnames"])
    MODEL_USER_ID = str(training["user_id"])
    NOSCALE = str(training["noscale"])
    CONVERT2GRAY = str(training["convert2gray"])

    # setup directory structure
    tmp = tempfile.TemporaryDirectory()
    TMP_DIR = tmp.name
    INPUT_DIR = os.path.join(TMP_DIR, EXP_NAME)
    OUTPUT_DIR = os.path.join(TMP_DIR, EXP_NAME + "_out")
    OUTFOCUS_DIR = os.path.join(OUTPUT_DIR, "outfocus")
    VALID_DIR = os.path.join(OUTPUT_DIR, "valid")
    INVALID_DIR = os.path.join(OUTPUT_DIR, "invalid")
    PATCHES_DIR = os.path.join(TMP_DIR, EXP_NAME + "_patches")
    MASKS_DIR = os.path.join(TMP_DIR, EXP_NAME + "_masks")
    CAM_DIR = os.path.join(TMP_DIR, EXP_NAME + "_cam")

    os.makedirs(INPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    os.makedirs(OUTFOCUS_DIR)
    os.makedirs(VALID_DIR)
    os.makedirs(INVALID_DIR)
    os.makedirs(PATCHES_DIR)
    os.makedirs(MASKS_DIR)
    os.makedirs(CAM_DIR)

    OUTPUT_FN = os.path.join(OUTPUT_DIR, EXP_NAME + ".csv")
    OUTPUT_FN_FOCUS = os.path.join(OUTPUT_DIR, EXP_NAME + "_outfocus.csv")
    OUTPUT_FN_PATCHES = os.path.join(OUTPUT_DIR, EXP_NAME + "_patches.csv")
    SUM_FN = os.path.join(OUTPUT_DIR, EXP_NAME + "_summary.csv")

    if MODE == "":
        MODE = "categorical"

    # download checkpoint if needed
    checkpoint_basepath = os.path.join(TMP_DIR, MODEL_NAME)
    os.makedirs(checkpoint_basepath)

    CHECKPOINT = os.path.join(checkpoint_basepath, "model_best.pth.tar")
    key = f"trainings/{MODEL_USER_ID}/{MODEL_STUDY}/{MODEL_NAME}/{MODEL_NAME}_out/model_best.pth.tar"
    download_file_from_s3(PHENO_BUCKET, key, CHECKPOINT, logger)

    # download input data
    key = f"classifications/{USER_ID}/{EXP_NAME}/{EXP_NAME}"
    download_directory_from_s3(PHENO_BUCKET, key, INPUT_DIR, logger)

    try:
        classes = CLASS_NAMES.split(",")
        # for tenaya
        if REMOVE_OUT_FOCUS == "yes":
            checkpoint_path = os.path.join(TMP_DIR, "master_checkpoints")
            os.makedirs(checkpoint_path)
            CHECKPOINT_FOCUS = os.path.join("checkpoint_resnet50_focus.pth.tar")

            key = "master_checkpoints/checkpoint_resnet50_focus.pth.tar"
            download_file_from_s3(PHENO_BUCKET, key, CHECKPOINT_FOCUS, logger)

            classifyArgs = [
                INPUT_DIR,
                "--arch",
                "resnet50",
                "--checkpoint",
                CHECKPOINT_FOCUS,
                "--precrop-size",
                str(224),
                "--patches-rows",
                str(1),
                "--patches-cols",
                str(1),
                "--noscale",
                "false",
                "--convert2gray",
                "false",
                "--num-classes",
                str(2),
            ]
            logging.info("classifying images for focus detection")
            probs, imageNames, patchProbs, patchNames = classifyImageFolder.main(classifyArgs)

            # open file for writing
            f = open(OUTPUT_FN_FOCUS, "w", newline="")
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Filename"])

            # move out-of-focus files to outputfolder
            logging.info("moving out-of-focus files")
            nof = 0
            for k, prob in enumerate(probs):
                ind = prob.argmax()
                if ind == 1:  # out of focus
                    # move the file
                    filepath, imfilename = os.path.split(imageNames[k])
                    src = os.path.join(INPUT_DIR, imageNames[k])
                    dst = os.path.join(OUTFOCUS_DIR, imfilename)
                    shutil.move(src, dst)
                    nof = nof + 1
                    # write to csv
                    writer.writerow([imageNames[k]])
            logging.info("detected %d out of focus images" % nof)
            f.close()

        # for chronus
        if filterModel != "None":
            # get model params
            FILTER_MODEL_NAME = str(filterModel["name"])
            FILTER_MODEL_USER_ID = str(filterModel["user_id"])
            FILTER_MODEL_STUDY = str(filterModel["study"])
            FILTER_MODEL_ARCH = str(filterModel["arch"])
            FILTER_MODEL_PRECROP_SIZE = str(filterModel["precropsize"])
            FILTER_MODEL_NOSCALE = str(filterModel["noscale"])
            FILTER_MODEL_CONVERT2GRAY = str(filterModel["convert2gray"])
            FILTER_MODEL_CLASS_NAMES = str(filterModel["classnames"])

            # download filter checkpoint from s3
            filter_basepath = os.path.join(TMP_DIR, FILTER_MODEL_NAME)
            os.makedirs(filter_basepath)
            FILTER_CHECKPOINT = os.path.join(filter_basepath, "model_best.pth.tar")

            key = f"trainings/{FILTER_MODEL_USER_ID}/{FILTER_MODEL_STUDY}/{FILTER_MODEL_NAME}/{FILTER_MODEL_NAME}_out/model_best.pth.tar"
            download_file_from_s3(PHENO_BUCKET, key, FILTER_CHECKPOINT, logger)

            classifyArgs = [
                INPUT_DIR,
                "--arch",
                FILTER_MODEL_ARCH,
                "--checkpoint",
                FILTER_CHECKPOINT,
                "--precrop-size",
                FILTER_MODEL_PRECROP_SIZE,
                "--patches-rows",
                str(1),
                "--patches-cols",
                str(1),
                "--noscale",
                FILTER_MODEL_NOSCALE,
                "--convert2gray",
                FILTER_MODEL_CONVERT2GRAY,
                "--num-classes",
                str(2),
            ]
            if CPU == True:
                classifyArgs.append("--cpu")
            logging.info("classifying images for valid / invalid detection")
            probs, imageNames, patchProbs, patchNames = classifyImageFolder.main(classifyArgs)

            # move invalid files, copy valid ones
            logging.info("moving invalid files")
            filterClasses = FILTER_MODEL_CLASS_NAMES.split(",")
            for k, prob in enumerate(probs):
                ind = prob.argmax()
                topclass = filterClasses[ind]
                filepath, imfilename = os.path.split(imageNames[k])
                src = os.path.join(INPUT_DIR, imageNames[k])
                if topclass != "valid":
                    dstFolder = os.path.join(INVALID_DIR, topclass)
                    dst = os.path.join(dstFolder, filepath.replace("/", "_") + "_" + imfilename)
                    if not os.path.exists(dstFolder):
                        os.makedirs(dstFolder)
                    shutil.move(src, dst)
                else:
                    dst = os.path.join(VALID_DIR, filepath.replace("/", "_") + "_" + imfilename)
                    shutil.copy(src, dst)

        # smart patch, for fountain
        if PATCH_DESCRIPTION == "smart":

            # make segmentation masks
            CHANNELS_2_SMART_PATCH = str(training["smartpatchchannel"])
            SEG_MODEL_NAME = str(smartPatchSegModel["name"])

            SEG_CHECKPOINT_PATH = os.makedirs(
                os.path.join(TMP_DIR, "segmentation_checkpoints", SEG_MODEL_NAME)
            )
            segpatches = str(smartPatchSegModel["patches"]).split("x")
            segpatchw = segpatches[0]
            segpatchh = segpatches[1]

            # download segmentation_checkpoint to s3
            key = f"trainings/{USER_ID}/segmentation_checkpoints/{SEG_MODEL_NAME}/checkpoint_best.pth.tar"
            seg_checkpoint_filepath = os.path.join(SEG_CHECKPOINT_PATH, "checkpoint_best.pth.tar")
            download_file_from_s3(PHENO_BUCKET, key, seg_checkpoint_filepath, logger)

            # pass sub-dirs separately
            for root, _, files in os.walk(INPUT_DIR):
                if len(files) > 0:
                    relDir = os.path.relpath(root, INPUT_DIR)
                    inFolder = os.path.join(INPUT_DIR, relDir)
                    outFolder = os.path.join(MASKS_DIR, relDir)
                    if not os.path.exists(outFolder):
                        os.makedirs(outFolder)

                    logging.info("making segmentation masks for " + relDir)
                    segmentArgs = [
                        "--data",
                        inFolder,
                        "--model_type",
                        str(smartPatchSegModel["arch"]),
                        "--model_path",
                        SEG_CHECKPOINT_PATH,
                        "--output_path",
                        outFolder,
                        "--batch-size",
                        "1",  # str(smartPatchSegModel['batchsize'])
                        "--patch-size",
                        str(smartPatchSegModel["patchsize"]),
                        "--center-crop",
                        str(smartPatchSegModel["centercrop"]),
                        "--noscale",
                        str(smartPatchSegModel["noscale"]),
                        "--output_mask_type",
                        "Mask",
                        "--workers",
                        "0",  # str(smartPatchSegModel['numworkers'])
                        "--labels",
                        str(smartPatchSegModel["labels"]),
                        "--channels",
                        str(CHANNELS_2_SMART_PATCH),
                        "--log-file",
                        LOG_FILENAME,
                    ]
                    segmentImageFolder.main(segmentArgs)

            classifyPatchArgs = ["--patch_width", str(PATCH_SIZE), "--maskfolder", MASKS_DIR]

        # default patching
        else:
            # get info
            patches = PATCH_DESCRIPTION.split("x")
            patchw = patches[0]
            patchh = patches[1]
            classifyPatchArgs = ["--patches-rows", str(patchh), "--patches-cols", str(patchw)]

        # classify
        classifyArgs = [
            INPUT_DIR,
            "--arch",
            ARCH,
            "--mode",
            MODE,
            "--checkpoint",
            CHECKPOINT,
            "--precrop-size",
            PRECROP_SIZE,
            "--noscale",
            NOSCALE,
            "--convert2gray",
            CONVERT2GRAY,
            "--num-classes",
            str(len(classes)),
        ]
        classifyArgs = classifyArgs + classifyPatchArgs
        if CPU == True:
            classifyArgs.append("--cpu")
        logging.info("classifying images")
        probs, imageNames, patchProbs, patchNames = classifyImageFolder.main(classifyArgs)

        # output file
        logging.info("writing output")
        if MODE == "categorical":
            f = open(OUTPUT_FN, "w", newline="")
            writer = csv.writer(f, delimiter=";")
            header = "Filename," + CLASS_NAMES
            writer.writerow([header])
            topClasses = np.zeros(len(classes))
            for k, prob in enumerate(probs):
                # format
                prob = np.sum(prob, axis=0) / prob.shape[0]
                probList = ["{:0.4f}".format(x) for x in prob]
                writer.writerow([imageNames[k] + "," + ",".join(probList)])
                # accumulate top class (for zip)
                ind = prob.argmax()
                topClasses[ind] = topClasses[ind] + 1
            f.close()
        else:  # regression
            f = open(OUTPUT_FN, "w", newline="")
            writer = csv.writer(f, delimiter=";")
            header = "Filename, Model Output"
            writer.writerow([header])
            topClasses = np.zeros(len(classes))
            for k, prob in enumerate(probs):
                # format
                prob = np.sum(prob, axis=0) / prob.shape[0]
                probList = ["{:0.4f}".format(x) for x in prob]
                writer.writerow([imageNames[k] + "," + probList[0]])
                # accumulate top class (for zip)
                ind = int(np.round(float(probList[0])))
                if ind >= 0 and ind < len(classes):
                    topClasses[ind] = topClasses[ind] + 1
            f.close()

        # update database
        if len(probs) == 0:
            update_table_value(CLASSIFICATION_TABLE, EXP_ID, "result", "none", logger)
        else:
            ind = topClasses.argmax()
            topClass = classes[ind]
            update_table_value(CLASSIFICATION_TABLE, EXP_ID, "result", topClass, logger)

        # output file for patches
        if MAKE_PATCH_CSV == "True" and MODE == "categorical":
            logging.info("writing output for patches")
            fp = open(OUTPUT_FN_PATCHES, "w", newline="")
            writer = csv.writer(fp, delimiter=";")
            header = "Filename," + CLASS_NAMES
            writer.writerow([header])
            for k, prob in enumerate(patchProbs):
                probList = ["{:0.4f}".format(x) for x in prob]
                writer.writerow([patchNames[k] + "," + ",".join(probList)])
            fp.close()

        # make summary csv
        if MAKE_SUM_CSV == "True" and MODE == "categorical":
            fs = open(SUM_FN, "w", newline="")
            writer = csv.writer(fs, delimiter=";")
            header = "Well," + CLASS_NAMES + ",standard errors"
            writer.writerow([header])
            # get unique well names
            wellNames = []
            for filename in imageNames:
                basename = os.path.basename(filename)
                parts = basename.split("_")
                well = parts[0]
                wellNames.append(well)
            wellNames = natural_sort(list(set(wellNames)))
            # go through wells and take average of probs
            for well in wellNames:
                wellProbs = np.empty((0, len(classes)))
                for k, prob in enumerate(probs):
                    if well + "_" in imageNames[k]:
                        prob = np.sum(prob, axis=0) / prob.shape[0]
                        wellProbs = np.append(wellProbs, [prob], axis=0)
                avgWellProbs = np.average(wellProbs, axis=0)
                seWellProbs = np.std(wellProbs, axis=0, ddof=1)
                seWellProbs = np.divide(seWellProbs, 2 * np.sqrt(wellProbs.shape[0]))
                avgWellProbs = ["{:0.4f}".format(x) for x in avgWellProbs]
                seWellProbs = ["{:0.4f}".format(x) for x in seWellProbs]
                writer.writerow([well + "," + ",".join(avgWellProbs) + "," + ",".join(seWellProbs)])
            fs.close()

        # done
        email_user("Classification complete")

    except Exception as e:
        logging.info(traceback.format_exc())
        email_user("Classification completed with error")

    # end time
    diffTime = str(int((time.time() - startTime) / 60.0))
    update_table_value(CLASSIFICATION_TABLE, EXP_ID, "processingtime", diffTime, logger)
    logging.info("Processing time: {} minutes".format(diffTime))

    # upload  output folder to s3
    key = f"classifications/{USER_ID}/{EXP_NAME}/{EXP_NAME}_out"
    upload_directory_to_s3(PHENO_BUCKET, key, OUTPUT_DIR, logger)

    # clean up
    logger.info("Performing cleanup on temporary directories.")
    tmp.cleanup()
