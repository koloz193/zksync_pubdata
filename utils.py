from constants import *
from pubdata import *
from eth_abi import decode
from collections import namedtuple
from typing import List
from pubdata import parse_pubdata_calldata
import requests
import json
import sys

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

def parse_commitcall_calldata(calldata, batch_to_find):
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

    if pubdata_source == PubdataSource.CALLDATA:
        # Need to parse out the last 32 bytes as they contain the blob commitment
        pubdata = pubdata[:len(pubdata) - 32]
        pubdata_info = parse_pubdata_calldata(pubdata)
        print(pubdata_info)
    elif pubdata_source == PubdataSource.BLOBS:
        print("BLOBS")
    else:
        pexit(f"Unsupported pubdata source byte: {pubdata_source}")


def get_batch_details(url, batch_number):
    headers = {"Content-Type": "application/json"}
    data = {"jsonrpc": "2.0", "id": 1, "method": "zks_getL1BatchDetails", "params": [batch_number]}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()["result"]

def pexit(msg: str):
    print(msg)
    sys.exit(1)
