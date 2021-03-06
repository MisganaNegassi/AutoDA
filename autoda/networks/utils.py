
import keras
from keras import backend as K
from sklearn.model_selection import train_test_split

import numpy as np
from collections import defaultdict


def enforce_image_format(image_format):
    def decorator(function):
        K.set_image_data_format(image_format)
        return function
    return decorator

#FIXME: find a way to remove argument augment
# move out normalization out of of get_data
# remove dependency to scikit learn because of just train_test_split
@enforce_image_format("channels_last")
def get_data(dataset, augment=True):

    # The data, shuffled and split between train and test sets:
    (x_train, y_train), (x_test, y_test) = dataset.load_data()

    num_classes = get_num_classes(y_train)

    img_rows, img_cols = x_train.shape[2], x_train.shape[2]
    # reshape 3D image to 4D
    if x_train.ndim == 3:
        x_train = x_train.reshape(x_train.shape[0], img_rows, img_cols, 1)
        x_test = x_test.reshape(x_test.shape[0], img_rows, img_cols, 1)

    # compute zero mean and unit variance for normalization
    mean, variance = compute_zero_mean_unit_variance(x_train)

    x_train, x_valid, y_train, y_valid = train_test_split(x_train, y_train, test_size=0.2)

    y_train = y_train.reshape((y_train.shape[0]))
    y_valid = y_valid.reshape((y_valid.shape[0]))
    y_test = y_test.reshape((y_test.shape[0]))

    if not augment:
        print("normalize training set beforehand if no data_augmentation")
        x_train = normalize(x_train, mean, variance)
    x_valid = normalize(x_valid, mean, variance)
    x_test = normalize(x_test, mean, variance)

    # dimensions of data
    print(x_train.shape, 'x_train Dimensions')
    print(x_train.shape[0], 'train samples')
    print(x_valid.shape[0], 'validation samples')
    print(x_test.shape[0], 'test samples')

    # Convert class vectors to binary class matrices.
    y_train = keras.utils.to_categorical(y_train, num_classes)
    y_valid = keras.utils.to_categorical(y_valid, num_classes)
    y_test = keras.utils.to_categorical(y_test, num_classes)

    data = x_train, y_train, x_valid, y_valid, x_test, y_test, mean, variance

    return data

def get_train_test_data(dataset, augment=True):

    # The data, shuffled and split between train and test sets:
    (x_train, y_train), (x_test, y_test) = dataset.load_data()

    num_classes = get_num_classes(y_train)

    img_rows, img_cols = x_train.shape[2], x_train.shape[2]
    # reshape 3D image to 4D
    if x_train.ndim == 3:
        x_train = x_train.reshape(x_train.shape[0], img_rows, img_cols, 1)
        x_test = x_test.reshape(x_test.shape[0], img_rows, img_cols, 1)

    # compute zero mean and unit variance for normalization
    mean, variance = compute_zero_mean_unit_variance(x_train)

    y_train = y_train.reshape((y_train.shape[0]))
    y_test = y_test.reshape((y_test.shape[0]))

    if not augment:
        print("normalize training set beforehand if no data_augmentation")
        x_train = normalize(x_train, mean, variance)
    x_test = normalize(x_test, mean, variance)

    # dimensions of data
    print(x_train.shape, 'x_train Dimensions')
    print(x_train.shape[0], 'train samples')
    print(x_test.shape[0], 'test samples')

    # Convert class vectors to binary class matrices.
    y_train = keras.utils.to_categorical(y_train, num_classes)
    y_test = keras.utils.to_categorical(y_test, num_classes)

    data = x_train, y_train, x_test, y_test, mean, variance

    return data


def _merge_dict(dict_list):
    dd = defaultdict(list)
    for d in dict_list:
        for key, value in d.items():
            if not hasattr(value, '__iter__'):
                value = (value,)
            [dd[key].append(v) for v in value]
    return dict(dd)


def _update_history(train_history, history):
    if len(train_history) == 0:
        train_history = history
    else:
        train_history = _merge_dict([train_history, history])
    return train_history


def get_num_classes(y_train):
    import numpy as np
    num_classes = int(np.max(y_train)) + 1

    try:
        num_elements, num_classes = len(num_classes), num_classes[0]
    except TypeError:
        return num_classes
    else:
        assert num_elements == 1
        return num_classes


def get_input_shape(x_train):
    _, *shape = x_train.shape
    return shape


def compute_zero_mean_unit_variance(x, mean=None, std=None):

    """ Compute zero mean and unit variance of training set
        for normalizating augmented batch in training

    """

    if mean is None:
        mean = np.mean(x, axis=0)
    if std is None:
        std = np.std(x, axis=0)

    return mean, std


def normalize(x, mean, std):
    """ Normalize data by its zero mean and standard variance

    """

    x_normalized = (x - mean) / (std + 1e-7)

    return x_normalized


def to_rgb(img):
    """
    Converts the given array into RGB image.
    """

    img = np.atleast_3d(img)
    channels = img.shape[2]
    if channels < 3:
        img = np.tile(img, 3)

    img[np.isnan(img)] = 0
    img -= np.amin(img)
    img /= np.amax(img)
    img *= 255
    return img
