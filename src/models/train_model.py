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
import time

import numpy as np
import torch
import wandb
from dataset_fetcher import Dataset_fetcher
from model_architecture import XrayClassifier
from omegaconf import OmegaConf
from torch import nn, optim
from cloud_functions import upload_blob

def train(TRAIN_PATHS: dict[str, str], TEST_PATHS: dict[str, str]) -> None:
    """This function runs the whole training procedure"""

    # set flags / seeds
    np.random.seed(1)
    torch.manual_seed(1)
    workingdir = os.getcwd() + "/"

    # Load config file
    config = OmegaConf.load(workingdir + "config/config.yaml")

    # Initialize logging with wandb and track conf settings
    wandb.init(project="MLOps-Project", config=dict(config))

    # Optimizer Hyperparameter
    EPOCHS = config.EPOCHS
    BATCH_SIZE = config.BATCH_SIZE
    LEARNING_RATE = config.LEARNING_RATE
    DROPOUT_PROBABILITY = config.DROPOUT_PROBABILITY

    # config  variables
    N_WORKERS = config.N_WORKERS
    best_val = config.BEST_VAL

    print("[INFO] Load datasets from disk...")
    training_set = Dataset_fetcher(TRAIN_PATHS["images"], TRAIN_PATHS["labels"])
    testing_set = Dataset_fetcher(TEST_PATHS["images"], TEST_PATHS["labels"])

    print("[INFO] Prepare dataloaders...")
    trainloader = torch.utils.data.DataLoader(
        training_set, shuffle=True, num_workers=N_WORKERS, batch_size=BATCH_SIZE
    )
    testloader = torch.utils.data.DataLoader(
        testing_set, shuffle=False, num_workers=N_WORKERS, batch_size=BATCH_SIZE
    )

    print("[INFO] Building network...")
    model = XrayClassifier(num_classes=3, dropout_probability=DROPOUT_PROBABILITY)
    wandb.watch(model, log_freq=100)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    print("[INFO] Started training the model...\n")
    start_t = time.time()
    for epoch in range(EPOCHS):
        # Training Loop Start
        model.train()

        losses = []
        correct = 0
        total = 0

        for images, labels in trainloader:
            optimizer.zero_grad(set_to_none=True)

            output = model(images)
            loss = criterion(output, labels)

            loss.backward()
            optimizer.step()

            losses.append(loss.item())
            total += len(labels)

            _, predicted = torch.max(output.data, 1)
            correct += (predicted == labels).sum().item()

        train_loss = sum(losses) / max(1, len(losses))
        train_acc = 100 * correct // total

        # Log train loss and acc
        wandb.log({"train_loss": train_loss})
        wandb.log({"train_acc": train_acc})

        print(
            f"Epoch {epoch+1}/{EPOCHS} \n \tTraining:  "
            f" Loss={train_loss:.2f}\t Accuracy={train_acc}%\t"
        )
        # Training Loop End

        with torch.no_grad():
            # Evaluation Loop Start
            model.eval()

            losses = []
            correct = 0
            total = 0

            for images, labels in testloader:

                output = model(images)
                loss = criterion(output, labels)

                losses.append(loss.item())
                total += len(labels)

                _, predicted = torch.max(output.data, 1)
                correct += (predicted == labels).sum().item()

        val_loss = sum(losses) / max(1, len(losses))
        val_acc = 100 * correct // total

        # Log train loss and acc
        wandb.log({"val_loss": val_loss})
        wandb.log({"val_acc": val_acc})

        print(f"\tValidation: Loss={val_loss:.2f}\t Accuracy={val_acc}%\t")

        # Evaluation loop end

        # Save best model if val_loss in current epoch is lower than the best validation loss
        if val_loss < best_val:
            best_val = val_loss
            print("\n[INFO] Saving new best_model...\n")
            torch.save(
                {
                    "epoch": epoch + 1,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                },
                config.BEST_MODEL_PATH,
            )

        # Save model based on the frequency defined by "args.save_after"
        if (epoch + 1) % 5 == 0:
            print(f"\n[INFO] Saving model as checkpoint -> epoch_{epoch+1}.pth\n")
            torch.save(
                {
                    "epoch": epoch + 1,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                },
                os.path.join(config.CHECKPOINT_PATH, "epoch_{}.pth".format(epoch + 1)),
            )

    end_t = time.time()
    run_time = end_t - start_t

    # if checkpoint folder is meant to be saved for each experiment
    # wandb.save(config.CHECKPOINT_PATH)

    print(f"[INFO] Successfully completed training session. Running time: {run_time/60:.2f} min")


if __name__ == "__main__":

    # this path must be adapted to your own machine
    root_dir = os.getcwd() + "/"  # "/home/davidparham/Workspaces/DTU/MLOps/project/"

    TRAIN_PATHS = {
        "images": root_dir + "data/preprocessed/covid_not_norm/train_images.pt",
        "labels": root_dir + "data/preprocessed/covid_not_norm/train_labels.pt",
    }

    TEST_PATHS = {
        "images": root_dir + "data/preprocessed/covid_not_norm/test_images.pt",
        "labels": root_dir + "data/preprocessed/covid_not_norm/test_labels.pt",
    }


    train(TRAIN_PATHS, TEST_PATHS)
