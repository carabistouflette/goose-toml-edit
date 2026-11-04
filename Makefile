GOOSE ?= .toolchain/goose/build/goose
SANITIZER_CC ?= clang
.PHONY: setup format check test property sanitize bench
setup:
	./scripts/setup-goose.sh
format:
	$(GOOSE) format toml_edit.goose tests examples bench
check:
	python3 scripts/check-vendor.py
	$(GOOSE) format --check toml_edit.goose tests examples bench
	$(GOOSE) check tests/editor.goose
	$(GOOSE) check tests/driver.goose
	git diff --check
test:
	mkdir -p .build
	$(GOOSE) run tests/editor.goose
	$(GOOSE) build tests/editor.goose -O2 -o .build/editor
	./.build/editor
	$(GOOSE) build tests/editor.goose --debug --no-bce -o .build/editor-debug
	./.build/editor-debug
property:
	mkdir -p .build
	$(GOOSE) build tests/driver.goose -O2 -o .build/driver
	python3 scripts/property-test.py --runner .build/driver
sanitize:
	mkdir -p .build
	$(GOOSE) tests/editor.goose --standalone --debug --no-bce -o .build/editor-sanitized.c
	$(SANITIZER_CC) -O1 -g -fno-pie -no-pie -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer .build/editor-sanitized.c -lm -ldl -lpthread -o .build/editor-sanitized-$(SANITIZER_CC)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 ./.build/editor-sanitized-$(SANITIZER_CC)
	$(GOOSE) tests/driver.goose --standalone --debug --no-bce -o .build/driver-sanitized.c
	$(SANITIZER_CC) -O1 -g -fno-pie -no-pie -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer .build/driver-sanitized.c -lm -ldl -lpthread -o .build/driver-sanitized-$(SANITIZER_CC)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 python3 scripts/property-test.py --runner .build/driver-sanitized-$(SANITIZER_CC) --cases 100
bench:
	mkdir -p .build
	$(GOOSE) build bench/edit.goose -O2 -o .build/bench
	python3 bench/measure.py --goose "$(GOOSE)" --runner .build/bench --output .build/benchmark.json
