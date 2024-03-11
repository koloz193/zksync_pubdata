import cli_parser
from web3 import Web3
from utils import pexit, parse_commitcall_calldata
from flask import Flask, render_template
from flask_caching import Cache

from utils import get_batch_details

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/batch/<int:batch_number>')
@cache.memoize(60)
def batch(batch_number):
    l1_url = app.config['l1_url']
    l2_url = app.config['l2_url']
    network = app.config['network']

    batch = {
        'id': batch_number
    }

    l2_batch_resp = get_batch_details(l2_url, batch_number)

    commit_txn_hash = l2_batch_resp.get("commitTxHash", None)
    if commit_txn_hash is None:
        pexit(f"Commit txn not found for batch: {batch_number}")

    batch['commitTxHash'] = commit_txn_hash

    batch['network'] = network

    ethweb3 = Web3(Web3.HTTPProvider(l1_url))
    if not ethweb3.is_connected():
        pexit("Failed to connect to L1 Ethereum.")

    try:
        commit_txn = ethweb3.eth.get_transaction(commit_txn_hash)
    except Exception as e:
        pexit(f"An error occurred: {e}")

    (
        pubdata_source, 
        num_blobs, 
        new_state_root, 
        pubdata_info, 
        parsed_system_logs, 
        pubdata_length
    ) = parse_commitcall_calldata(network, commit_txn['input'], batch_number)

    batch['pubdata_source'] = pubdata_source
    batch['num_blobs'] = num_blobs

    batch['newStateRoot'] = new_state_root.hex()

    batch['l1_l2_msg_counter'] = pubdata_info[0]
    batch['large_msg_counter'] = pubdata_info[1]
    batch['bytecodes'] = pubdata_info[2]
    batch['initial_writes'] = {k.hex():(v[0], v[1].hex()) for k,v in pubdata_info[3].items()}
    
    batch['repeated_writes'] = {k.hex():(v[0], v[1].hex()) for k,v in pubdata_info[4].items()}

    batch['initial_writes_count'] = len(pubdata_info[3])
    batch['repeated_writes_count'] = len(pubdata_info[4])
    batch['parsed_system_logs'] = parsed_system_logs
    batch['pubdata_length'] = pubdata_length
    batch['pubdata_msg_length'] = pubdata_info[5][0]
    batch['pubdata_bytecode_length'] = pubdata_info[5][1]
    batch['pubdata_statediff_length'] = pubdata_info[5][2]
    uncompressed = len(batch['initial_writes']) * 64 + len(batch["repeated_writes"]) * 40 
    if uncompressed > 0:
        batch['statediff_compression_percent'] = round((batch['pubdata_statediff_length']  * 100 / uncompressed))
    
    return render_template('batch.html', batch=batch)


if __name__ == '__main__':
    parser = cli_parser.init_argparse()
    args = parser.parse_args()
    
    config = {
        'l1_url': args.l1rpc,
        'l2_url': args.l2rpc,
        'network': args.network,
    }
    app.config.update(config)
    app.run(debug=True)