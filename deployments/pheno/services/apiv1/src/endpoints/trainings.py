import os
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
import main
from models import *
from utils import generate_presigned_get
from utils import is_image_file
from utils import format_name
from utils import makePNG
from utils import readCSV
from utils import upload_file_to_s3
from utils import copy_s3_file
from utils import copy_s3_directory
import io
from datetime import datetime
import tempfile
import zipfile
import uuid
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
async def get_all_unfiltered_trainings(selected_user_id: int):
    rows = await main.db.fetch_all(
        query="SELECT * FROM trainings WHERE user_id=:id", values={"id": selected_user_id}
    )

    trainings = [dict(training) for training in rows]

    for training in trainings:
        key = f"trainings/{selected_user_id}/{training['study']}/{training['name']}/sample.jpg"
        url = generate_presigned_get(key=key, exp=5 * 60e3)
        training.update({"sample_url": url})

    return trainings


@router.get(
    "/getFiltered/{selected_user_id}",
    description="Requests all trainings for user with filtered params",
)
async def get_all_filtered_trainings(selected_user_id: int):
    rows = await main.db.fetch_all(
        query="SELECT * FROM trainings WHERE user_id=:id AND status!='deleted' AND status!='none'",
        values={"id": selected_user_id},
    )

    return [Filtered_training_model(**training).dict() for training in rows]


@router.get(
    "/downloadLog/{id}",
    description="Downloads user-selected training log from s3 if error occurs during training",
)
async def get_training_log(id: int):
    training = await main.db.fetch_one(
        query="SELECT name, study, user_id FROM trainings WHERE id=:id", values={"id": id}
    )

    if not training:
        return None

    key = f"trainings/{training['user_id']}/{training['study']}/{training['name']}/{training['name']}.log"
    return generate_presigned_get(key=key, exp=5 * 60e3)


@router.get(
    "/downloadResults/{id}",
    description="Downloads user-selected training output file from s3 once status is complete",
)
async def get_training_results(id: int):
    training = await main.db.fetch_one(
        query="SELECT name, study, user_id FROM trainings WHERE id=:id", values={"id": id}
    )

    if not training:
        return None

    key = f"trainings/{training['user_id']}/{training['study']}/{training['name']}/{training['name']}.log"
    return generate_presigned_get(key=key, exp=5 * 60e3)


@router.get("/updateParam/{id}", description="Updates value in training table")
async def update_table_value(id: int, field: str, value: str) -> JSONResponse:
    update_query = f"UPDATE trainings SET {field}=:value WHERE id=:id;"
    await main.db.execute(query=update_query, values={"id": id, "value": value})
    return JSONResponse(status_code=status.HTTP_200_OK)


# new training-related


@router.get(
    "/newSetup/{user_id}",
    response_description="redirects to initial setup page",
    description="Called when user clicks 'Start New Training'. Route first queries db to check if user has reached account limit of successful (status!='deleted'/'none'/'error') trainings and then redirects to setup page.",
)
async def new_train_setup(user_id: int):
    # get count of existing trainings for users
    num_of_trainings = await main.db.fetch_one(
        query="SELECT COUNT(*) FROM trainings WHERE user_id=:user_id AND status!='deleted' AND status!='none'",
        values={"user_id": user_id},
    )

    # get limit of trainings from tiered account privileges
    account = await main.db.fetch_one(
        query="SELECT uploadlimit, type, email FROM users WHERE id=:id", values={"id": user_id}
    )

    # database saves unpaid users to 5, but original site requests limit of 2 non-error trainings
    # type is currently unused in db, only four people have 'admin' otherwise it's ''
    # could use type for user type to check limit
    if account["uploadlimit"] > num_of_trainings["count"] or account["type"] == "":
        response_dict = dict()

        # decide how to handle these user differences
        response_dict["segtrainings"] = await main.db.fetch_all(
            query="SELECT * FROM segtrainings WHERE user_id=:user_id AND status!='deleted' AND status!='none'",
            values={"user_id": user_id},
        )
        response_dict["show_focus_option"] = account["type"] in ["admin", "tenaya", "mo"]
        response_dict["select_focus_option"] = account["type"] in ["tenaya", "mo"]
        response_dict["smart_patching_option"] = account["type"] in ["admin", "fountain"]
        response_dict["type"] = account["type"]

        return response_dict

    return "User has reached account limit."


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
):

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
                            print(sample_img_key)
                        else:  # upload class images
                            key = (
                                f"trainings/{user_id}/{study_name}/{name}/{name}/{class_name}/{unique_name}"
                                if val_data_source == "combined"
                                else f"trainings/{user_id}/{study_name}/{name}/{name}/{val_or_train}/{class_name}/{unique_name}"
                            )

                            response = upload_file_to_s3(key, file_path)

            logger.info(f"Uploading {file}: {response}")
        return JSONResponse(status_code=status.HTTP_200_OK, content=content={"message": f"Successfully uploaded images for Luci"})
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
):  # try to set this up as a pydantic request model instead of each individual param
    try:
        account = await main.db.fetch_one(
            query="SELECT uploadlimit, type FROM users WHERE id=:id", values={"id": user_id}
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
        await main.db.execute(
            query="""INSERT INTO trainings 
                (name, study, origname, status, patches, smartpatchsegmodel, smartpatchchannel, patchsize, imagesize, user_id, valdatasource, valpercent, removeoutfocus, version, arch, precropsize, epochs, batchsize, learnrate, momentum, weightdecay, checkpoint, transfer, augment, preaugment, stopcriteria, noscale, convert2gray, weightedsampling, numworkers, mode, regweight, isreviewed) 
                VALUES 
                (:name, :study, :origname, :status, :patches, :smartpatchsegmodel, :smartpatchchannel, :patchsize, :imagesize, :user_id, :valdatasource, :valpercent, :removeoutfocus, :version, :arch, :precropsize, :epochs, :batchsize, :learnrate, :momentum, :weightdecay, :checkpoint, :transfer, :augment, :preaugment, :stopcriteria, :noscale, :convert2gray, :weightedsampling, :numworkers, :mode, :regweight, :isreviewed)""",
            values={
                "name": training_name,
                "study": study_name,
                "origname": orig_name,
                "status": "none",
                "patches": patch_description,
                "smartpatchsegmodel": smart_patch_seg_model,
                "smartpatchchannel": smart_patch_channel,
                "patchsize": patch_size,
                "imagesize": image_size,
                "user_id": user_id,
                "valdatasource": val_data_source,
                "valpercent": val_percent,
                "removeoutfocus": remove_out_focus,
                "version": "web",
                "arch": arch,
                "precropsize": precrop_size,
                "epochs": min(epochs, 100),
                "batchsize": batch_size,
                "learnrate": learn_rate,
                "momentum": momentum,
                "weightdecay": weight_decay,
                "checkpoint": checkpoint,
                "transfer": transfer,
                "augment": augment,
                "preaugment": preaugment,
                "stopcriteria": stop_criteria,
                "noscale": no_scale,
                "convert2gray": convert2gray,
                "weightedsampling": weighted_sampling,
                "numworkers": num_workers,
                "mode": mode,
                "regweight": regweight,
                "isreviewed": skip_review,
            },
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
):
    try:
        # get original training entry
        training = await main.db.fetch_one(query="SELECT * FROM trainings WHERE id=:id", values={"id": id})

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

        await main.db.execute(
            query="""INSERT INTO trainings 
                    (name, origname, study, patches, retrain, smartpatchsegmodel, smartpatchchannel, patchsize, imagesize, classnames, imagesperclass, user_id, type, filternet, valdatasource, removeoutfocus, version, arch, precropsize, epochs, batchsize, learnrate, momentum, weightdecay, checkpoint, transfer, augment, preaugment, stopcriteria, noscale, convert2gray, weightedsampling, numworkers, mode, regweight, isreviewed) 
                    VALUES 
                    (:name, :origname, :study, :patches, :retrain, :smartpatchsegmodel, :smartpatchchannel, :patchsize, :imagesize, :classnames, :imagesperclass, :user_id, :type, :filternet, :valdatasource, :removeoutfocus, :version, :arch, :precropsize, :epochs, :batchsize, :learnrate, :momentum, :weightdecay, :checkpoint, :transfer, :augment, :preaugment, :stopcriteria, :noscale, :convert2gray, :weightedsampling, :numworkers, :mode, :regweight, :isreviewed)""",
            values={
                "name": retraining_name,
                "user_id": user_id,
                "origname": orig_name,
                "study": training["study"],
                "patches": patch_description,
                "retrain": training["name"],
                "smartpatchsegmodel": smart_patch_seg_model,
                "smartpatchchannel": smart_patch_channel,
                "patchsize": patch_size,
                "imagesize": training["imagesize"],
                "classnames": training["classnames"],
                "imagesperclass": training["imagesperclass"],
                "filternet": training["filternet"],
                "valpercent": val_percent,
                "valdatasource": val_data_source,
                "removeoutfocus": remove_out_focus,
                "version": "web",
                "arch": arch,
                "precropsize": precrop_size,
                "epochs": min(epochs, 100),
                "batchsize": batch_size,
                "learnrate": learn_rate,
                "momentum": momentum,
                "weightdecay": weight_decay,
                "checkpoint": checkpoint,
                "transfer": transfer,
                "augment": augment,
                "preaugment": preaugment,
                "stopcriteria": stop_criteria,
                "noscale": no_scale,
                "convert2gray": convert2gray,
                "weightedsampling": weighted_sampling,
                "numworkers": num_workers,
                "mode": mode,
                "regweight": regweight,
                "isreviewed": skip_review,
            },
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


@router.post("/viewTrainingDetails/{id}")
async def view_training_details(id: int):
    training = await main.db.fetch_one(query="SELECT * FROM users WHERE id=:id", values={"id": id})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Email has been sent"})


# # TODO check this route
# @router.get(
#     "/plotLog/{id}",
#     description="Called from details view on init every 10 seconds. Route queries db for training name and checks s3 if training exists. if it exists, copys data from file in  s3 and returns it.",
# )
# def plot_log(id: int):
#     return


# # TODO check this route
# @router.post(
#     "/generatePatchExamples/{id}",
#     description="Called from details view on init every 10 seconds. Route queries db for training name and checks s3 if training exists. if it exists, copys data from file in  s3 and returns it.",
# )
# def plot_log(id: int, class_names: list):
#     return


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
