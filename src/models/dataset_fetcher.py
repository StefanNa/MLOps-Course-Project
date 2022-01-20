#!/usr/bin/env python3
######################################################################
# Authors:      <s202540> Rian Leevinson
#                     <s202385> David Parham
#                     <s193647> Stefan Nahstoll
#                     <s210246> Abhista Partal Balasubramaniam
#
# Course:        Machine Learning Operations
# Semester:    Spring 2022
# Institution:  Technical University of Denmark (DTU)
#
# Module: This module is responsible accessing our data
######################################################################

import os
from typing import Union

import torch
import torchvision.transforms as transforms
from omegaconf import OmegaConf
from torch.utils.data import DataLoader, Dataset

import kornia as K
import torchvision


class korniaGray2RGB(object):
    def __call__(self, img):

        return K.color.grayscale_to_rgb(img)


class korniaRGB2Gray(object):
    def __call__(self, img):

        return K.color.rgb_to_grayscale(img)


data_aug = torchvision.transforms.Compose(
    [
        korniaGray2RGB(),
        K.augmentation.RandomHorizontalFlip(p=0.2),
        K.augmentation.RandomVerticalFlip(p=0.2),
        K.augmentation.RandomSharpness(sharpness=0.5, p=0.2),
        K.augmentation.RandomGaussianNoise(mean=0.0, std=0.01, p=0.1),
        K.augmentation.RandomThinPlateSpline(scale=0.2, p=0.2),
        korniaRGB2Gray(),
    ]
)


# TODO: Write tests for this module
class Dataset_fetcher(Dataset):
    def __init__(
        self,
        PATH_IMG: str,
        PATH_LAB: str,
        transform: Union[transforms.transforms.Compose, None] = data_aug,
    ) -> None:

        self.images = torch.load(PATH_IMG)
        self.labels = torch.load(PATH_LAB).long()
        self.transform = transform

    def __getitem__(self, idx: int) -> Union[torch.tensor, str]:
        image = self.images[idx]
        label = self.labels[idx]

        if self.transform:
            image = self.transform(image)

        return image.view(-1, 512, 512), label

    def __len__(self) -> int:
        return len(self.images)


if __name__ == "__main__":

    BASE_DIR = os.getcwd()

    # Load config file
    config = OmegaConf.load(BASE_DIR + "/config/config.yaml")

    TRAIN_PATHS = {
        "images": BASE_DIR + config.TRAIN_PATHS.images,
        "labels": BASE_DIR + config.TRAIN_PATHS.labels,
    }

    dataset = Dataset_fetcher(TRAIN_PATHS["images"], TRAIN_PATHS["labels"])
    dataloader = DataLoader(dataset, shuffle=False, num_workers=4, batch_size=3)
    image, label = next(iter(dataloader))


def mean_and_std() -> None:
    """This function calculates the mean and standard deviation of the dataset"""

    ##Code is redundant from the above class. Needs to be fixed
    BASE_DIR = os.getcwd()
    config = OmegaConf.load(BASE_DIR + "/config/config.yaml")
    TRAIN_PATHS = {
        "images": BASE_DIR + config.TRAIN_PATHS.images,
        "labels": BASE_DIR + config.TRAIN_PATHS.labels,
    }

    dataset = Dataset_fetcher(TRAIN_PATHS["images"], TRAIN_PATHS["labels"])
    dataloader = DataLoader(dataset, shuffle=False, num_workers=4, batch_size=3)
    mean = 0.0
    std = 0.0
    nb_samples = 0.0

    for images, _ in dataloader:
        batch_samples = images.size(0)
        data = images.view(batch_samples, images.size(1), -1)
        mean += data.mean(2).sum(0)
        std += data.std(2).sum(0)
        nb_samples += batch_samples

    mean /= nb_samples
    std /= nb_samples
    print(mean, std)


mean_and_std()
