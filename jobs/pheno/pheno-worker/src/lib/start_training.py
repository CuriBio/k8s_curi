import sys
import os
import math
import shutil
import numpy as np
from PIL import Image
import logging
import traceback
import csv
import shutil
import time
import tempfile
import sys

from botocore.exceptions import ClientError

from ..pytorch.pytorch_classification import train_new
from ..pytorch.pytorch_classification import patch
from ..pytorch.pytorch_classification import optimPatch
from ..pytorch.pytorch_classification import augment
from ..pytorch.pytorch_classification import classifyImageFolder
from ..pytorch.pytorch_classification import evaluateImageFolderRegression
from ..pytorch.pytorch_classification import evaluateImageFolder
from ..pytorch.pytorch_classification.folder import ImageFolder

from ..pytorch.pytorch_segmentation import segmentImageFolder

from .constants import TRAIN_CPU
from .constants import PHENO_BUCKET

from .utils import download_file_from_s3
from .utils import upload_directory_to_s3
from .utils import download_directory_from_s3
from .utils import email_user
from .utils import update_table_value

logger = logging.getLogger(__name__)

# ------------------------------------------ #
def start_training(training, LOG_FILENAME):
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
    startTime = time.time()
    TRAINING_TABLE = "trainings"

    # parse
    TRAIN_ID = training["id"]
    TRAIN_NAME = str(training["name"])
    FILTER_MODEL = training["filtermodel"]
    SM_SEG_MODEL = training["smartpatchsegmodel"]
    TRAIN_STUDY = str(training["study"])
    PATCH_DESCRIPTION = str(training["patches"])
    PATCH_SIZE = str(training["patchsize"])
    VAL_PERCENT = str(training["valpercent"])
    VAL_DATA_SOURCE = str(training["valdatasource"])
    ARCH = str(training["arch"])
    MODE = str(training["mode"])
    PRECROP_SIZE = str(training["precropsize"])
    EPOCHS = str(training["epochs"])
    BATCH_SIZE = str(training["batchsize"])
    LEARNING_RATE = str(training["learnrate"])
    MOMENTUM = str(training["momentum"])
    WEIGHT_DECAY = str(training["weightdecay"])
    CHECKPOINT = str(training["checkpoint"])
    TRANSFER = str(training["transfer"])
    AUGMENT = str(training["augment"])
    PREAUGMENT = str(training["preaugment"])
    STOP_CRITERIA = str(training["stopcriteria"])
    USER_ID = str(training["user_id"])
    REMOVE_OUT_FOCUS = str(training["removeoutfocus"])
    NOSCALE = str(training["noscale"])
    CONVERT2GRAY = str(training["convert2gray"])
    WEIGHTED_SAMPLING = str(training["weightedsampling"])
    WORKERS = str(training["numworkers"])
    REG_WEIGHT = str(training["regweight"])

    # setup directory structure
    tmp = tempfile.TemporaryDirectory()
    TMP_DIR = tmp.name
    INPUT_DIR = os.path.join(TMP_DIR, TRAIN_NAME)
    OUTPUT_DIR = os.path.join(TMP_DIR, TRAIN_NAME + "_out")
    OUTFOCUS_DIR = os.path.join(OUTPUT_DIR, "outfocus")
    VALID_DIR = os.path.join(OUTPUT_DIR, "valid")
    INVALID_DIR = os.path.join(OUTPUT_DIR, "invalid")
    OUTPUT_FN = os.path.join(OUTPUT_DIR, TRAIN_NAME + ".csv")
    OUTPUT_FN_FOCUS = os.path.join(OUTPUT_DIR, TRAIN_NAME + "_outfocus.csv")
    PATCHES_DIR = os.path.join(TMP_DIR, TRAIN_NAME + "_patches")
    MASKS_DIR = os.path.join(TMP_DIR, TRAIN_NAME + "_masks")
    CAM_DIR = os.path.join(TMP_DIR, TRAIN_NAME + "_cam")

    os.makedirs(INPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    os.makedirs(OUTFOCUS_DIR)
    os.makedirs(VALID_DIR)
    os.makedirs(INVALID_DIR)
    os.makedirs(PATCHES_DIR)
    os.makedirs(MASKS_DIR)
    os.makedirs(CAM_DIR)

    # log
    for key, value in training.items():
        logger.info(str(key) + " = " + str(value))

    # download data to input folder
    logger.info("transferring data")

    key = f"trainings/{USER_ID}/{TRAIN_STUDY}/{TRAIN_NAME}/{TRAIN_NAME}"
    download_directory_from_s3(PHENO_BUCKET, key, INPUT_DIR, logger)

    # get class names
    if VAL_DATA_SOURCE == "combined":
        tempData = ImageFolder(INPUT_DIR)
        classes = tempData.classes
    else:
        tempData = ImageFolder(os.path.join(INPUT_DIR, "Train"))
        classes = tempData.classes

    try:

        # detect and move out-of-focus images
        if REMOVE_OUT_FOCUS == "yes":
            CHECKPOINT_FOCUS = os.path.abspath("checkpoint_resnet50_focus.pth.tar")
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
                "--num-classes",
                str(2),
            ]
            logger.info("classifying images for focus detection")
            probs, imageNames, patchProbs, patchNames = classifyImageFolder.main(classifyArgs)

            # open file for writing
            f = open(OUTPUT_FN_FOCUS, "w", newline="")
            writer = csv.writer(f, delimiter=";")
            header = "Filename"
            writer.writerow([header])

            # move out-of-focus files to OUTPUT_DIR
            logger.info("moving out-of-focus files")
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
            logger.info("detected %d out of focus images" % nof)
            f.close()

        # if filter
        if FILTER_MODEL != "None":
            # get model params
            FILTER_MODEL_NAME = str(FILTER_MODEL["name"])
            FILTER_MODEL_USER_ID = str(FILTER_MODEL["user_id"])
            FILTER_MODEL_STUDY = str(FILTER_MODEL["study"])
            FILTER_MODEL_ARCH = str(FILTER_MODEL["arch"])
            FILTER_MODEL_PRECROP_SIZE = str(FILTER_MODEL["precropsize"])
            # FILTER_MODEL_PATCH_SIZE = str(FILTER_MODEL["patchsize"])
            FILTER_MODEL_NOSCALE = str(FILTER_MODEL["noscale"])
            FILTER_MODEL_CONVERT2GRAY = str(FILTER_MODEL["convert2gray"])
            FILTER_MODEL_CLASSES = str(FILTER_MODEL["classnames"]).split(",")

            try:
                filter_model_dir = os.makedirs(os.path.join(TMP_DIR, FILTER_MODEL_NAME))
                FILTER_CHECKPOINT = os.path.join(filter_model_dir, "model_best.pth.tar")
                key = f"trainings/{FILTER_MODEL_USER_ID}/{FILTER_MODEL_STUDY}/{FILTER_MODEL_NAME}_out/model_best.pth.tar"
                download_file_from_s3(PHENO_BUCKET, key, FILTER_CHECKPOINT)
            except ClientError as e:
                logger.error(f"Failed to upload: {e}")

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
                str(len(FILTER_MODEL_CLASSES)),
            ]

            if CPU == "True":
                classifyArgs.append("--cpu")
            logger.info("classifying images for valid / invalid detection")
            probs, imageNames, patchProbs, patchNames = classifyImageFolder.main(classifyArgs)

            # move invalid files, leave valid ones alone
            logger.info("moving invalid files")
            for k, prob in enumerate(probs):
                ind = prob.argmax()
                topclass = FILTER_MODEL_CLASSES[ind]
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

        # count number of files remaining
        numFiles = sum([len(files) for _, _, files in os.walk(INPUT_DIR)])
        if numFiles > 0:

            # split to train and val if uploaded together
            if VAL_DATA_SOURCE == "combined":
                logger.info("splitting to train and val")
                input_dataset = ImageFolder(INPUT_DIR)
                # classes = input_dataset.classes
                for i, clas in enumerate(classes):
                    # make folders
                    os.makedirs(os.path.join(INPUT_DIR, "Train", clas))
                    os.makedirs(os.path.join(INPUT_DIR, "Val", clas))
                    # get indices of images in that class
                    indices = []
                    for j, img in enumerate(input_dataset.imgs):
                        if str(i) == str(img[1]):
                            indices.append(j)
                    # split indices to train val
                    split = int(np.floor(float(VAL_PERCENT) / 100.0 * len(indices)))
                    split = max(1, split)
                    np.random.seed(0)
                    np.random.shuffle(indices)
                    train_idx, valid_idx = indices[split:], indices[:split]
                    # move files
                    for idx in train_idx:
                        image, _ = input_dataset.imgs[idx]
                        filepath, imfilename = os.path.split(image)
                        dst = os.path.join(INPUT_DIR, "Train", clas, imfilename)
                        shutil.move(image, dst)
                    for idx in valid_idx:
                        image, _ = input_dataset.imgs[idx]
                        filepath, imfilename = os.path.split(image)
                        dst = os.path.join(INPUT_DIR, "Val", clas, imfilename)
                        shutil.move(image, dst)

            # get width height
            tempPath = os.path.join(INPUT_DIR, "Train", classes[0])
            tempFile = os.path.join(tempPath, os.listdir(tempPath)[0])
            imTest = Image.open(tempFile)
            width, height = imTest.size
            update_table_value(TRAINING_TABLE, TRAIN_ID, "imagesize", str(width) + "x" + str(height), logger)

            # check workers
            if width > 5000 or height > 5000:
                logger.info("large images, setting workers to 0")
                WORKERS = 0
                update_table_value(TRAINING_TABLE, TRAIN_ID, "numworkers", 0, logger)

            # if smart patching
            if PATCH_DESCRIPTION == "smart":

                # make segmentation masks
                CHANNELS_2_SMART_PATCH = str(training["smartpatchchannel"])
                SEG_MODEL_NAME = str(SM_SEG_MODEL["name"])
                SEG_CHECKPOINT_PATH = os.path.join(TMP_DIR, "segmentation_checkpoints", SEG_MODEL_NAME)
                os.makedirs(SEG_CHECKPOINT_PATH)
                segpatches = str(SM_SEG_MODEL["patches"]).split("x")
                # segpatchw = segpatches[0]
                # segpatchh = segpatches[1]

                # download segmentation_checkpoint to s3
                try:
                    key = f"trainings/{USER_ID}/segmentation_checkpoints/{SEG_MODEL_NAME}/checkpoint_best.pth.tar"
                    seg_checkpoint_filepath = os.path.join(SEG_CHECKPOINT_PATH, "checkpoint_best.pth.tar")
                    download_file_from_s3(PHENO_BUCKET, key, seg_checkpoint_filepath)
                except ClientError as e:
                    logger.error(f"Failed to download {PHENO_BUCKET}/{key}: {e}")

                for TV in ["Train", "Val"]:
                    for clas in classes:

                        logger.info("making segmentation masks for " + TV + "," + clas)
                        inFolder = os.path.join(INPUT_DIR, TV, clas)
                        outFolder = os.path.join(MASKS_DIR, TV, clas)
                        os.makedirs(outFolder)

                        segmentArgs = [
                            "--data",
                            inFolder,
                            "--model_type",
                            str(SM_SEG_MODEL["arch"]),
                            "--model_path",
                            SEG_CHECKPOINT_PATH,
                            "--output_path",
                            outFolder,
                            "--batch-size",
                            str(SM_SEG_MODEL["batchsize"]),
                            "--patch-size",
                            str(SM_SEG_MODEL["patchsize"]),
                            "--center-crop",
                            str(SM_SEG_MODEL["centercrop"]),
                            "--noscale",
                            str(SM_SEG_MODEL["noscale"]),
                            "--output_mask_type",
                            "Mask",
                            "--workers",
                            str(SM_SEG_MODEL["numworkers"]),
                            "--labels",
                            str(SM_SEG_MODEL["labels"]),
                            "--channels",
                            str(CHANNELS_2_SMART_PATCH),
                            "--log-file",
                            LOG_FILENAME,
                        ]
                        segmentImageFolder.main(segmentArgs)

                # make patches
                logger.info("generating patches")
                os.makedirs(os.path.join(PATCHES_DIR, "Train"))
                os.makedirs(os.path.join(PATCHES_DIR, "Val"), exists_ok=True)
                optimPatch.main(
                    [
                        os.path.join(INPUT_DIR, "Train"),
                        os.path.join(MASKS_DIR, "Train"),
                        "--outputfolder",
                        os.path.join(PATCHES_DIR, "Train"),
                        "--patch_width",
                        str(PATCH_SIZE),
                        "--noscale",
                        NOSCALE,
                        "--convert2gray",
                        CONVERT2GRAY,
                        "--workers",
                        WORKERS,
                        "--log-file",
                        LOG_FILENAME,
                    ]
                )
                optimPatch.main(
                    [
                        os.path.join(INPUT_DIR, "Val"),
                        os.path.join(MASKS_DIR, "Val"),
                        "--outputfolder",
                        os.path.join(PATCHES_DIR, "Val"),
                        "--patch_width",
                        str(PATCH_SIZE),
                        "--noscale",
                        NOSCALE,
                        "--convert2gray",
                        CONVERT2GRAY,
                        "--workers",
                        WORKERS,
                        "--log-file",
                        LOG_FILENAME,
                    ]
                )

            # regular patching
            else:

                # calc patch size
                patches = PATCH_DESCRIPTION.split("x")
                patchw = patches[0]
                patchh = patches[1]
                sizew = float(width) / float(patchw)
                sizeh = float(height) / float(patchh)
                patchSize = math.floor(min(sizew, sizeh))
                update_table_value(TRAINING_TABLE, TRAIN_ID, "patchsize", patchSize, logger)

                # make patches
                logger.info("generating patches")
                os.makedirs(os.path.join(PATCHES_DIR, "Train"))
                os.makedirs(os.path.join(PATCHES_DIR, "Val"), exists_ok=True)
                patch.main(
                    [
                        os.path.join(INPUT_DIR, "Train"),
                        "--outputfolder",
                        os.path.join(PATCHES_DIR, "Train"),
                        "--patches-rows",
                        str(patchh),
                        "--patches-cols",
                        str(patchw),
                        "--noscale",
                        NOSCALE,
                        "--convert2gray",
                        CONVERT2GRAY,
                        "--log-file",
                        LOG_FILENAME,
                    ]
                )

                patch.main(
                    [
                        os.path.join(INPUT_DIR, "Val"),
                        "--outputfolder",
                        os.path.join(PATCHES_DIR, "Val"),
                        "--patches-rows",
                        str(patchh),
                        "--patches-cols",
                        str(patchw),
                        "--noscale",
                        NOSCALE,
                        "--convert2gray",
                        CONVERT2GRAY,
                        "--log-file",
                        LOG_FILENAME,
                    ]
                )

            # preaugmentation
            if PREAUGMENT == "True":
                logger.info("augmenting patches")
                augmentedpatches_dir = os.path.join(TMP_DIR, TRAIN_NAME + "_augmented_patches")
                os.makedirs(augmentedpatches_dir)
                os.makedirs(os.path.join(augmentedpatches_dir, "Train"))
                augment.main(
                    [
                        os.path.join(PATCHES_DIR, "Train"),
                        "--outputfolder",
                        os.path.join(augmentedpatches_dir, "Train"),
                        "--mode",
                        "classification",
                        "--log-file",
                        LOG_FILENAME,
                    ]
                )
                augment.main(
                    [
                        os.path.join(PATCHES_DIR, "Val"),
                        "--outputfolder",
                        os.path.join(augmentedpatches_dir, "Val"),
                        "--mode",
                        "classification",
                        "--log-file",
                        LOG_FILENAME,
                    ]
                )
            else:
                augmentedpatches_dir = PATCHES_DIR

            # location for progress file upload
            progressFileKey = f"trainings/{USER_ID}/{TRAIN_STUDY}/{TRAIN_NAME}/{TRAIN_NAME}_out/progress.txt"

            # train
            trainArgs = [
                augmentedpatches_dir,
                "--outputfolder",
                OUTPUT_DIR,
                "--arch",
                ARCH,
                "--mode",
                MODE,
                "--reg_weight",
                REG_WEIGHT,
                "--precrop-size",
                PRECROP_SIZE,
                "--epochs",
                EPOCHS,
                "--batch-size",
                BATCH_SIZE,
                "--learning-rate",
                LEARNING_RATE,
                "--momentum",
                MOMENTUM,
                "--weight-decay",
                WEIGHT_DECAY,
                "--stopping-criteria",
                STOP_CRITERIA,
                "--progress-upload-key",
                progressFileKey,
                "--log-file",
                LOG_FILENAME,
                "--workers",
                WORKERS,
            ]
            if CHECKPOINT != "None":  # TODO less certain about this change
                checkpoint_path = os.path.join(
                    TMP_DIR, "master_checkpoints", CHECKPOINT, " model_best.pth.tar"
                )
                os.makedirs(
                    checkpoint_path,
                    exist_ok=True,
                )
                key = f"trainings/master_checkpoints/{CHECKPOINT}/model_best.pth.tar"
                download_file_from_s3(PHENO_BUCKET, key, checkpoint_path)

                trainArgs.append("--checkpoint")
                trainArgs.append(checkpoint_path)
            if CPU == True:
                trainArgs.append("--cpu")
            if TRANSFER == "True":
                trainArgs.append("--transfer")
            if AUGMENT == "True":
                trainArgs.append("--augment")
            if WEIGHTED_SAMPLING == "True":
                trainArgs.append("--weighted_sampling")

            logger.info("training model")
            train_new.main(trainArgs)

            # # make copy of best model for classifications
            srcModel = os.path.join(OUTPUT_DIR, "model_best.pth.tar")
            if not os.path.isfile(srcModel):
                email_user(f"Training {TRAIN_NAME} completed with error")
                exit()

            # parse progress.txt -- get accuracy
            content = np.loadtxt(
                open(os.path.join(OUTPUT_DIR, "progress.txt"), "rb"), delimiter=",", skiprows=1
            )
            val_accuracy_col = content[:, 3]
            best_epoch_ind = np.argmax(val_accuracy_col)
            (best_epoch, train_accuracy, train_loss, val_accuracy, val_loss) = content[best_epoch_ind, 0:5]
            logger.info(
                "Best epoch: {0:f}, train accuracy: {1:.3f}, train loss: {2:.3f}, val accuracy: {3:.3f}, val loss: {4:.3f}".format(
                    best_epoch, train_accuracy, train_loss, val_accuracy, val_loss
                )
            )
            update_table_value(
                TRAINING_TABLE, TRAIN_ID, "trainpatchaccuracy", "{0:.1f}".format(train_accuracy), logger
            )
            update_table_value(
                TRAINING_TABLE, TRAIN_ID, "valpatchaccuracy", "{0:.1f}".format(val_accuracy), logger
            )

            # evaluate image folder
            for TV in ["Val", "Train"]:

                logger.info("evaluating " + TV)

                # evaluate on train and val
                if PATCH_DESCRIPTION == "smart":
                    trainMaskFolder = os.path.join(MASKS_DIR, TV)
                    evaluatePatchArgs = [
                        "--patch_width",
                        str(PATCH_SIZE),
                        "--maskfolder",
                        trainMaskFolder,
                    ]
                else:
                    evaluatePatchArgs = ["--patch_rows", str(patchh), "--patch_cols", str(patchw)]

                subFolder = os.path.join(INPUT_DIR, TV)
                evaluateArgs = [
                    subFolder,
                    "--arch",
                    ARCH,
                    "--mode",
                    MODE,
                    "--checkpoint",
                    srcModel,
                    "--precrop-size",
                    PRECROP_SIZE,
                    "--noscale",
                    NOSCALE,
                    "--convert2gray",
                    CONVERT2GRAY,
                    "--log-file",
                    LOG_FILENAME,
                    "--outputfile",
                    OUTPUT_FN,
                    "--trainorval",
                    TV,
                    "--workers",
                    WORKERS,
                ]
                evaluateArgs = evaluateArgs + evaluatePatchArgs
                if TV == "Val" and MODE == "categorical":
                    evaluateArgs.extend(["--camfolder", os.path.join(CAM_DIR, "Val")])
                if CPU == True:
                    evaluateArgs.append("--cpu")

                if MODE == "categorical":
                    accuracy, zscore, perClassAccuracy = evaluateImageFolder.main(evaluateArgs)
                else:
                    accuracy, zscore, perClassAccuracy = evaluateImageFolderRegression.main(evaluateArgs)

                classAccuraciesStr = ["{0:.1f}".format(a) for a in perClassAccuracy]

                if TV == "Train":
                    update_table_value(
                        TRAINING_TABLE,
                        TRAIN_ID,
                        "trainperclassaccuracies",
                        ",".join(classAccuraciesStr),
                        logger,
                    )
                    logger.info("Per class train accuracy: {}".format(",".join(classAccuraciesStr)))
                    update_table_value(
                        TRAINING_TABLE, TRAIN_ID, "trainimageaccuracy", "{0:.1f}".format(accuracy), logger
                    )
                    if len(classes) == 2 and zscore != None:
                        update_table_value(
                            TRAINING_TABLE, TRAIN_ID, "zscoretrain", "{0:.2f}".format(zscore), logger
                        )
                else:
                    update_table_value(
                        TRAINING_TABLE,
                        TRAIN_ID,
                        "valperclassaccuracies",
                        ",".join(classAccuraciesStr),
                        logger,
                    )
                    logger.info("Per class val accuracy: {}".format(",".join(classAccuraciesStr)))
                    update_table_value(
                        TRAINING_TABLE, TRAIN_ID, "valimageaccuracy", "{0:.1f}".format(accuracy), logger
                    )
                    if len(classes) == 2 and zscore != None:
                        update_table_value(
                            TRAINING_TABLE, TRAIN_ID, "zscoreval", "{0:.2f}".format(zscore), logger
                        )

            # done
            email_user("Training completed successfully")
            logger.info("done")

        # num files is 0
        else:
            email_user("Training completed, no valid files")
            logger.info("no valid files")

    except Exception as e:
        logger.info(traceback.format_exc())
        email_user("Training completed with error")

    # end time
    diffTime = str(int((time.time() - startTime) / 60.0))
    update_table_value(TRAINING_TABLE, TRAIN_ID, "processingtime", diffTime, logger)
    logger.info("Time in training: {} minutes".format(diffTime))

    # upload  output folder to s3
    key = f"trainings/{USER_ID}/{TRAIN_STUDY}/{TRAIN_NAME}/{TRAIN_NAME}_out"
    upload_directory_to_s3(PHENO_BUCKET, key, OUTPUT_DIR, logger)

    # upload patch validation data to s3
    PATCHES_DIR_VAL = os.path.join(PATCHES_DIR, "Val")
    key = f"trainings/{USER_ID}/{TRAIN_STUDY}/{TRAIN_NAME}/{TRAIN_NAME}_patches/Val"
    upload_directory_to_s3(PHENO_BUCKET, key, PATCHES_DIR_VAL, logger)

    # upload training masks to s3
    key = f"trainings/{USER_ID}/{TRAIN_STUDY}/{TRAIN_NAME}/{TRAIN_NAME}_masks"
    upload_directory_to_s3(PHENO_BUCKET, key, MASKS_DIR, logger)

    # upload cam data to s3
    key = f"trainings/{USER_ID}/{TRAIN_STUDY}/{TRAIN_NAME}/{TRAIN_NAME}_cam"
    upload_directory_to_s3(PHENO_BUCKET, key, CAM_DIR, logger)

    # clean up
    logger.info("Performing cleanup on temporary directories.")
    tmp.cleanup()
