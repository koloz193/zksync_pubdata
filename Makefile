init: process-circuits
	pip3 install -r requirements.txt && \
	pip3 install $(shell pwd)/zkevm_circuits/target/wheels/zkevm_circuits-1.4.1-cp311-cp311-macosx_11_0_arm64.whl --force-reinstall

process-circuits:
	pip3 install maturin && \
	pushd zkevm_circuits && \
	maturin build && \
	popd
