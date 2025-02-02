import contextlib
from typing import Optional
from unittest.mock import MagicMock, patch
from uuid import UUID

from layer.clients.account_service import AccountServiceClient
from layer.clients.data_catalog import DataCatalogClient
from layer.clients.layer import LayerClient
from layer.clients.project_service import ProjectServiceClient
from layer.config import ClientConfig, Config
from layer.contracts.accounts import Account
from layer.contracts.projects import Project


@contextlib.contextmanager
def project_client_mock(
    project_api_stub: Optional[ProjectServiceClient] = None,
    data_catalog_client: Optional[DataCatalogClient] = None,
):
    project_client = _get_mock_project_service_client(project_api_stub=project_api_stub)
    data_catalog_client = (
        MagicMock(spec=DataCatalogClient)
        if data_catalog_client is None
        else data_catalog_client
    )
    account = MagicMock()
    account.name = "account-name"
    account_service_client = MagicMock(
        spec=AccountServiceClient, **{"get_my_account.return_value": account}
    )

    client = MagicMock()
    client.__enter__.return_value = MagicMock(
        set_spec=LayerClient,
        data_catalog=data_catalog_client,
        project_service_client=project_client,
        account=account_service_client,
    )

    config = MagicMock(
        set_spec=Config,
        client=MagicMock(set_spec=ClientConfig, grpc_gateway_address="grpc.test"),
    )

    async def config_refresh():
        return config

    with patch("layer.clients.layer.LayerClient.init", return_value=client), patch(
        "layer.config.ConfigManager.refresh", side_effect=config_refresh
    ):
        yield


VALID_UUID = UUID(int=0x12345678123456781234567812345678)


def _get_mock_project_service_client(
    project_api_stub: Optional[MagicMock] = None,
) -> ProjectServiceClient:
    project_client = ProjectServiceClient()
    if project_api_stub is None:
        valid_response = Project(
            id=VALID_UUID,
            name="test-proj",
            account=Account(
                id=VALID_UUID,
                name="test-acc",
            ),
        )
        project_client.get_project = MagicMock(return_value=valid_response)
    else:
        # can't use spec_set as it does not recognise methods as defined by protocompiler
        project_client._service = project_api_stub  # pylint: disable=protected-access
    return project_client
