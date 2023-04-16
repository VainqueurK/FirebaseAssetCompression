# import requests
# import json
# from web3 import Web3, HTTPProvider
#
# def get_erc721_contracts(contract_list):
#     web3 = Web3(HTTPProvider('https://rpcapi.fantom.network'))
#
#     contracts = []
#
#     for contract_address in contract_list:
#         if isinstance(contract_address, str):
#             # Remove whitespace and empty lines
#             contract_address = contract_address.strip()
#
#             # Check if the contract is an ERC721 token
#             abi_url = f"https://api.ftmscan.com/api?module=contract&action=getabi&address={contract_address}"
#             response = requests.get(abi_url)
#             abi = json.loads(response.content)['result']
#             contract = web3.eth.contract(address=contract_address, abi=abi)
#
#             if contract.functions.supportsInterface('0x80ac58cd').call():
#                 contracts.append(contract_address)
#         else:
#             print(f"Contract address {contract_address} is not a string, skipping...")
#
#     return contracts
#
#
# # Read contract addresses from a text file
# def read_contracts_from_file(file_path):
#     with open(file_path, 'r') as file:
#         contract_list = file.readlines()
#
#     return contract_list
#
#
# # Get ERC721 contracts from a list of contract addresses
# def get_erc721_contracts_from_list(contract_list):
#     return get_erc721_contracts(contract_list)
#
#
# # Example usage with a text file containing contract addresses
# file_path = "contract_addresses.txt"
# contract_list = read_contracts_from_file(file_path)
# erc721_contracts = get_erc721_contracts_from_list(contract_list)
#
# # Example usage with a Python list of contract addresses
# contract_list = ["0x1792a96E5668ad7C167ab804a100ce42395Ce54D"]
# erc721_contracts = get_erc721_contracts_from_list(contract_list)
#
# print(f"ERC721 contracts: {erc721_contracts}")
