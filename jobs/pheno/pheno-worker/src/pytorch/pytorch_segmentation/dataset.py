import torch
import numpy as np
import cv2
from torch.utils.data import Dataset

class SegmentationDataset(Dataset):
    def __init__(self, file_names: list, to_augment=False, transform=None, mode='train', labels=[0,255]):
        self.file_names = file_names
        self.to_augment = to_augment
        self.transform = transform
        self.mode = mode
        self.labels = labels

    def __len__(self):
        return len(self.file_names)

    def __getitem__(self, idx):
        img_file_name = self.file_names[idx]

        if self.mode == 'train':
            img = load_image(img_file_name)
            mask = load_mask(img_file_name, self.labels)
            if self.transform is not None:
                img, mask = self.transform(img, mask)

            if len(self.labels) == 2:
                return to_float_tensor(img), torch.from_numpy(np.expand_dims(mask, 0)).float()
            else:
                return to_float_tensor(img), torch.from_numpy(mask).long()

        elif self.mode == 'patch':
            img = load_image(img_file_name)
            mask = load_mask(img_file_name)
            return img, mask, str(img_file_name)

        elif self.mode == 'patch-predict':
            img = load_image(img_file_name)
            return img, str(img_file_name)

        else: # predict
            img = load_image(img_file_name)
            return to_float_tensor(img), str(img_file_name)


def to_float_tensor(img):
    return torch.from_numpy(np.moveaxis(img, -1, 0)).float()


def load_image(path):
    img = cv2.imread(str(path),1|2)
#    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img.astype('float32')


def load_mask(path, labels=None):
    mask_folder = 'LABEL'
    mask_path = path.parents[1] / mask_folder
    mask_file_name_list = list(mask_path.glob(str(path.name)[:-4]+ '.*'))
    if len(mask_file_name_list)>0:
        mask_file_name = str(mask_file_name_list[0])
        mask = cv2.imread(mask_file_name, 0)
        if labels is None:
            return mask.astype(np.uint8)
        if len(labels)>2:
            # map the labels to 0 to num_classes
            temp_mask = mask.copy()
            for i, label in enumerate(labels):
                temp_mask[mask==label]=i
            mask = temp_mask
            return mask.astype(np.uint8)
        else:
            return (mask/255).astype(np.uint8)
