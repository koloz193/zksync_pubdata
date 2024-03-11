from constants import *
from pubdata import *
from eth_abi import decode
from collections import namedtuple
from typing import List
from pubdata import parse_pubdata_calldata
import requests
import json
import sys
from zkevm_circuits import ethereum_4844_data_into_zksync_pubdata

ParsedSystemLog = namedtuple("ParsedSystemLog", ['sender', 'key', 'value'])

def parse_system_logs(system_logs) -> List[ParsedSystemLog]:
    # split into pieces - each piece is 88 bytes long.
    logs = [system_logs[i:i + SYSTEM_LOG_SIZE] for i in range(0, len(system_logs), SYSTEM_LOG_SIZE)]

    parsed_logs = []
    for log in logs:
        sender = log[4:24].hex()
        key = log[24:56].hex()
        value = log[56:88].hex()
        parsed_sender = SYSTEM_LOG_SENDERS.get(sender, sender)
        parsed_key = SYSTEM_LOG_KEYS.get(key, key)
        # print(f"log: {parsed_sender} : key: {parsed_key} -> {value}" )
        parsed_logs.append(
            ParsedSystemLog(parsed_sender, parsed_key, value)
        )

    return parsed_logs

def parse_commitcall_calldata(network, calldata, batch_to_find):
    selector = calldata[0:4]

    if selector.hex() != COMMIT_BATCHES_SELECTOR:
        print(f"\033[91m[FAIL] Invalid selector {selector.hex()} - expected {COMMIT_BATCHES_SELECTOR}. \033[0m")
        raise Exception
    
    (_, new_batches_data) = decode(["(uint64,bytes32,uint64,uint256,bytes32,bytes32,uint256,bytes32)", "(uint64,uint64,uint64,bytes32,uint256,bytes32,bytes32,bytes32,bytes,bytes)[]"], calldata[4:])

    # We might be commiting multiple batches in one call - find the one that we're looking for
    selected_batch = None
    for batch in new_batches_data:
        if batch[0] == batch_to_find:
            selected_batch = batch
    
    if not selected_batch:
        pexit(f"\033[91m[FAIL] Could not find batch {batch_to_find} in calldata.. \033[0m")
    
    (
        batch_number_, 
        timestamp_, 
        index_repeated_storage_changes_, 
        new_state_root_, 
        num_l1_tx_, 
        priority_op_hash_, 
        bootloader_initial_heap_, 
        events_queue_state_, 
        system_logs, 
        pubdata_commitments
    ) = selected_batch

    parsed_system_logs = parse_system_logs(system_logs)

    (pubdata_source, pubdata) = pubdata_commitments[0], pubdata_commitments[1:]
    num_blobs = 0

    if pubdata_source == PubdataSource.CALLDATA:
        # Need to parse out the last 32 bytes as they contain the blob commitment
        pubdata = pubdata[:len(pubdata) - 32]
        pubdata_info = parse_pubdata_calldata(pubdata)
        total_pubdata = pubdata
    elif pubdata_source == PubdataSource.BLOBS:
        blobs = []
        for i in range(0, len(pubdata), 144):
            pubdata_commitment = pubdata[i:i+144]
            kzg_commitment = pubdata_commitment[48:96]
            blob = get_blob(network, kzg_commitment.hex())[2:]
            num_blobs += 1
            blob_bytes = bytes.fromhex(blob)
            blobs += ethereum_4844_data_into_zksync_pubdata(blob_bytes)
        del_trailing_zeroes(blobs)
        blob_bytes = bytes(blobs)
        pubdata_info = parse_pubdata_calldata(blob_bytes)
        total_pubdata = blob_bytes
    else:
        pexit(f"Unsupported pubdata source byte: {pubdata_source}")
    
    return (pubdata_source, num_blobs, new_state_root_, pubdata_info, parsed_system_logs, len(total_pubdata))

def get_blob(network, kzg_commitment):
    if network == 'mainnet':
        base = 'https://api.blobscan.com/api/blobs/'
    elif network == 'goerli':
        base = 'https://api.goerli.blobscan.com/api/blobs/'
    elif network == 'sepolia':
        base = 'https://api.sepolia.blobscan.com/api/blobs/'
    else:
        pexit(f"Network not supported: {network}")

    url = base + "0x" + kzg_commitment
    resp = requests.get(url)
    return resp.json()['data']

def get_batch_details(url, batch_number):
    headers = {"Content-Type": "application/json"}
    data = {"jsonrpc": "2.0", "id": 1, "method": "zks_getL1BatchDetails", "params": [batch_number]}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(response.json())
    return response.json()["result"]

def pexit(msg: str):
    print(msg)
    sys.exit(1)

def del_trailing_zeroes(mylist):
    for i in reversed(mylist):
        if not i:
            del mylist[-1]
        else:
            break
