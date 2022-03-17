from base64 import decode
import os
from urllib import request
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
import main
from typing import *
from lib.models import *
from lib.utils import generate_presigned_get
from lib.utils import is_image_file
from lib.utils import format_name
from lib.utils import makePNG
from lib.utils import readCSV
from lib.utils import upload_file_to_s3
from lib.utils import copy_s3_file
from lib.utils import copy_s3_directory
import io
import json
from datetime import datetime
import tempfile
import zipfile
import uuid
import requests
import logging
from aiofile import async_open

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/train", tags=["trainings"])
MODEL_ARCHS = [
    "inception_v3",
    "resnet18",
    "resnet34",
    "resnet50",
    "resnet101",
    "resnet152",
    "vgg11",
    "vgg13",
    "vgg16",
    "vgg19",
    "vgg11_bn",
    "vgg13_bn",
    "vgg16_bn",
    "vgg19_bn",
    "squeezenet1_0",
    "squeezenet1_1",
    "densenet121",
    "densenet169",
    "densenet201",
    "densenet161",
]


@router.get(
    "/{selected_user_id}",
    description="request on initial trainings page render",
)
async def get_all_unfiltered_trainings(selected_user_id: int) -> List[Any]:
    try:
        async with main.db.pool.acquire() as cur:
            rows = await cur.fetch("SELECT * FROM trainings WHERE user_id=$1", selected_user_id)

            trainings = [dict(training) for training in rows]

            for training in trainings:
                key = f"trainings/{selected_user_id}/{training['study']}/{training['name']}/sample.jpg"
                url = generate_presigned_get(key=key, exp=5 * 60e3)
                training.update({"sample_url": url})

        return trainings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process request: {e}",
        )


@router.get(
    "/getFiltered/{selected_user_id}",
    description="Requests all trainings for user with filtered params",
)
async def get_all_filtered_trainings(selected_user_id: int) -> List[Filtered_training_model]:
    try:
        async with main.db.pool.acquire() as cur:

            rows = await cur.fetch(
                "SELECT * FROM trainings WHERE user_id=$1 AND status!='deleted' AND status!='none'",
                selected_user_id,
            )

        return [Filtered_training_model(**training).dict() for training in rows]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process request: {e}",
        )


@router.get(
    "/downloadLog/{id}",
    description="Downloads user-selected training log from s3 if error occurs during training",
)
async def get_training_log(id: int) -> str:
    try:
        async with main.db.pool.acquire() as cur:
            training = await cur.fetchrow("SELECT name, study, user_id FROM trainings WHERE id=$1", id)
            if not training:
                return None

            key = f"trainings/{training['user_id']}/{training['study']}/{training['name']}/{training['name']}.log"

        return generate_presigned_get(key=key, exp=5 * 60e3)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process request: {e}",
        )


@router.get(
    "/downloadResults/{id}",
    description="Downloads user-selected training output file from s3 once status is complete",
)
async def get_training_results(id: int) -> str:
    try:
        async with main.db.pool.acquire() as cur:

            training = await cur.fetchrow("SELECT name, study, user_id FROM trainings WHERE id=$1", id)

            if not training:
                return None

            key = f"trainings/{training['user_id']}/{training['study']}/{training['name']}/{training['name']}.log"

        return generate_presigned_get(key=key, exp=5 * 60e3)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process request: {e}",
        )


@router.get("/updateParam/{id}", description="Updates value in training table")
async def update_table_value(id: int, field: str, value: str) -> JSONResponse:
    try:
        async with main.db.pool.acquire() as cur:
            await cur.execute(f"UPDATE trainings SET {field}=$1 WHERE id=$2;", id, value)

        return JSONResponse(status_code=status.HTTP_200_OK)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process request: {e}",
        )


# new training-related


@router.get(
    "/newSetup/{user_id}",
    response_description="redirects to initial setup page",
    description="Called when user clicks 'Start New Training'. Route first queries db to check if user has reached account limit of successful (status!='deleted'/'none'/'error') trainings and then redirects to setup page.",
)
async def new_train_setup(user_id: int) -> Dict[str, Any]:
    try:
        async with main.db.pool.acquire() as cur:

            # get count of existing trainings for users
            num_of_trainings = await cur.fetchrow(
                "SELECT COUNT(*) FROM trainings WHERE user_id=$1 AND status!='deleted' AND status!='none'",
                user_id,
            )

            # get limit of trainings from tiered account privileges
            account = await cur.fetchrow("SELECT uploadlimit, type, email FROM users WHERE id=$1", user_id)

            # database saves unpaid users to 5, but original site requests limit of 2 non-error trainings
            # type is currently unused in db, only four people have 'admin' otherwise it's ''
            # could use type for user type to check limit
            if account["uploadlimit"] > num_of_trainings["count"] or account["type"] == "":
                response_dict = dict()

                # decide how to handle these user differences
                response_dict["segtrainings"] = await cur.fetch(
                    "SELECT * FROM segtrainings WHERE user_id=$1 AND status!='deleted' AND status!='none'",
                    user_id,
                )
                response_dict["show_focus_option"] = account["type"] in ["admin", "tenaya", "mo"]
                response_dict["select_focus_option"] = account["type"] in ["tenaya", "mo"]
                response_dict["smart_patching_option"] = account["type"] in ["admin", "fountain"]
                response_dict["type"] = account["type"]
                return response_dict
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User has reached account limit.",
                )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process request: {e}",
        )


@router.post(
    "/uploadNewTrainImages/{user_id}",
)
async def upload_new_train_images(
    user_id: int,
    class_name: str = "test_class",
    name: str = "train_name",
    val_data_source: str = "combined",
    val_or_train: str = "train",
    study_name: str = "study_name",
    files: List[UploadFile] = File(...),
) -> JSONResponse:

    try:
        # return if, for some reason no files to upload
        if len(files) == 0:
            return JSONResponse(status_code=status.HTTP_200_OK, content=f"No files to upload")

        with tempfile.TemporaryDirectory() as tmp_dir:
            for file in files:
                _, file_ext = os.path.splitext(file.filename)
                # extract or write files to temp directory
                if "zip" in file_ext:
                    with zipfile.ZipFile(io.BytesIO(file.file.read()), "r") as zip_ref:
                        zip_ref.extractall(tmp_dir)
                else:
                    out_path = os.path.join(tmp_dir, file.filename)
                    async with async_open(out_path, "wb") as out_file:
                        content = await file.read()  # async read
                        await out_file.write(content)  # async write

            # list files, and upload, protects against any other file structure in the zipfile
            for root, _, files in os.walk(tmp_dir):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    # if valid image
                    if "__MACOSX" not in file_path and await is_image_file(file_path):
                        if ".csv" in filename.lower():
                            try:
                                pathFileOut = file_path.replace("csv", "png").replace("CSV", "png")
                                signals = readCSV(file_path)
                                makePNG(signals, pathFileOut)
                                file_path = pathFileOut
                            except:
                                print("error csv to png")

                        relFileNoExt, file_ext = os.path.splitext(filename)
                        unique_name = relFileNoExt.replace("/", "_") + "_" + str(uuid.uuid4())[:8] + file_ext
                        if filename == "sample.jpg":  # upload sample image
                            sample_img_key = f"trainings/{user_id}/{study_name}/{name}/sample.jpg"
                            response = upload_file_to_s3(sample_img_key, file_path)
                        else:  # upload class images
                            key = (
                                f"trainings/{user_id}/{study_name}/{name}/{name}/{class_name}/{unique_name}"
                                if val_data_source == "combined"
                                else f"trainings/{user_id}/{study_name}/{name}/{name}/{val_or_train}/{class_name}/{unique_name}"
                            )

                            response = upload_file_to_s3(key, file_path)

            logger.info(f"Uploading {file}: {response}")
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": f"Successfully uploaded images for {name}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading training images to s3: {e}",
        )


@router.post(
    "/submitNewTraining/{user_id}",
    response_description="redirects to step 2/3 and passes certain params to next view",
    description="Step 1/3 when starting a new training. Route creates new training entry in db with user-inputted data then uploads to s3.",
)
async def new_train_submit(
    user_id: int,
    orig_name: str = Form(...),
    study_name: str = Form(...),
    patch_description: str = Form(...),
    smart_patch_seg_model: str = Form(...),
    smart_patch_channel: str = Form(...),
    patch_size: str = Form(...),
    image_size: str = Form(...),
    val_percent: int = Form(...),
    val_data_source: str = Form(...),
    remove_out_focus: str = Form(...),
    arch: str = Form(...),
    precrop_size: int = Form(...),
    epochs: int = Form(...),
    batch_size: int = Form(...),
    learn_rate: str = Form(...),
    momentum: str = Form(...),
    weight_decay: str = Form(...),
    checkpoint: str = Form(...),
    transfer: str = Form(...),
    augment: str = Form(...),
    preaugment: str = Form(...),
    stop_criteria: str = Form(...),
    no_scale: str = Form(...),
    convert2gray: str = Form(...),
    weighted_sampling: str = Form(...),
    mode: str = Form(...),
    regweight: str = Form(...),
    num_workers: str = Form(...),
) -> JSONResponse:  # try to set this up as a pydantic request model instead of each individual param

    try:
        async with main.db.pool.acquire() as cur:

            account = await cur.fetchrow(
                "SELECT uploadlimit, type FROM users WHERE id=$1", user_id
            )  # figure out diff user type requirements for future
            remove_out_focus = "no" if not remove_out_focus else remove_out_focus

            # remove spaces and special characters
            orig_name = format_name(orig_name)
            if study_name == "":
                study_name = "None"
            else:
                study_name = format_name(study_name)

            # set up name
            now = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            training_name = f"TR-{user_id}-{now}"

            # update review status on user type
            skip_review = (
                "yes"
                if account["type"]
                in ["admin", "mo", "tenaya", "fountain", "shadi", "juan", "charlene", "chronus"]
                else "no"
            )

            # insert new training data
            await cur.execute(
                "INSERT INTO trainings (name, study, origname, status, patches, smartpatchsegmodel, smartpatchchannel, patchsize, imagesize, user_id, valdatasource, valpercent, removeoutfocus, version, arch, precropsize, epochs, batchsize, learnrate, momentum, weightdecay, checkpoint, transfer, augment, preaugment, stopcriteria, noscale, convert2gray, weightedsampling, numworkers, mode, regweight, isreviewed) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33)",
                training_name,
                study_name,
                orig_name,
                "none",
                patch_description,
                smart_patch_seg_model,
                smart_patch_channel,
                patch_size,
                image_size,
                user_id,
                val_data_source,
                val_percent,
                remove_out_focus,
                "web",
                arch,
                precrop_size,
                min(epochs, 100),
                batch_size,
                learn_rate,
                momentum,
                weight_decay,
                checkpoint,
                transfer,
                augment,
                preaugment,
                stop_criteria,
                no_scale,
                convert2gray,
                weighted_sampling,
                num_workers,
                mode,
                regweight,
                skip_review,
            )

            # TODO update job queue with new entry

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error submitting {orig_name}: {e}"
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"message": f"successfully submitted {training_name}"}
    )


# re-training


@router.post(
    "/reSubmit/{id}",
    response_description="redirects to training view",
    description="Route creates new db entry and updates fields with new input values and prefixes name with 'Re-'. which uploads to s3 and updates status to 'queued'.",
)
async def retrain_submit(
    id: int,
    user_id: int,
    name: str = Form(...),
    whichuser: str = Form(...),
    orig_name: str = Form(...),
    patch_description: str = Form(...),
    smart_patch_seg_model: str = Form(...),
    smart_patch_channel: str = Form(...),
    patch_size: str = Form(...),
    val_percent: int = Form(...),
    val_data_source: int = Form(...),
    remove_out_focus: str = Form(...),
    arch: str = Form(...),
    precrop_size: int = Form(...),
    epochs: int = Form(...),
    batch_size: int = Form(...),
    learn_rate: str = Form(...),
    momentum: str = Form(...),
    weight_decay: str = Form(...),
    checkpoint: str = Form(...),
    transfer: str = Form(...),
    augment: str = Form(...),
    preaugment: str = Form(...),
    stop_criteria: str = Form(...),
    no_scale: str = Form(...),
    convert2gray: str = Form(...),
    weighted_sampling: str = Form(...),
    mode: str = Form(...),
    regweight: str = Form(...),
    num_workers: str = Form(...),
) -> JSONResponse:
    try:
        async with main.db.pool.acquire() as cur:

            # get original training entry
            training = await cur.fetchrow("SELECT * FROM trainings WHERE id=$1", id)

            # check for if user has special privileges to skip required review
            skip_review = (
                "yes"
                if whichuser in ["admin", "mo", "tenaya", "fountain", "shadi", "juan", "charlene", "chronus"]
                else "no"
            )

            # set up name
            now = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            retraining_name = f"RE-{user_id}-{now}"
            remove_out_focus = "no" if not remove_out_focus else remove_out_focus

            await cur.execute(
                "INSERT INTO trainings (name, origname, study, patches, retrain, smartpatchsegmodel, smartpatchchannel, patchsize, imagesize, classnames, imagesperclass, user_id, type, filternet, valdatasource, removeoutfocus, version, arch, precropsize, epochs, batchsize, learnrate, momentum, weightdecay, checkpoint, transfer, augment, preaugment, stopcriteria, noscale, convert2gray, weightedsampling, numworkers, mode, regweight, isreviewed) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35, $38)",
                retraining_name,
                user_id,
                orig_name,
                training["study"],
                patch_description,
                training["name"],
                smart_patch_seg_model,
                smart_patch_channel,
                patch_size,
                training["imagesize"],
                training["classnames"],
                training["imagesperclass"],
                training["filternet"],
                val_percent,
                val_data_source,
                remove_out_focus,
                "web",
                arch,
                precrop_size,
                min(epochs, 100),
                batch_size,
                learn_rate,
                momentum,
                weight_decay,
                checkpoint,
                transfer,
                augment,
                preaugment,
                stop_criteria,
                no_scale,
                convert2gray,
                weighted_sampling,
                num_workers,
                mode,
                regweight,
                skip_review,
            )

            # copy sample image over to new directory in s3
            source_key = f'trainings/{training["user_id"]}/{training["study"]}/{name}/sample.jpg'
            target_key = f'trainings/{user_id}/{training["study"]}/{retraining_name}/sample.jpg'
            copy_s3_file(source_key, target_key)

            # copy original images over to new dir in s3
            source_prefix = f'trainings/{user_id}/{training["study"]}/{name}/{name}/'
            target_prefix = f'trainings/{user_id}/{training["study"]}/{retraining_name}/{retraining_name}/'
            copy_s3_directory(source_prefix, target_prefix)

            # TODO update job queue with new entry

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting {retraining_name} for retraining: {e}",
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"successfully submitted {retraining_name} to be retrained"},
    )


@router.get(
    "/plotLog/{id}",
    response_model=Log_model,
    description="Called from details view on init every 10 seconds. Route queries db for training name and checks s3 if training exists. if it exists, copys data from file in  s3 and returns it.",
)
async def plot_log(id: int):
    try:
        # get training details for s3 key
        async with main.db.pool.acquire() as cur:
            training = await cur.fetchrow("SELECT * FROM trainings WHERE id=$1", id)

        # get training log from s3
        # key = "trainings/84/test_training/TR-84-2022-02-28-165358/TR-84-2022-02-28-165358_out/progress.txt"
        key = f'trainings/{training["user_id"]}/{training["study"]}/{training["name"]}/{training["name"]}_out/progress.txt'
        url = generate_presigned_get(key)
        if url:

            logfile = requests.get(url)
            decoded_file = logfile.content.decode("UTF-8")
            # split each line into list of training values
            file_lines = [line.split(",") for line in decoded_file.split("\n")]
            # setup dict to return
            response_dict = {
                "epochs": list(),
                "training_accuracy": list(),
                "training_loss": list(),
                "val_accuracy": list(),
                "val_loss": list(),
            }

            for line in file_lines:
                if len(line) > 1:
                    response_dict["epochs"].append(line[0])
                    response_dict["training_accuracy"].append(line[1])
                    response_dict["training_loss"].append(line[2])
                    response_dict["val_accuracy"].append(line[3])
                    response_dict["val_loss"].append(line[4])

            return Log_model(**response_dict).dict()
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": f"No logfile found for {training['name']}."},
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting log file for {training['name']}: {e}",
        )


# TODO check this route
@router.post(
    "/generatePatchExamples/{id}",
    description="Called from details view on init every 10 seconds. Route queries db for training name and checks s3 if training exists. if it exists, copys data from file in  s3 and returns it.",
)
def generate_patch_examples(id: int):
    return


# # scoring-related
# startBlindScore_desc = "Called when user clicks 'Launch' for training. Route queries db for training with ID and gets classnames. Route checks if object exists in s3 and if exists, counts number of val images. "


# @router.get(
#     "/startBlindScore/{id}",
#     tags=["train", "train3D"],
#     response_description="redirects to blindscore view with props updated with training, number of vals, classnames, userid and error if error.",
#     description=startBlindScore_desc,
# )
# def start_blind_score(id: int):
#     return None


# generateImages_desc = "Route called when user clicks 'start / restart' from the blindscore view. Route queries db for training and checks against various conditions in s3, generates presignedURLs for each val file in s3 and returns data dict."


# @router.post(
#     "/generateImagesToScore/{id}",
#     tags=["train", "train3D"],
#     description=generateImages_desc,
# )
# def generate_images_to_score(id: int, numImagesToScore: int):
#     return


# processBlindScoreResults_desc = "Called when a user selects any of the classes in the blindscore view. Route queries db for training, processes data, uploads output .csv file to s3, and returns data dict."


# @router.post(
#     "/processBlindScoreResults/{id}",
#     tags=["train", "train3D"],
#     description=processBlindScoreResults_desc,
# )
# def process_blind_score_results(id: int, scores: str, imageURLs: str, trueClasses: str):
#     return


# getScoreResults_desc = "Once a user processes the results, then they will be able to click 'Download Results'. Route gets output csv file from s3 and downloads it to local directory."


# @router.get(
#     "/getBlindScoreResults/{id}",
#     tags=["train", "train3D"],
#     response_description="returns Reponse() then downloads file.",
#     description=getScoreResults_desc,
# )
# def process_blind_score_results(id: int):
#     return
