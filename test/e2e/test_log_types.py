from uuid import UUID

import numpy as np
import pandas as pd
import pytest
from sklearn.svm import SVC

import layer
from layer.clients.layer import LayerClient
from layer.contracts.logged_data import LoggedDataType, Video
from layer.contracts.projects import Project
from layer.decorators import dataset, model, pip_requirements
from layer.exceptions.exceptions import LayerClientResourceNotFoundException
from test.e2e.assertion_utils import E2ETestAsserter


def test_logging_in_remote_execution(
    initialized_project: Project, asserter: E2ETestAsserter, client: LayerClient
):
    # given
    dataset_name = "scalar_ds"

    str_tag = "str_tag"

    @dataset(dataset_name)
    def scalar():
        data = [[1, "product1", 15], [2, "product2", 20], [3, "product3", 10]]
        dataframe = pd.DataFrame(data, columns=["Id", "Product", "Price"])
        layer.log(
            {
                str_tag: "bar",
            }
        )
        return dataframe

    # when
    run = layer.run([scalar])

    # then
    asserter.assert_run_succeeded(run.id)

    first_ds = client.data_catalog.get_dataset_by_name(
        initialized_project.id, dataset_name
    )

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=str_tag, dataset_build_id=first_ds.build.id
    )
    assert logged_data.value == "bar"
    assert logged_data.logged_data_type == LoggedDataType.TEXT
    assert logged_data.tag == str_tag


def test_dataset_get_metadata_and_changing_old_version_logged_data(
    initialized_project: Project, asserter: E2ETestAsserter, client: LayerClient
):
    # given
    dataset_name = "scalar_ds"

    @dataset(dataset_name)
    def scalarv1():
        data = [[1, "product1", 15], [2, "product2", 20], [3, "product3", 10]]
        dataframe = pd.DataFrame(data, columns=["Id", "Product", "Price"])
        layer.log(
            {
                "zoo": 567,
            }
        )
        return dataframe

    # same dataset as above, but with different content
    @dataset(dataset_name)
    def scalarv2():
        data = [[11, "product1", 155], [22, "product2", 200], [3, "product3", 1000]]
        dataframe = pd.DataFrame(data, columns=["Id", "Product", "Price"])
        layer.log(
            {
                "str_tag": "bar",
            }
        )
        return dataframe

    scalarv1()

    ds_v1 = layer.get_dataset(dataset_name)

    scalarv2()
    ds_v2 = layer.get_dataset(dataset_name)

    # add a log to the older version of the dataset
    ds_v1.log({"foo": 123})

    assert ds_v1.get_metadata("zoo").value() == 567
    assert ds_v1.get_metadata("foo").value() == 123

    assert ds_v2.get_metadata("str_tag").value() == "bar"

    with pytest.raises(LayerClientResourceNotFoundException):
        assert ds_v2.get_metadata("zoo")

    with pytest.raises(LayerClientResourceNotFoundException):
        assert ds_v2.get_metadata("foo")

    with pytest.raises(LayerClientResourceNotFoundException):
        assert ds_v1.get_metadata("str_tag")


def test_scalar_values_logged(
    initialized_project: Project, asserter: E2ETestAsserter, client: LayerClient
):
    # given
    dataset_name = "scalar_ds"

    str_tag = "str_tag"
    int_tag = "int_tag"
    bool_tag = "bool_tag"
    float_tag = "float_tag"

    @dataset(dataset_name)
    def scalar():
        data = [[1, "product1", 15], [2, "product2", 20], [3, "product3", 10]]
        dataframe = pd.DataFrame(data, columns=["Id", "Product", "Price"])
        layer.log(
            {
                str_tag: "bar",
                int_tag: 123,
                bool_tag: True,
                float_tag: 1.11,
            }
        )
        return dataframe

    # when
    scalar()

    # then
    first_ds = client.data_catalog.get_dataset_by_name(
        initialized_project.id, dataset_name
    )

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=str_tag, dataset_build_id=first_ds.build.id
    )
    assert logged_data.value == "bar"
    assert logged_data.logged_data_type == LoggedDataType.TEXT
    assert logged_data.tag == str_tag

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=int_tag, dataset_build_id=first_ds.build.id
    )
    assert logged_data.value == "123"
    assert logged_data.logged_data_type == LoggedDataType.NUMBER
    assert logged_data.tag == int_tag

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=bool_tag, dataset_build_id=first_ds.build.id
    )
    assert logged_data.value == "True"
    assert logged_data.logged_data_type == LoggedDataType.BOOLEAN
    assert logged_data.tag == bool_tag

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=float_tag, dataset_build_id=first_ds.build.id
    )
    assert logged_data.value == "1.11"
    assert logged_data.logged_data_type == LoggedDataType.NUMBER
    assert logged_data.tag == float_tag


def test_list_values_logged(
    initialized_project: Project, asserter: E2ETestAsserter, client: LayerClient
):
    # given
    dataset_name = "list_ds"

    list_tag = "list_tag"
    numpy_tag = "numpy_tag"

    @dataset(dataset_name)
    def lists():
        data = [[1, "product1", 15], [2, "product2", 20], [3, "product3", 10]]
        dataframe = pd.DataFrame(data, columns=["Id", "Product", "Price"])
        layer.log(
            {
                list_tag: ["a", "b", "c"],
                numpy_tag: np.array([1, 2, 3]),
            }
        )
        return dataframe

    # when
    lists()

    # then
    first_ds = client.data_catalog.get_dataset_by_name(
        initialized_project.id, dataset_name
    )

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=list_tag, dataset_build_id=first_ds.build.id
    )
    assert logged_data.value == str(["a", "b", "c"])
    assert logged_data.logged_data_type == LoggedDataType.TEXT
    assert logged_data.tag == list_tag

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=numpy_tag, dataset_build_id=first_ds.build.id
    )
    assert logged_data.value == str([1, 2, 3])
    assert logged_data.logged_data_type == LoggedDataType.TEXT
    assert logged_data.tag == numpy_tag


def test_pandas_dataframe_logged(initialized_project: Project, client: LayerClient):
    # given
    ds_tag = "dataframe_tag"
    ds_name = "pandas_dataframe_log"

    @dataset(ds_name)
    def dataset_func():
        d = {"col1": [1, 2], "col2": [3, 4]}
        df = pd.DataFrame(data=d)
        layer.log({ds_tag: df})
        return df

    # then
    dataset_func()

    ds = client.data_catalog.get_dataset_by_name(initialized_project.id, ds_name)

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=ds_tag, dataset_build_id=ds.build.id
    )

    assert logged_data.logged_data_type == LoggedDataType.TABLE


def test_markdown_logged(initialized_project: Project, client: LayerClient):
    # given
    ds_tag = "dataframe_tag"
    ds_name = "markdown_dataframe_log"

    markdown = """
        # Markdown header
        Some code with [link](http://my link)
        """

    @dataset(ds_name)
    def dataset_func():
        layer.log({ds_tag: layer.Markdown(markdown)})
        return pd.DataFrame(data={"col1": [1, 2], "col2": [3, 4]})

    # then
    dataset_func()

    ds = client.data_catalog.get_dataset_by_name(initialized_project.id, ds_name)

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=ds_tag, dataset_build_id=ds.build.id
    )

    assert logged_data.logged_data_type == LoggedDataType.MARKDOWN
    assert logged_data.value == markdown


def test_image_and_video_logged(initialized_project: Project, client: LayerClient):
    # given
    ds_name = "multimedia"
    model_name = "model_with_stepped_log"
    pil_image_tag = "pil_image_tag"
    image_path_tag = "image_path_tag"
    video_path_tag = "video_path_tag"
    stepped_pil_image_tab = "stepped_pil_image_tag"
    pytorch_tensor_video_tag = "pytorch_tensor_video_tag"

    @dataset(ds_name)
    def multimedia():
        import os
        from pathlib import Path

        from PIL import Image

        image = Image.open(f"{os.getcwd()}/test/e2e/assets/log_assets/layer_logo.jpeg")
        layer.log({pil_image_tag: image})

        image_path = Path(f"{os.getcwd()}/test/e2e/assets/log_assets/layer_logo.jpeg")
        layer.log({image_path_tag: image_path})

        video_path = Path(f"{os.getcwd()}/test/e2e/assets/log_assets/layer_video.mp4")
        layer.log({video_path_tag: video_path})

        import torch

        tensor_video = torch.rand(10, 3, 100, 200)
        layer.log({pytorch_tensor_video_tag: Video(tensor_video)})

        return pd.DataFrame(data={"col1": [1, 2], "col2": [3, 4]})

    multimedia()

    ds = client.data_catalog.get_dataset_by_name(initialized_project.id, ds_name)

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=pil_image_tag, dataset_build_id=ds.build.id
    )
    assert logged_data.value.startswith("https://logged-data--layer")
    assert logged_data.value.endswith(pil_image_tag)
    assert logged_data.logged_data_type == LoggedDataType.IMAGE

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=image_path_tag, dataset_build_id=ds.build.id
    )
    assert logged_data.value.startswith("https://logged-data--layer")
    assert logged_data.value.endswith(image_path_tag)
    assert logged_data.logged_data_type == LoggedDataType.IMAGE

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=video_path_tag, dataset_build_id=ds.build.id
    )
    assert logged_data.value.startswith("https://logged-data--layer")
    assert logged_data.value.endswith(video_path_tag)
    assert logged_data.logged_data_type == LoggedDataType.VIDEO

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=pytorch_tensor_video_tag, dataset_build_id=ds.build.id
    )
    assert logged_data.value.startswith("https://logged-data--layer")
    assert logged_data.value.endswith(pytorch_tensor_video_tag)
    assert logged_data.logged_data_type == LoggedDataType.VIDEO

    @pip_requirements(packages=["scikit-learn==0.23.2"])
    @model(model_name)
    def train_model():
        import os

        from PIL import Image
        from sklearn import datasets

        iris = datasets.load_iris()
        clf = SVC()
        result = clf.fit(iris.data, iris.target)

        image = Image.open(f"{os.getcwd()}/test/e2e/assets/log_assets/layer_logo.jpeg")
        for step in range(4, 6):
            layer.log({stepped_pil_image_tab: image}, step=step)

        print("model1 computed fully")
        return result

    train_model()

    mdl = layer.get_model(model_name)
    logged_data = client.logged_data_service_client.get_logged_data(
        tag=stepped_pil_image_tab, train_id=UUID(mdl.storage_config.train_id.value)
    )
    assert logged_data.logged_data_type == LoggedDataType.IMAGE
    assert len(logged_data.values_with_coordinates) == 2
    assert logged_data.values_with_coordinates[4].startswith(
        "https://logged-data--layer"
    )
    assert logged_data.values_with_coordinates[4].endswith(
        f"{stepped_pil_image_tab}/epoch/4"
    )
    assert logged_data.values_with_coordinates[5].startswith(
        "https://logged-data--layer"
    )
    assert logged_data.values_with_coordinates[5].endswith(
        f"{stepped_pil_image_tab}/epoch/5"
    )


def test_file_and_directory_logged(initialized_project: Project, client: LayerClient):
    # given
    ds_name = "file_and_directory"
    file_tag = "file_tag"
    directory_tag = "directory_tag"

    @dataset(ds_name)
    def file_and_directory():
        import os
        from pathlib import Path

        layer.log(
            {file_tag: Path(f"{os.getcwd()}/test/e2e/assets/log_assets/somefile.txt")}
        )
        layer.log(
            {directory_tag: Path(f"{os.getcwd()}/test/e2e/assets/log_assets/somedir")}
        )

        return pd.DataFrame(data={"col1": [1, 2], "col2": [3, 4]})

    file_and_directory()

    ds = client.data_catalog.get_dataset_by_name(initialized_project.id, ds_name)

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=file_tag, dataset_build_id=ds.build.id
    )
    assert logged_data.value.startswith("https://logged-data--layer")
    assert logged_data.value.endswith(file_tag)
    assert logged_data.logged_data_type == LoggedDataType.FILE

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=directory_tag, dataset_build_id=ds.build.id
    )
    assert logged_data.value.startswith("https://logged-data--layer")
    assert logged_data.value.endswith(directory_tag)
    assert logged_data.logged_data_type == LoggedDataType.DIRECTORY


def test_matplotlib_objects_logged(initialized_project: Project, client: LayerClient):
    # given
    figure_tag = "matplotlib_figure_tag"
    plot_tag = "matplotlib_pyplot_tag"

    ds_name = "ds_with_plots"

    @dataset(ds_name)
    def dataset_func():
        import matplotlib.pyplot as plt
        import seaborn

        data = pd.DataFrame({"col": [1, 2, 42]})
        plot = seaborn.histplot(data=data, x="col", color="green")
        layer.log({plot_tag: plot})

        figure = plt.figure()
        figure.add_subplot(111)

        layer.log({figure_tag: figure})
        return pd.DataFrame(data={"col1": [1, 2], "col2": [3, 4]})

    # then
    dataset_func()

    ds = client.data_catalog.get_dataset_by_name(initialized_project.id, ds_name)

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=figure_tag, dataset_build_id=ds.build.id
    )

    assert logged_data.value.startswith("https://logged-data--layer")
    assert logged_data.value.endswith(figure_tag)
    assert logged_data.logged_data_type == LoggedDataType.IMAGE

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=plot_tag, dataset_build_id=ds.build.id
    )

    assert logged_data.value.startswith("https://logged-data--layer")
    assert logged_data.value.endswith(plot_tag)
    assert logged_data.logged_data_type == LoggedDataType.IMAGE


def test_metrics_logged(initialized_project: Project, client: LayerClient):
    # given
    metric_tag_1 = "metric_tag_1"
    metric_tag_2 = "metric_tag_2"

    ds_name = "metrics_ds"

    @dataset(ds_name)
    def metrics():
        for step in range(1, 5):
            layer.log(
                {metric_tag_1: f"value {step}", metric_tag_2: f"value {step}"}, step
            )
        return pd.DataFrame(data={"col1": [1, 2], "col2": [3, 4]})

    # then
    metrics()

    ds = client.data_catalog.get_dataset_by_name(initialized_project.id, ds_name)

    logged_data = client.logged_data_service_client.get_logged_data(
        tag=metric_tag_1, dataset_build_id=ds.build.id
    )

    assert logged_data.logged_data_type == LoggedDataType.TEXT
    # value from the last step
    assert logged_data.value == "value 4"
