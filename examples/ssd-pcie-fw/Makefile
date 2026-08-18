CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -O2
CPPFLAGS ?= -Iinclude
BUILD_DIR := build
DIST_DIR := dist

.PHONY: all test lint package clean

all: $(BUILD_DIR)/ssd-pcie-fw-sample.elf

$(BUILD_DIR):
	mkdir -p $@

$(DIST_DIR):
	mkdir -p $@

$(BUILD_DIR)/fw_core.o: src/fw_core.c include/fw_core.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/main.o: src/main.c include/fw_core.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/ssd-pcie-fw-sample.elf: $(BUILD_DIR)/fw_core.o $(BUILD_DIR)/main.o
	$(CC) $(CFLAGS) $^ -o $@

$(BUILD_DIR)/test_fw_core: tests/test_fw_core.c src/fw_core.c include/fw_core.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/test_fw_core.c src/fw_core.c -o $@

test: $(BUILD_DIR)/test_fw_core
	./$(BUILD_DIR)/test_fw_core

lint:
	$(CC) $(CPPFLAGS) $(CFLAGS) -fsyntax-only src/fw_core.c src/main.c tests/test_fw_core.c

package: all | $(DIST_DIR)
	cp $(BUILD_DIR)/ssd-pcie-fw-sample.elf $(DIST_DIR)/ssd-pcie-fw-sample.elf

clean:
	rm -rf $(BUILD_DIR) $(DIST_DIR)
