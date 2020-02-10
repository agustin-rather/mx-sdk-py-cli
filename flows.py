import logging
from erdpy.projects import load_project
from erdpy.hosts import TestnetHost
from erdpy.accounts import Account
from erdpy.contracts import SmartContract

logger = logging.getLogger("examples")

def deploy_smart_contract(project_directory, address, pem_file, proxy_url):
    logger.info("deploy_smart_contract")

    project = load_project(project_directory)
    bytecode = project.get_bytecode()
    contract = SmartContract(bytecode=bytecode)
    host = TestnetHost(proxy_url)
    owner = Account(address, pem_file)

    def flow():
        tx, address = host.deploy_contract(contract, sender=owner)
        logger.info("Tx hash: %s", tx)
        logger.info("Contract address: %s", address)

    host.run_flow(flow)