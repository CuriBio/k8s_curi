from typing import Any, List
from pydantic import BaseModel, EmailStr
from fastapi import Form

class Usage_res_model(BaseModel):
    trainings: int
    experiments: int
    segmentations: int
    segtrainings: int
    total_processingtime: int

class New_train_response_model(BaseModel):
    segtrainings: List[Any]
    show_focus_option: bool
    select_focus_option: bool
    smart_patching_option: bool
    type: str

class Filtered_training_model(BaseModel):
    id: int
    trainpatchaccuracy: str
    valpatchaccuracy: str
    trainimageaccuracy: str
    valimageaccuracy: str
    zscoretrain: str
    zscoreval: str
    isreviewed: str


class Email_params_model(BaseModel):
    email: EmailStr
    message: str     subject: str


class Email_request_model(BaseModel):
    user_id: int
    message: str
    name: str


class image_upload_model(BaseModel):
    user_id = int
    name = str
    class_name = str
    val_data_source = str
    val_or_train = str


class Train_upload_model(BaseModel):
    name: str
    class_name: int
    study_name: str
    val_or_train: str
    val_data_source: str


class Log_model(BaseModel):
    epochs: List[Any]
    training_accuracy: List[Any]
    training_loss: List[Any]
    val_accuracy: List[Any]
    val_loss: List[Any]


class Generate_images_response_model(BaseModel):
    urls: List[str]
    num_imagess: int
    class_names: List[str]
    true_classes: List[str]


class Blindscore_request_model(BaseModel):
    image_urls: List[str]
    true_classes: List[str]
    class_names: List[str]
    scores: List[int]


class Blindscore_response_model(BaseModel):
    net_score: int
    net_score_per_class: List[int]
    num_images_per_class: List[int]
    total_images: int




def form_body(cls):
    cls.__signature__ = cls.__signature__.replace(
        parameters=[
            arg.replace(default=Form(...))
            for arg in cls.__signature__.parameters.values()
        ]
    )
    return cls


@form_body
class New_train_model(BaseModel):
    orig_name: str 
    study_name: str 
    patch_description: str 
    smart_patch_seg_model: str 
    smart_patch_channel: str 
    patch_size: str 
    image_size: str 
    val_percent: int 
    val_data_source: str 
    remove_out_focus: str 
    arch: str 
    precrop_size: int 
    epochs: int 
    batch_size: int 
    learn_rate: str 
    momentum: str 
    weight_decay: str 
    checkpoint: str 
    transfer: str 
    augment: str 
    preaugment: str 
    stop_criteria: str 
    no_scale: str 
    convert2gray: str 
    weighted_sampling: str 
    mode: str 
    regweight: str 
    num_workers: str 
