from functools import partial

import keras
from keras.models import Sequential
from keras_contrib.applications.wide_resnet import WideResidualNetwork
from keras_contrib.applications.resnet import ResNet18
from keras.models import Sequential
from keras.layers import (
    Activation, Conv2D, Dense,
    Dropout, BatchNormalization, Flatten,
    MaxPooling2D
)


def alexnet(input_shape, num_classes,
            optimizer=keras.optimizers.Adam(lr=0.0016681005372000575),
            loss=keras.losses.categorical_crossentropy,
            metrics=["accuracy", ]):
    # AlexNet

    model = Sequential()

    model.add(Conv2D(140, (5, 5), padding='same',
                     input_shape=input_shape))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(3, 3), strides=2))

    model.add(Conv2D(94, (5, 5)))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(3, 3), strides=2))

    model.add(Conv2D(126, (5, 5), padding='same'))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(3, 3), strides=2))

    model.add(Flatten())
    model.add(Dense(num_classes))
    model.add(Activation('softmax'))


    return model


def lenet(input_shape, num_classes,
          optimizer=keras.optimizers.Adam(lr=0.0016681005372000575),
          loss=keras.losses.categorical_crossentropy,
          metrics=["accuracy", ]):

    # LeNet
    model = Sequential()
    model.add(Conv2D(32, kernel_size=(3, 3),
                     activation='relu',
                     input_shape=input_shape))
    model.add(Conv2D(64, (3, 3), activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))
    model.add(Flatten())
    model.add(Dense(128, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(num_classes, activation='softmax'))

    model.compile(loss=loss, optimizer=optimizer, metrics=metrics)

    return model


def resnet(input_shape, num_classes, wide=False):
    if wide:
        model = WideResidualNetwork(
            depth=28, width=8, dropout_rate=0.0, weights=None,
            input_shape=input_shape, classes=num_classes
        )
    else:
        model = ResNet18(input_shape=input_shape, classes=num_classes)

    model.summary()
    return model


ARCHITECTURES = {
    "AlexNet": alexnet,
    "LeNet": lenet,
    "WideResNet": partial(resnet, wide=True),
    "ResNet": resnet
}
