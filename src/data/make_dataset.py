# -*- coding: utf-8 -*-
import argparse
import logging
import os
import sys
import zipfile
from distutils.command import config
from pathlib import Path

import kornia as K
import matplotlib.pyplot as plt
import numpy as np
import requests
import torch
import torchvision
from dotenv import find_dotenv, load_dotenv
from omegaconf import OmegaConf
from PIL import Image
from sklearn.model_selection import train_test_split
from torchvision import transforms
from tqdm import tqdm

config = OmegaConf.load("config/data.yaml")
url = config.URL


def download_extract(
    zip_file_url: str,
    PATH: str,
    filename: str = config.FILENAME,
    foldername: str = config.FOLDERNAME,
    chunk_size: int = config.CHUNK_SIZE,
) -> None:
    """
    Script to download dataset zip into raw folder
    zip_file_url : url to download file from
    PATH : path to download to
    filename : wanted filename for zip
    foldername : unzipped foldername
    inspired by: https://gist.github.com/nikhilkumarsingh/d29c1fdec0f4e266e53137d96b52e289
    """

    if PATH[-1] != "/":
        PATH.append("/")

    download = True
    extract = True
    if os.path.isfile(PATH + filename):
        download = False
    if os.path.isdir(PATH + foldername):
        extract = False

    if download:
        r = requests.get(zip_file_url, stream=True)
        total_size = int(r.headers["content-length"])
        with open(PATH + filename, "wb") as f:
            for data in tqdm(
                iterable=r.iter_content(chunk_size=chunk_size),
                total=total_size / chunk_size,
                unit="KB",
            ):
                f.write(data)
        print("Download complete!")
        del r

    if extract:
        z = zipfile.ZipFile(PATH + filename)
        z.extractall(PATH)
        del z


class check_size_and_gray(object):
    """Class to check the shape and size of the images"""

    def __init__(self, transform):
        self.transform = transform

    def __call__(self, img):
        shape = img.shape
        if shape[0] == 3:
            img = self.transform(img)
        elif shape[0] == 1:
            pass
        else:
            nonezero_layers = [i for i in range(shape[0]) if not (img[i] == img[i][0, 0]).all()]
            # assert len(nonezero_layers) ==3
            img = self.transform(img[nonezero_layers, :, :][:3])
        return img


def sizeof_fmt(num: float, suffix="B"):
    """by Fred Cirera,  https://stackoverflow.com/a/1094933/1870254, modified"""

    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, "Yi", suffix)


def sizetorch(value):
    """function to return size of objects"""

    try:
        return sys.getsizeof(value.storage())
    except:
        return sys.getsizeof(value)


def kornia_preprocess(pil_image: Image.Image) -> Image.Image:
    """This module performs preprocessing using Kornia and pytorch"""

    init_image = Image.open(pil_image)  # Opening PIL image
    image_tensor = transforms.ToTensor()(init_image).unsqueeze_(0)  # Transform PIL to Tensor
    resized_tensor = K.geometry.transform.resize(
        image_tensor, (512, 512), antialias=False
    )  # resizing using Kornia
    norm_image = K.enhance.normalize(
        resized_tensor, torch.Tensor([config.MEAN]), torch.Tensor([config.STD])
    )  # normalizing
    tensor_to_pil = transforms.ToPILImage()(norm_image.squeeze_(0))  # Transform Tensor to PIL

    return tensor_to_pil


def preprocess(
    path: str,
    plotsample: bool = config.PLOT_SAMPLE,
    output_filepath: str = config.OUTPUT_FILEPATH,
    maxperclass: int = config.MAX_PER_CLASS,
) -> None:
    """Performs preprocessing operations and transformations on the data"""

    classes = [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
    classes = np.sort(classes)
    class_map = {name: c for c, name in enumerate(classes)}
    img_paths = []
    labels = []
    for class_name in class_map:
        path_ = path + "/" + class_name
        files_names = [
            name for name in os.listdir(path_) if not os.path.isdir(os.path.join(path_, name))
        ]
        for count, file_name in enumerate(files_names):
            if count <= maxperclass:
                img_paths.append(path_ + "/" + file_name)
                labels.append(class_map[class_name])

        #     if len(labels)==200:
        #         break
        # if len(labels)==200:
        #     break

    all_images_gray512 = torch.empty([len(img_paths), 1, 512, 512])

    rgb_to_gray = torchvision.transforms.Compose(
        [
            torchvision.transforms.ToTensor(),
            # K.augmentation.RandomHorizontalFlip(p=0.5),
            # K.colour.rgb_to_grayscale
            check_size_and_gray(torchvision.transforms.Grayscale(num_output_channels=1))
            # ,torchvision.transforms.Normalize(0,1)
        ]
    )

    data_aug = torchvision.transforms.Compose(
        [
            K.augmentation.RandomHorizontalFlip(p=0.5),
            K.augmentation.RandomSharpness(p=0.5),
            K.augmentation.RandomGaussianNoise(p=0.2),
            K.augmentation.RandomThinPlateSpline(p=0.2),
        ]
    )

    for c, i in enumerate(tqdm(img_paths)):
        tensor_to_pil = kornia_preprocess(i)
        img_gray512 = rgb_to_gray(tensor_to_pil)
        test1 = K.color.grayscale_to_rgb(img_gray512)
        transf1 = data_aug(test1)
        tensor_to_pil = transforms.ToPILImage()(transf1.squeeze_(0))
        back1 = rgb_to_gray(tensor_to_pil)
        all_images_gray512[c, :, :, :] = back1

    if plotsample:
        figpath = config.FIG_PATH
        if not os.path.isdir(figpath):
            os.makedirs(figpath)
        for number in range(5):
            samples = all_images_gray512[np.random.randint(0, len(all_images_gray512), 25), :, :]
            grid_img = torchvision.utils.make_grid(samples, nrow=int(5))

            plt.figure()
            plt.imshow(grid_img.permute(1, 2, 0))
            plt.savefig(figpath + "/" + "sample" + str(number) + ".png")
            del samples

    validation_split = config.VALIDATION_SPLIT
    seed = config.SEED
    train_indices, test_indices, _, _ = train_test_split(
        range(len(all_images_gray512)),
        labels,
        stratify=labels,
        test_size=validation_split,
        random_state=seed,
    )

    len2test = int(len(test_indices) / 2)
    valid_indices = test_indices[len2test:]
    test_indices = test_indices[:len2test]

    train_images = all_images_gray512[train_indices].float().clone()
    test_images = all_images_gray512[test_indices].float().clone()
    valid_images = all_images_gray512[valid_indices].float().clone()

    train_labels = np.array(labels)[train_indices]
    test_labels = np.array(labels)[test_indices]
    valid_labels = np.array(labels)[valid_indices]

    for name, size in sorted(
        ((name, sizetorch(value)) for name, value in locals().items()), key=lambda x: -x[1]
    )[:10]:
        print("{:>30}: {:>8}".format(name, sizeof_fmt(size)))

    if not os.path.isdir(output_filepath):
        os.makedirs(output_filepath)

    print("break before")
    torch.save(train_images, output_filepath + "train_images.pt")
    del train_images
    print("break after train")
    torch.save(torch.from_numpy(train_labels), output_filepath + "train_labels.pt")
    del train_labels

    torch.save(test_images, output_filepath + "test_images.pt")
    del test_images
    torch.save(torch.from_numpy(test_labels), output_filepath + "test_labels.pt")
    del test_labels

    torch.save(valid_images, output_filepath + "valid_images.pt")
    del valid_images
    torch.save(torch.from_numpy(valid_labels), output_filepath + "valid_labels.pt")
    del valid_labels

    del all_images_gray512


def main():
    """Runs data processing scripts to turn raw data from (../raw) into
    cleaned data ready to be analyzed (saved in ../processed).
    """

    parser = argparse.ArgumentParser(description="Data downloading and unzipping arguments")
    parser.add_argument(
        "--url",
        type=str,
        default="https://data.mendeley.com/public-files/datasets/jctsfj2sfn/files/148dd4e7-636b-404b-8a3c-6938158bc2c0/file_downloaded",
        help="data URL to zip file",
    )
    parser.add_argument("--PATH", type=str, default="data/raw/", help="where to save zip")
    parser.add_argument(
        "--NAME",
        type=str,
        default="covid19-pneumonia-normal-chest-xraypa-dataset.zip",
        help="name of file to be extracted",
    )
    parser.add_argument(
        "--exdir",
        type=str,
        default="COVID19_Pneumonia_Normal_Chest_Xray_PA_Dataset",
        help="name of dir to be extracted",
    )
    parser.add_argument("--maxperclass", type=int, default=200, help="maximum imgs per class")
    parser.add_argument("-plotsample", action="store_true")
    args = parser.parse_args()
    zip_file_url = args.url
    PATH = args.PATH
    filename = args.NAME
    foldername = args.exdir
    maxperclass = args.maxperclass
    plotsample = config.PLOT_SAMPLE

    download_extract(zip_file_url, PATH, filename, foldername)
    path = config.RAW_DATA
    print("plotsample:", plotsample)
    preprocess(path, plotsample=plotsample, maxperclass=maxperclass)

    logger = logging.getLogger(__name__)

    logger.info("making final data set from raw data")


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    load_dotenv(find_dotenv())

    main()
