import cli_parser
import sys
from web3 import Web3
from utils import pexit, parse_commitcall_calldata

from utils import get_batch_details

parser = cli_parser.init_argparse()
args = parser.parse_args()

l1_url = args.l1rpc
l2_url = args.l2rpc
batch_number = args.batch

l2_batch_resp = get_batch_details(l2_url, batch_number)

commit_txn_hash = l2_batch_resp.get("commitTxHash", None)
if commit_txn_hash is None:
    pexit(f"Commit txn not found for batch: {batch_number}")

ethweb3 = Web3(Web3.HTTPProvider(l1_url))
if not ethweb3.is_connected():
    pexit("Failed to connect to L1 Ethereum.")

try:
    commit_txn = ethweb3.eth.get_transaction(commit_txn_hash)
except Exception as e:
    pexit(f"An error occurred: {e}")

parse_commitcall_calldata(commit_txn['input'], batch_number)
