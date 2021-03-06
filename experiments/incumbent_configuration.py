#!/usr/bin/python3
# -*- coding: iso-8859-15 -*-
#!/usr/bin/python3
# -*- coding: iso-8859-15 -*-

import sys
import os
import argparse
import json
import pickle

import numpy as np
import ConfigSpace as CS
import time
import keras
import keras.backend.tensorflow_backend as K

from keras.datasets import mnist, cifar10, cifar100

from functools import partial

from os.path import join as path_join, abspath
sys.path.insert(0, abspath(path_join(__file__, "..", "..")))

from autoda.networks.architectures import ARCHITECTURES
from autoda.networks.utils import get_train_test_data
from keras.callbacks import ReduceLROnPlateau, EarlyStopping

from autoda.data_augmentation import ImageAugmentation

from autoda.networks.utils import (
    _update_history, get_input_shape,
)


def train_and_test(data, configuration=None, benchmark="AlexNet", max_epochs=200, batch_size=128, time_budget=7200, gpu_device="/gpu:1"):
    # preprocess data
    x_train, y_train, x_test, y_test, data_mean, data_variance = data

    input_shape = get_input_shape(x_train)  # NWHC

    num_classes = y_train.shape[1]

    train_history, runtime = {}, []

    used_budget, num_epochs, duration_last_epoch = 0., 0, 0.
    num_datapoints, *_ = x_train.shape

    start_time = time.time()

    config = K.tf.ConfigProto(log_device_placement=False, allow_soft_placement=True)
    session = K.tf.Session(config=config)
    K.set_session(session)

    assert benchmark in ARCHITECTURES
    network_function = ARCHITECTURES[benchmark]
    model = network_function(num_classes=num_classes, input_shape=input_shape)

    with K.tf.device('/gpu:0'):
        with session.graph.as_default():
            opt = keras.optimizers.Adam(lr=0.0016681005372000575)

            model.compile(loss='categorical_crossentropy',
                          optimizer=opt,
                          metrics=['accuracy'])

            while(num_epochs < max_epochs) and \
                    (used_budget + 1.11 * duration_last_epoch < time_budget):

                if configuration:
                    print("Using real-time data augmentation.")

                    if isinstance(configuration, CS.Configuration):
                        config = configuration
                    else:
                        config = CS.Configuration(
                            configuration_space=ImageAugmentation.get_config_space(),
                            values=configuration,
                        )
                    augmenter = ImageAugmentation(config)

                    callbacks = []

                    if benchmark == "ResNet":
                        lr_reducer = ReduceLROnPlateau(monitor='val_loss', factor=0.2,
                                  patience=5, min_lr=0.001)
                        early_stopper = EarlyStopping(min_delta=0.001, patience=10)
                        callbacks = [lr_reducer, early_stopper]
                    # Fit the model on the batches augmented data generated by apply transform
                    history = model.fit_generator(
                        augmenter.apply_transform(
                            x_train, y_train,
                            data_mean, data_variance,
                            batch_size=batch_size
                        ),
                        steps_per_epoch=num_datapoints // batch_size,
                        epochs=num_epochs + 1,
                        initial_epoch=num_epochs,
                        callbacks=callbacks
                    )
                else:
                    print('Not using data augmentation.')

                    history = model.fit(
                        x_train, y_train,
                        batch_size=batch_size,
                        epochs=num_epochs + 1,
                        initial_epoch=num_epochs,
                        shuffle=True
                    )

                train_history = _update_history(train_history, history.history)

                num_epochs += len(history.history.get("loss", []))
                duration_last_epoch = (time.time() - start_time) - used_budget
                used_budget += duration_last_epoch
                runtime.append(time.time() - start_time)

            score = model.evaluate(x_test, y_test, verbose=0)
            test_loss, test_accuracy = score[0], score[1]

    result = {
        "test_loss": test_loss,
        "test_error": 1 - test_accuracy,
        "used_budget": used_budget,
        "configs": config,
        "epochs": num_epochs,
        "benchmark": benchmark,
        "train_history": train_history
    }

    if configuration:
        result["configs"] = configuration
    else:
        result["configs"] = {}

    return result


def main():

    parser = argparse.ArgumentParser(description='Simple python script to benchmark data augmentation configurations.')


    parser.add_argument(
        "--benchmark",
        default="AlexNet",
        help="Neural network to be trained with augmented data"
    )

    parser.add_argument(
        "--pipeline",
        dest="pipeline",
        default="best_config",
        help="Data augmentation pipeline to use, choice:{default, no_augment, best_config}"
    )

    parser.add_argument(
        "--max-epochs",
        default=200,
        dest="max_epochs",
        type=int,
        help="Maximum number of epochs to train network"
    )
    parser.add_argument(
        "--batch-size", default=128,
        dest="batch_size",
        type=int,
        help="Size of a mini batch",
    )

    parser.add_argument(
        "--augment", action="store_true", help="If the data should be augmented, if flag not set defaults to false"
    )

    parser.add_argument(
        "--time-budget", default=7200, help="Maximum time budget to train a network",
        type=int, dest="time_budget"
    )
    parser.add_argument(
        "--dataset",
        default="cifar10",
        help="Dataset to train neural network on"

    )

    parser.add_argument(
        "--gpu-device",
        default="/gpu:1",
        help="gpu node to train"

    )
    parser.add_argument(
        "--optimizer",
        default="hyperband",
        help="optimizer"
    )
    parser.add_argument(
        "--run-id", help="The id of single job", dest="run_id"
    )

    parser.add_argument(
    "--output-file", "-o", help="Output File",
    default=None, dest="output_file"
    )

    parser.add_argument(
        "--configuration-file",
        help="Path to pickle file containing a multiple configuration dictionaries for "
             "our data augmentation. "
             "Defaults to `None`, which uses no data augmentation.",
        default=None, dest="configuration_file"
    )


    args = parser.parse_args()

    assert args.run_id is not None
    assert args.dataset is not None
    assert args.time_budget is not None
    assert args.pipeline is not None
    assert args.gpu_device is not None

    run_id=int(args.run_id)


    benchmark = args.benchmark
    gpu_device = args.gpu_device

    dataset = {"mnist": mnist, "cifar10": cifar10, "cifar100":cifar100}[args.dataset]

    max_epochs, batch_size, time_budget = int(args.max_epochs), int(args.batch_size), int(args.time_budget)


    configuration = None

    augment = args.augment or (args.configuration_file is not None)

    data = get_train_test_data(dataset, augment)

    if args.configuration_file:
        with open(args.configuration_file, "rb") as configuration_file:
            HB_result = pickle.load(configuration_file)
            res = HB_result.get_id2config_mapping()

    for config_id, values in res.items():
        configuration = values["config"]
        print("config:", configuration)
        print(config_id)

        results = train_and_test(
            data=data, benchmark=benchmark,
            time_budget=time_budget,
            max_epochs=max_epochs,
            configuration=configuration,
            gpu_device=gpu_device
        )

        # XXX: separate path to base_path and json name, for future
        pickle_file = path_join(
            abspath("."), "AutoData",
            args.dataset,
            args.pipeline,
            args.benchmark,
            "pickles",
            "{incumbent}_{pipeline}_{dataset}_{run_id}.pickle".format(
                incumbent=str(config_id),
                pipeline=args.pipeline, dataset=args.dataset, run_id=int(args.run_id)
                )
            )


        output_file = path_join(
            abspath("."), "AutoData",
            args.dataset,
            args.pipeline, # this path holds only for no_augment and default results
            args.benchmark,
            "{incumbent}_{pipeline}_{dataset}_{run_id}.json".format(
                incumbent=str(config_id),
                pipeline=args.pipeline, dataset=args.dataset, run_id=int(args.run_id)
            )
        )

        with open(pickle_file, "wb") as fo:
            pickle.dump(results["train_history"], fo)

        try:
            del results["train_history"]
        except KeyError:
            pass

        with open(output_file, "w") as fh:
            json.dump(results, fh)


if __name__ == "__main__":
    main()

