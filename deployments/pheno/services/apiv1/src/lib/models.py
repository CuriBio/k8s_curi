from typing import Any, List
from pydantic import BaseModel, EmailStr


class Usage_res_model(BaseModel):
    trainings: int
    experiments: int
    segmentations: int
    segtrainings: int
    total_processingtime: int


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
    message: str
    subject: str


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


class train_upload_model(BaseModel):
    orig_name: str
    study_name: str
    num_classes: int
    patch_description: str
    smart_patch_seg_model: str
    smart_patch_channel: str
    patch_size: str
    image_size: str
    sample_url: str
    val_percent: str
    val_data_source: str
    remove_out_focus: str


class Log_model(BaseModel):
    epochs: List[Any]
    training_accuracy: List[Any]
    training_loss: List[Any]
    val_accuracy: List[Any]
    val_loss: List[Any]
