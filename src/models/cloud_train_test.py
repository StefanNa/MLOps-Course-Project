import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import torch
from google.cloud import storage

"""
JOB_NAME=test_job6
gcloud ai-platform jobs submit training ${JOB_NAME} \
  --region=europe-west1 \
  --master-image-uri=gcr.io/charged-city-337910/project:latest \
  --config=config/gcloud_ai_config.yaml
"""

"""
JOB_NAME=train6
gcloud ai-platform jobs submit training ${JOB_NAME} \
  --region=europe-west1 \
  --master-image-uri=gcr.io/charged-city-337910/train:latest \
  --config=config/gcloud_ai_config.yaml
"""

"""
docker build --build-arg WANDB_TOKEN='77fd84d04670fb6689468a55cc459483104ce350' -t project:0.2 -f train.Dockerfile .
"""


def run() -> None:
    parser = argparse.ArgumentParser(description="model running arguments")
    parser.add_argument(
        "-e",
        "--num-epochs",
        type=int,
        default=5,
        help="number of epochs",
    )

    parser.add_argument(
        "-lr",
        "--learning-rate",
        type=float,
        default=0.01,
        help="learning rate",
    )

    parser.add_argument(
        "-img",
        "--image-file",
        type=str,
        default="data/preprocessed/covid_not_norm/train_images.pt",
        help="location of train tensor",
    )

    parser.add_argument(
        "-lab",
        "--label-file",
        type=str,
        default="data/preprocessed/covid_not_norm/train_labels.pt",
        help="location of train tensor",
    )

    parser.add_argument(
        "-bs",
        "--batch-size",
        type=str,
        default="data/preprocessed/covid_not_norm",
        help="location of train tensor",
    )

    parser.add_argument(
        "--bucket-name",
        type=str,
        default="mlops_dtu_covid_project",
        help="name of gs bucket",
    )

    args = parser.parse_args()

    bucket_name = args.bucket_name

    figname = "reports/figures/example.png"
    if not os.path.isdir("/".join([i for i in figname.split("/")[:-1]])):
        os.makedirs("/".join([i for i in figname.split("/")[:-1]]))
    x, y = np.random.randint(0, 100, 20), np.random.randint(0, 1000, 20)

    imgs = torch.load(args.image_file)
    labels = torch.load(args.label_file)
    randimg = np.random.randint(0, len(labels))
    randlabel = str(labels[randimg].numpy())
    print(imgs[randimg, 0, :, :].shape)
    plt.figure()
    plt.imshow(imgs[randimg, 0, :, :], cmap="gray")
    plt.title("class " + randlabel)
    # plt.show()
    plt.savefig(figname)
    print(os.getcwd())

    source_file_name = figname
    destination_blob_name = "experiment" + randlabel + "/" + source_file_name.split("/")[-1]
    upload_blob(bucket_name, source_file_name, destination_blob_name)


def upload_blob(bucket_name: str, source_file_name: str, destination_blob_name: str) -> None:
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print("File {} uploaded to {}.".format(source_file_name, destination_blob_name))


if __name__ == "__main__":
    run()
