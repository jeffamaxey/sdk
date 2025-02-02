import logging
import uuid
from typing import Any
from unittest.mock import MagicMock, create_autospec

import pytest

from layer.clients.layer import LayerClient
from layer.clients.model_catalog import ModelCatalogClient
from layer.config import ClientConfig
from layer.contracts.project_full_name import ProjectFullName
from layer.contracts.tracker import ResourceTransferState
from layer.exceptions.exceptions import UnexpectedModelTypeException
from layer.training.train import Train


logger = logging.getLogger(__name__)


def test_train_raises_exception_if_error_happens() -> None:
    client = create_autospec(LayerClient)
    client.model_catalog.complete_model_train.side_effect = Exception("cannot complete")
    try:
        with Train(
            layer_client=client,
            name="name",
            project_full_name=ProjectFullName(
                project_name="test-project", account_name="acc"
            ),
            version="2",
            train_id=uuid.uuid4(),
            train_index="1",
        ):
            raise Exception("train exception")
    except Exception as e:
        assert str(e) == "train exception"


@pytest.mark.parametrize(
    "invalid_model_object",
    [
        "Invalid object type",
        1.23,
        [],
        {},
        set(),
    ],
)
def test_when_save_model_gets_invalid_object_then_throw_exception(
    invalid_model_object: Any,
) -> None:
    config = create_autospec(ClientConfig)
    config.model_catalog = MagicMock()
    config.s3 = MagicMock()
    config.s3.endpoint_url = MagicMock()
    client = create_autospec(LayerClient)
    client.model_catalog = ModelCatalogClient(config, logger)

    train = Train(
        layer_client=client,
        name="name",
        project_full_name=ProjectFullName(
            project_name="test-project", account_name="acc"
        ),
        version="2",
        train_id=uuid.uuid4(),
        train_index="1",
    )
    with pytest.raises(UnexpectedModelTypeException):
        train.save_model(
            invalid_model_object,
            transfer_state=ResourceTransferState(),
        )
