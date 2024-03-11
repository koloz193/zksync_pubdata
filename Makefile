init: init-submodule process-circuits
	pip3 install -r requirements.txt && \
	pip3 install $(shell pwd)/zkevm_circuits/target/wheels/*.whl --force-reinstall

process-circuits:
	pip3 install maturin && \
	pushd zkevm_circuits && \
	maturin build && \
	popd

init-submodule:
	git submodule init && git submodule update
