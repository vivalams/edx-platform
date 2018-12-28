import requests
import json
import logging

log = logging.getLogger("edx.azure_msi_key_vault")

def _get_configs_from_keyvault(request_uri=None, payload=None, key_vault_url=None, key_name=None, api_version=None):
    """
    Read configurations from azure key vault
    """
    try:
        request_url = "{}/secrets/{}?api-version={}".format(key_vault_url, key_name, api_version)
        # get access token with Azure MSI
        result = requests.get(request_uri, params=payload, headers={'Metadata': 'true'})
        access_token = result.json()['access_token']

        # get value from Azure keyvault using access token
        headers_credentials = {'Authorization': 'Bearer' + ' ' + (access_token)}
        response = requests.get(request_url, headers=headers_credentials)
        secrets = json.loads(response.json()['value'])

    except Exception as e:
        # we don't want the platform to break for errors occured while accessing kay-vault configs.
        # so we are retutning the the empty dictionary in any exception.
        log.error("There was an error while rendering configs from azure key-vault. %s", e)
        secrets = {}

    return secrets

def override_configs_from_keyvault(configs,request_uri=None, payload=None, key_vault_url=None, key_name=None, api_version=None):
    """
    Override the configurations using  keyvault configs
    """
    secrets = _get_configs_from_keyvault(request_uri, payload, key_vault_url, key_name, api_version)
    for secret in secrets:
        configs[secret] = secrets.get(secret)
    return configs
