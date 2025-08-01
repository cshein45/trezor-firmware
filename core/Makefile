
.PHONY: vendor

# get the number of CPU cores in a "portable" manner
# (accounting for darwin and big.LITTLE archs)
JOBS = $(shell sysctl -n hw.perflevel0.physicalcpu 2>/dev/null ||\
               sysctl -n hw.physicalcpu            2>/dev/null ||\
               sysctl -n hw.ncpu                   2>/dev/null ||\
               nproc                               2>/dev/null ||\
               echo 4)
MAKE = make -j $(JOBS)

BUILD_DIR             = build
BOARDLOADER_BUILD_DIR = $(BUILD_DIR)/boardloader
BOOTLOADER_BUILD_DIR  = $(BUILD_DIR)/bootloader
BOOTLOADER_CI_BUILD_DIR   = $(BUILD_DIR)/bootloader_ci
BOOTLOADER_EMU_BUILD_DIR  = $(BUILD_DIR)/bootloader_emu
PRODTEST_BUILD_DIR    = $(BUILD_DIR)/prodtest
PRODTEST_EMU_BUILD_DIR    = $(BUILD_DIR)/prodtest_emu
REFLASH_BUILD_DIR     = $(BUILD_DIR)/reflash
KERNEL_BUILD_DIR      = $(BUILD_DIR)/kernel
SECMON_BUILD_DIR      = $(BUILD_DIR)/secmon
FIRMWARE_BUILD_DIR    = $(BUILD_DIR)/firmware
UNIX_BUILD_DIR        = $(BUILD_DIR)/unix
RUST_BUILD_DIR        = $(BUILD_DIR)/rust

UNAME_S := $(shell uname -s)
UNIX_PORT_OPTS ?=
CROSS_PORT_OPTS ?=

PRODUCTION ?= 0
PYOPT      ?= 1
BITCOIN_ONLY ?= 0
BOOTLOADER_QA ?= 0
BOOTLOADER_DEVEL ?= 0
UNSAFE_FW ?= 0
DISABLE_OPTIGA ?= 0
DISABLE_TROPIC ?= 1
TREZOR_MODEL ?= T2T1
TREZOR_MEMPERF ?= 0
ADDRESS_SANITIZER ?= 0
CMAKELISTS ?= 0
PYTEST_TIMEOUT ?= 500
TEST_LANG ?= "en"
THP ?= $(if $(filter T3W1,$(TREZOR_MODEL)),1,0)
BENCHMARK ?= 0
LOG_STACK_USAGE ?= 0
TREZOR_EMULATOR_DEBUGGABLE ?= 0
QUIET_MODE ?= 0
TREZOR_DISABLE_ANIMATION ?= $(if $(filter 0,$(PYOPT)),1,0)
STORAGE_INSECURE_TESTING_MODE ?= 0
UI_DEBUG_OVERLAY ?= 0

# If set, VCP writes will be blocking, in order to allow reliable debug data transmission over VCP.
# Disabled by default, to prevent debug firmware from getting stuck while writing log messages (if the host is not reading them).
BLOCK_ON_VCP ?= 0

# OpenOCD interface default. Alternative: ftdi/olimex-arm-usb-tiny-h
OPENOCD_INTERFACE ?= stlink
# OpenOCD transport default. Alternative: jtag
OPENOCD_TRANSPORT ?= hla_swd

# Include the device-specific definitions.
include embed/models/$(TREZOR_MODEL)/config.mk

# Get bindgen macros for rust tests
TEST_BINDGEN_MACROS := $(shell tr -d '\n' < embed/models/$(TREZOR_MODEL)/test_bindgen_macros.txt)
export TEST_BINDGEN_MACROS


FLASH_START		         = $(shell layout_parser ${TREZOR_MODEL} FLASH_START)
BOARDLOADER_START        = $(shell layout_parser ${TREZOR_MODEL} BOARDLOADER_START)
BOOTLOADER_START         = $(shell layout_parser ${TREZOR_MODEL} BOOTLOADER_START)
KERNEL_START             = $(shell layout_parser ${TREZOR_MODEL} KERNEL_START)
FIRMWARE_START           = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_START)
FIRMWARE_P2_START        = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_P2_START)
STORAGE_1_START          = $(shell layout_parser ${TREZOR_MODEL} STORAGE_1_START)
STORAGE_2_START	         = $(shell layout_parser ${TREZOR_MODEL} STORAGE_2_START)
STORAGE_SIZE             = $(shell layout_parser ${TREZOR_MODEL} NORCOW_SECTOR_SIZE)
BOARDLOADER_MAXSIZE      = $(shell layout_parser ${TREZOR_MODEL} BOARDLOADER_MAXSIZE)
BOOTLOADER_MAXSIZE       = $(shell layout_parser ${TREZOR_MODEL} BOOTLOADER_MAXSIZE)
FIRMWARE_MAXSIZE         = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_MAXSIZE)
FIRMWARE_P1_MAXSIZE      = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_P1_MAXSIZE)
FIRMWARE_P2_MAXSIZE      = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_P2_MAXSIZE)
BOARDLOADER_SECTOR_START = $(shell layout_parser ${TREZOR_MODEL} BOARDLOADER_SECTOR_START)
BOARDLOADER_SECTOR_END   = $(shell layout_parser ${TREZOR_MODEL} BOARDLOADER_SECTOR_END)
BOOTLOADER_SECTOR_START  = $(shell layout_parser ${TREZOR_MODEL} BOOTLOADER_SECTOR_START)
BOOTLOADER_SECTOR_END    = $(shell layout_parser ${TREZOR_MODEL} BOOTLOADER_SECTOR_END)
FIRMWARE_SECTOR_START    = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_SECTOR_START)
FIRMWARE_SECTOR_END      = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_SECTOR_END)
FIRMWARE_P1_SECTOR_START = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_P1_SECTOR_START)
FIRMWARE_P1_SECTOR_END   = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_P1_SECTOR_END)
FIRMWARE_P2_SECTOR_START = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_P2_SECTOR_START)
FIRMWARE_P2_SECTOR_END   = $(shell layout_parser ${TREZOR_MODEL} FIRMWARE_P2_SECTOR_END)
STORAGE_1_SECTOR_START   = $(shell layout_parser ${TREZOR_MODEL} STORAGE_1_SECTOR_START)
STORAGE_1_SECTOR_END     = $(shell layout_parser ${TREZOR_MODEL} STORAGE_1_SECTOR_END)
STORAGE_2_SECTOR_START   = $(shell layout_parser ${TREZOR_MODEL} STORAGE_2_SECTOR_START)
STORAGE_2_SECTOR_END     = $(shell layout_parser ${TREZOR_MODEL} STORAGE_2_SECTOR_END)


STORAGE_1_OFFSET := $(shell expr $(STORAGE_1_START) - $(FLASH_START))
STORAGE_2_OFFSET := $(shell expr $(STORAGE_2_START) - $(FLASH_START))

OPENOCD = openocd -f interface/$(OPENOCD_INTERFACE).cfg -c "transport select $(OPENOCD_TRANSPORT)" -f $(OPENOCD_TARGET)

SCM_REVISION = '$(shell git rev-parse HEAD)'
CFLAGS += -DSCM_REVISION_INIT='{$(shell echo ${SCM_REVISION} | sed 's:\(..\):0x\1,:g')}'

TESTPATH = $(CURDIR)/../tests

EMU = $(CURDIR)/emu.py
EMU_LOG_FILE ?= $(TESTPATH)/trezor.log
EMU_TEST_ARGS = --disable-animation --headless --output=$(EMU_LOG_FILE) --temporary-profile
EMU_TEST = $(EMU) $(EMU_TEST_ARGS) -c

JUNIT_XML ?= $(TESTPATH)/junit.xml
PYTEST = pytest --junitxml=$(JUNIT_XML)
TREZOR_FIDO2_UDP_PORT = 21326
RUST_TARGET=$(shell rustc -vV | sed -n 's/host: //p')

MULTICORE ?= "auto"
RANDOM=$(shell python -c 'import random; print(random.randint(0, 1000000))')

SCONS_VARS = \
	BENCHMARK="$(BENCHMARK)" \
	BITCOIN_ONLY="$(BITCOIN_ONLY)" \
	BOOTLOADER_DEVEL="$(BOOTLOADER_DEVEL)" \
	BOOTLOADER_QA="$(BOOTLOADER_QA)" \
	UNSAFE_FW="$(UNSAFE_FW)" \
	CFLAGS="$(CFLAGS)" \
	CMAKELISTS="$(CMAKELISTS)" \
	DISABLE_OPTIGA="$(DISABLE_OPTIGA)" \
	DISABLE_TROPIC="$(DISABLE_TROPIC)" \
	HW_REVISION="$(HW_REVISION)" \
	LOG_STACK_USAGE="$(LOG_STACK_USAGE)" \
	MICROPY_ENABLE_SOURCE_LINE="$(MICROPY_ENABLE_SOURCE_LINE)" \
	PRODUCTION="$(PRODUCTION)" \
	PYOPT="$(PYOPT)" \
	QUIET_MODE="$(QUIET_MODE)" \
	SCM_REVISION="$(SCM_REVISION)" \
	STORAGE_INSECURE_TESTING_MODE="$(STORAGE_INSECURE_TESTING_MODE)" \
	THP="$(THP)" \
	TREZOR_DISABLE_ANIMATION="$(TREZOR_DISABLE_ANIMATION)" \
	TREZOR_EMULATOR_ASAN="$(ADDRESS_SANITIZER)" \
	TREZOR_EMULATOR_DEBUGGABLE=$(TREZOR_EMULATOR_DEBUGGABLE) \
	TREZOR_MEMPERF="$(TREZOR_MEMPERF)" \
	TREZOR_MODEL="$(TREZOR_MODEL)" \
	UI_DEBUG_OVERLAY="$(UI_DEBUG_OVERLAY)" \
	BLOCK_ON_VCP="$(BLOCK_ON_VCP)"

SCONS_OPTS = -Q -j $(JOBS)
ifeq ($(QUIET_MODE),1)
SCONS_OPTS += --quiet
endif

SCONS = scons $(SCONS_OPTS) $(SCONS_VARS)

## help commands:

help: ## show this help
	@awk -f ../tools/help.awk $(MAKEFILE_LIST)

## dependencies commands:

vendor: ## update git submodules
	git submodule update --init --recursive --force

## emulator commands:

run: ## run unix port
	cd src ; ../$(UNIX_BUILD_DIR)/trezor-emu-core

emu: ## run emulator
	$(EMU)

## test commands:

test: ## run unit tests
	cd tests ; ./run_tests.sh $(TESTOPTS)

test_rust: ## run rs unit tests
	export BUILD_DIR=$(abspath $(UNIX_BUILD_DIR)) ; \
	cd embed/rust ; cargo test $(TESTOPTS) --target=$(RUST_TARGET) \
		--no-default-features --features $(LAYOUT_FEATURE),power_manager,test \
		-- --test-threads=1 --nocapture

test_emu_sanity: ## make sure the emulator doesn't crash on startup
	$(EMU) --disable-animation --headless --temporary-profile --command true

test_emu: ## run selected device tests from python-trezor
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/device_tests $(TESTOPTS) --lang=$(TEST_LANG)

test_emu_multicore: ## run device tests using multiple cores
	$(PYTEST) -n $(MULTICORE) $(TESTPATH)/device_tests $(TESTOPTS) --timeout $(PYTEST_TIMEOUT) \
		--control-emulators --model=core --random-order-seed=$(RANDOM) \
		--lang=$(TEST_LANG)

test_emu_monero: ## run selected monero device tests from monero-agent
	cd tests ; $(EMU_TEST) ./run_tests_device_emu_monero.sh $(TESTOPTS)

test_emu_u2f: ## run selected u2f device tests from u2f-tests-hid
	$(EMU_TEST) --slip0014 $(TESTPATH)/fido_tests/u2f-tests-hid/HIDTest $(TREZOR_FIDO2_UDP_PORT) $(TESTOPTS)
	$(EMU_TEST) --slip0014 $(TESTPATH)/fido_tests/u2f-tests-hid/U2FTest $(TREZOR_FIDO2_UDP_PORT) $(TESTOPTS)

test_emu_fido2: ## run fido2 device tests
	cd $(TESTPATH)/fido_tests/fido2 ; \
		$(EMU_TEST) --slip0014 $(PYTEST) --maxfail=5 --sim tests/standard/ --vendor trezor $(TESTOPTS)

test_emu_click: ## run click tests
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/click_tests $(TESTOPTS) --lang=$(TEST_LANG)

test_emu_click_ui: ## run click tests with UI testing
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/click_tests $(TESTOPTS) \
		--ui=test --ui-check-missing --do-master-diff --lang=$(TEST_LANG)

test_emu_click_ui_multicore: ## run click tests with UI testing using multiple cores
	$(PYTEST) -n $(MULTICORE) $(TESTPATH)/click_tests $(TESTOPTS) --timeout $(PYTEST_TIMEOUT) \
		--ui=test --ui-check-missing --do-master-diff --lang=$(TEST_LANG) \
		--control-emulators --model=core --random-order-seed=$(RANDOM)

test_emu_persistence: ## run persistence tests
	$(PYTEST) $(TESTPATH)/persistence_tests $(TESTOPTS) --lang=$(TEST_LANG)

test_emu_persistence_ui: ## run persistence tests with UI testing
	$(PYTEST) $(TESTPATH)/persistence_tests $(TESTOPTS) \
		--ui=test --ui-check-missing --do-master-diff --lang=$(TEST_LANG)

test_emu_ui: ## run ui integration tests
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/device_tests $(TESTOPTS) \
		--ui=test --ui-check-missing --do-master-diff \
		--lang=$(TEST_LANG)

test_emu_ui_multicore: ## run ui integration tests using multiple cores
	$(PYTEST) -n $(MULTICORE) $(TESTPATH)/device_tests $(TESTOPTS) --timeout $(PYTEST_TIMEOUT) \
		--ui=test --ui-check-missing --do-master-diff \
		--control-emulators --model=core --random-order-seed=$(RANDOM) \
		--lang=$(TEST_LANG)

test_emu_ui_record: ## record and hash screens for ui integration tests
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/device_tests $(TESTOPTS) \
		--ui=record --ui-check-missing --do-master-diff --lang=$(TEST_LANG)

test_emu_ui_record_multicore: ## quickly record all screens
	make test_emu_ui_multicore || echo "All errors are recorded in fixtures.json"
	../tests/update_fixtures.py local --remove-missing

pylint: ## run pylint on application sources and tests
	pylint -E $(shell find src tests -name *.py)

mypy: ## deprecated; use "make typecheck"
	@echo "mypy is deprecated; use 'make typecheck'"
	make typecheck

typecheck: pyright

pyright:
	python ../tools/pyright_tool.py

clippy:
	export BUILD_DIR=$(abspath $(UNIX_BUILD_DIR)) ; \
	cd embed/rust ; cargo clippy $(TESTOPTS) --all-features --target=$(RUST_TARGET)

## code generation:

templates: translations ## render Mako templates (for lists of coins, tokens, etc.)
	./tools/build_templates

templates_check: translations_check ## check that Mako-rendered files match their templates
	./tools/build_templates --check

translations: ## update translations
	python ./translations/order.py
	python ./translations/cli.py gen

translations_check: ## check that translations are up to date
	python ./translations/order.py --check
	python ./translations/cli.py gen --check
	# spits out error if the stored merkle root is not up to date
	python ./translations/cli.py merkle-root > /dev/null

translations_crowdin_push: translations  ## split translations and push to crowdin
	## prepare source files from joint `en.json` into split `en_<layout_type>.json`
	cd translations; python crowdin.py split
	cd translations; crowdin push sources

translations_crowdin_pull: ## pull translations from crowdin
	cd translations; crowdin pull --skip-untranslated-strings
	# prepare joint `<lang>.json` from split `<lang>_<layout_type>.json`
	cd translations; python crowdin.py merge

## build commands:

build: build_boardloader build_bootloader build_firmware build_prodtest build_unix ## build all

build_embed: build_boardloader build_bootloader build_firmware # build boardloader, bootloader, firmware

build_boardloader: ## build boardloader
	$(SCONS) $(BOARDLOADER_BUILD_DIR)/boardloader.bin

build_bootloader: ## build bootloader
	$(SCONS) $(BOOTLOADER_BUILD_DIR)/bootloader.bin

build_bootloader_ci: ## build CI device testing bootloader
	$(SCONS) $(BOOTLOADER_CI_BUILD_DIR)/bootloader.bin

build_bootloader_emu: ## build the unix bootloader emulator
	$(SCONS) $(BOOTLOADER_EMU_BUILD_DIR)/bootloader.elf

build_bootloader_emu_debug: ## build the unix bootloader emulator
	$(SCONS) TREZOR_EMULATOR_DEBUGGABLE=1 $(BOOTLOADER_EMU_BUILD_DIR)/bootloader.elf

build_prodtest: ## build production test firmware
	$(SCONS) $(PRODTEST_BUILD_DIR)/prodtest.bin

build_prodtest_emu: ## build the unix prodtest emulator
	$(SCONS) $(PRODTEST_EMU_BUILD_DIR)/prodtest.elf

build_reflash: ## build reflash firmware + reflash image
	$(SCONS) $(REFLASH_BUILD_DIR)/reflash.bin
	dd if=build/boardloader/boardloader.bin of=$(REFLASH_BUILD_DIR)/sdimage.bin bs=1 seek=0
	dd if=build/bootloader/bootloader.bin of=$(REFLASH_BUILD_DIR)/sdimage.bin bs=1 seek=49152

build_secmon: ## build security monitor image
	$(SCONS) $(SECMON_BUILD_DIR)/secmon.bin

build_kernel: ## build kernel image
	$(SCONS) $(KERNEL_BUILD_DIR)/kernel.bin

build_firmware: MICROPY_ENABLE_SOURCE_LINE ?= 0
build_firmware: templates build_cross $(if $(or $(filter 1,$(PRODUCTION)),$(filter 1,$(UNSAFE_FW))),,build_secmon) build_kernel ## build firmware with frozen modules
	$(SCONS) $(FIRMWARE_BUILD_DIR)/firmware.bin

build_unix: MICROPY_ENABLE_SOURCE_LINE ?= 1
build_unix: templates ## build unix port
	$(SCONS) PYOPT=0 $(UNIX_BUILD_DIR)/trezor-emu-core $(UNIX_PORT_OPTS)

build_unix_frozen: MICROPY_ENABLE_SOURCE_LINE ?= 1
build_unix_frozen: templates build_cross ## build unix port with frozen modules
	$(SCONS) $(UNIX_BUILD_DIR)/trezor-emu-core $(UNIX_PORT_OPTS) TREZOR_EMULATOR_FROZEN=1

build_unix_debug: MICROPY_ENABLE_SOURCE_LINE ?= 1
build_unix_debug: templates ## build unix port
	$(SCONS) --max-drift=1 $(UNIX_BUILD_DIR)/trezor-emu-core $(UNIX_PORT_OPTS) \
		TREZOR_EMULATOR_ASAN=1 TREZOR_EMULATOR_DEBUGGABLE=1

build_cross: ## build mpy-cross port
	INC=-I$(CURDIR)/embed/upymod/mpycross_include/ \
		$(MAKE) -C vendor/micropython/mpy-cross $(CROSS_PORT_OPTS) \
		CFLAGS_EXTRA=-DMICROPY_ENABLE_SOURCE_LINE=$(MICROPY_ENABLE_SOURCE_LINE)

## clean commands:

clean: clean_boardloader clean_bootloader clean_bootloader_emu clean_bootloader_ci \
	clean_prodtest clean_reflash clean_firmware clean_kernel clean_secmon clean_unix clean_cross ## clean all
	rm -f ".sconsign.dblite"

clean_boardloader: ## clean boardloader build
	rm -rf $(BOARDLOADER_BUILD_DIR)

clean_bootloader: ## clean bootloader build
	rm -rf $(BOOTLOADER_BUILD_DIR)

clean_bootloader_ci: ## clean bootloader_ci build
	rm -rf $(BOOTLOADER_CI_BUILD_DIR)

clean_bootloader_emu: ## clean bootloader_emu build
	rm -rf $(BOOTLOADER_EMU_BUILD_DIR)

clean_prodtest: ## clean prodtest build
	rm -rf $(PRODTEST_BUILD_DIR)

clean_reflash: ## clean reflash build
	rm -rf $(REFLASH_BUILD_DIR)

clean_secmon: ## clean security monitor build
	rm -rf $(SECMON_BUILD_DIR)

clean_kernel: ## clean kernel build
	rm -rf $(KERNEL_BUILD_DIR)

clean_firmware: ## clean firmware build
	rm -rf $(FIRMWARE_BUILD_DIR) $(RUST_BUILD_DIR)

clean_unix: ## clean unix build
	rm -rf $(UNIX_BUILD_DIR) $(RUST_BUILD_DIR)

clean_cross: ## clean mpy-cross build
	$(MAKE) -C vendor/micropython/mpy-cross clean $(CROSS_PORT_OPTS)

## flash commands:

flash: flash_boardloader flash_bootloader flash_firmware ## flash everything using OpenOCD

flash_boardloader: $(BOARDLOADER_BUILD_DIR)/boardloader.bin ## flash boardloader using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOARDLOADER_START); exit"

flash_bootloader: $(BOOTLOADER_BUILD_DIR)/bootloader.bin ## flash bootloader using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOOTLOADER_START); exit"

flash_bootloader_ci: $(BOOTLOADER_CI_BUILD_DIR)/bootloader.bin ## flash CI bootloader using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOOTLOADER_START); exit"

flash_prodtest: $(PRODTEST_BUILD_DIR)/prodtest.bin ## flash prodtest using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(FIRMWARE_START); exit"

flash_firmware: $(FIRMWARE_BUILD_DIR)/firmware.bin ## flash firmware using OpenOCD
ifeq ($(MCU),$(filter $(MCU),STM32F4))
	$(OPENOCD) -c "init; reset halt; flash write_image erase $<.p1 $(FIRMWARE_START); flash write_image erase $<.p2 $(FIRMWARE_P2_START); exit"

else
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(FIRMWARE_START); exit"
endif

flash_combine: $(PRODTEST_BUILD_DIR)/combined.bin ## flash combined using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOARDLOADER_START); exit"

flash_erase: ## erase all sectors in flash bank 0
	$(OPENOCD) -c "init; reset halt; flash info 0; flash erase_sector 0 0 last; flash erase_check 0; exit"

flash_erase_bootloader: ## erase bootloader
	$(OPENOCD) -c "init; reset halt; flash info 0; flash erase_sector 0 $(BOOTLOADER_SECTOR_START) $(BOOTLOADER_SECTOR_END); exit"

flash_erase_firmware: ## erase bootloader
ifeq ($(MCU),$(filter $(MCU),STM32F4))
	$(OPENOCD) -c "init; reset halt; flash info 0; flash erase_sector 0 $(FIRMWARE_P1_SECTOR_START) $(FIRMWARE_P1_SECTOR_END);  flash erase_sector 0 $(FIRMWARE_P2_SECTOR_START) $(FIRMWARE_P2_SECTOR_END); exit"

else
	$(OPENOCD) -c "init; reset halt; flash info 0; flash erase_sector 0 $(FIRMWARE_SECTOR_START) $(FIRMWARE_SECTOR_END); exit"
endif

flash_read_storage: ## read storage sectors from flash
	$(OPENOCD) -c "init; reset halt; flash read_bank 0 storage1.data $(STORAGE_1_OFFSET) $(STORAGE_SIZE); flash read_bank 0 storage2.data $(STORAGE_2_OFFSET) $(STORAGE_SIZE); exit"

flash_erase_storage: ## erase storage sectors from flash
	$(OPENOCD) -c "init; reset halt; flash erase_sector 0 $(STORAGE_1_SECTOR_START) $(STORAGE_1_SECTOR_END); flash erase_sector 0 $(STORAGE_2_SECTOR_START) $(STORAGE_2_SECTOR_END); exit"

flash_bootloader_jlink: $(BOOTLOADER_BUILD_DIR)/bootloader.bin ## flash bootloader using JLink
	JLinkExe -nogui 1 -commanderscript embed/projects/bootloader/bootloader_flash.jlink

flash_bootloader_ci_jlink: $(BOOTLOADER_CI_BUILD_DIR)/bootloader.bin ## flash CI bootloader using JLink
	JLinkExe -nogui 1 -commanderscript embed/projects/bootloader_ci/bootloader_flash.jlink

flash_firmware_jlink: $(FIRMWARE_BUILD_DIR)/firmware.bin ## flash firmware using JLink. file names must end in .bin for JLink
	cp -f $<.p1 $<.p1.bin
	cp -f $<.p2 $<.p2.bin
	## pad 2nd part so that FW integrity works after flash
	## read&compare in flashing will avoid erasing unmodified sectors
	truncate -s $(FIRMWARE_P2_MAXSIZE) $<.p2.bin
	JLinkExe -nogui 1 -commanderscript embed/projects/firmware/firmware_flash.jlink

## openocd debug commands:

openocd: ## start openocd which connects to the device
	$(OPENOCD)

openocd_reset: ## cause a system reset using OpenOCD
	$(OPENOCD) -c "init; reset; exit"

GDB = arm-none-eabi-gdb --nx -ex 'set remotetimeout unlimited' -ex 'set confirm off' -ex 'target remote 127.0.0.1:3333' -ex 'monitor reset halt'

gdb_boardloader: $(BOARDLOADER_BUILD_DIR)/boardloader.elf ## start remote gdb session to openocd with boardloader symbols
	$(GDB) $<

gdb_bootloader: $(BOOTLOADER_BUILD_DIR)/bootloader.elf ## start remote gdb session to openocd with bootloader symbols
	$(GDB) $<

gdb_prodtest: $(PRODTEST_BUILD_DIR)/prodtest.elf ## start remote gdb session to openocd with prodtest symbols
	$(GDB) $<

gdb_firmware: $(FIRMWARE_BUILD_DIR)/firmware.elf ## start remote gdb session to openocd with firmware symbols
	$(GDB) $<

## misc commands:

binctl: ## print info about binary files
	./tools/headertool.py $(BOOTLOADER_BUILD_DIR)/bootloader.bin
	./tools/headertool.py $(FIRMWARE_BUILD_DIR)/firmware.bin

bloaty: ## run bloaty size profiler
	bloaty -d symbols -n 0 -s file $(FIRMWARE_BUILD_DIR)/firmware.elf | less
	bloaty -d compileunits -n 0 -s file $(FIRMWARE_BUILD_DIR)/firmware.elf | less

ifeq  ($(MCU),$(filter $(MCU),STM32F4))
sizecheck: ## check sizes of binary files
	test "$(BOARDLOADER_MAXSIZE)" -ge "$(shell wc -c < $(BOARDLOADER_BUILD_DIR)/boardloader.bin)"
	test "$(BOOTLOADER_MAXSIZE)" -ge "$(shell wc -c < $(BOOTLOADER_BUILD_DIR)/bootloader.bin)"
	test "$(FIRMWARE_P1_MAXSIZE)" -ge "$(shell wc -c < $(FIRMWARE_BUILD_DIR)/firmware.bin.p1)"
	test "$(FIRMWARE_P2_MAXSIZE)" -ge "$(shell wc -c < $(FIRMWARE_BUILD_DIR)/firmware.bin.p2)"
	test "$(FIRMWARE_MAXSIZE)" -ge "$(shell wc -c < $(FIRMWARE_BUILD_DIR)/firmware.bin)"
else ifeq ($(MCU),$(filter $(MCU),STM32U5))
sizecheck: ## check sizes of binary files
	test "$(BOARDLOADER_MAXSIZE)" -ge "$(shell wc -c < $(BOARDLOADER_BUILD_DIR)/boardloader.bin)"
	test "$(BOOTLOADER_MAXSIZE)" -ge "$(shell wc -c < $(BOOTLOADER_BUILD_DIR)/bootloader.bin)"
	test "$(FIRMWARE_MAXSIZE)" -ge "$(shell wc -c < $(FIRMWARE_BUILD_DIR)/firmware.bin)"
endif

combine: ## combine boardloader + bootloader + prodtest into one combined image
	combine_firmware \
		$(TREZOR_MODEL) \
		$(PRODTEST_BUILD_DIR)/combined.bin \
		-b BOARDLOADER $(BOARDLOADER_BUILD_DIR)/boardloader.bin \
		-b BOOTLOADER $(BOOTLOADER_BUILD_DIR)/bootloader.bin \
		-b FIRMWARE $(PRODTEST_BUILD_DIR)/prodtest.bin

ifeq  ($(MCU),$(filter $(MCU),STM32F4))
combine_fw: ## combine boardloader + bootloader + firmware into one combined image
	combine_firmware \
		$(TREZOR_MODEL) \
		$(PRODTEST_BUILD_DIR)/combined.bin \
		-b BOARDLOADER $(BOARDLOADER_BUILD_DIR)/boardloader.bin \
		-b BOOTLOADER $(BOOTLOADER_BUILD_DIR)/bootloader.bin \
		-b FIRMWARE $(FIRMWARE_BUILD_DIR)/firmware.bin.p1 \
		-b FIRMWARE_P2 $(FIRMWARE_BUILD_DIR)/firmware.bin.p2
else ifeq ($(MCU),$(filter $(MCU),STM32U5))
combine_fw: ## combine boardloader + bootloader + firmware into one combined image
	combine_firmware \
		$(TREZOR_MODEL) \
		$(PRODTEST_BUILD_DIR)/combined.bin \
		-b BOARDLOADER $(BOARDLOADER_BUILD_DIR)/boardloader.bin \
		-b BOOTLOADER $(BOOTLOADER_BUILD_DIR)/bootloader.bin \
		-b FIRMWARE $(FIRMWARE_BUILD_DIR)/firmware.bin
endif

combine_to_hex: ## convert combined image to hex format
	arm-none-eabi-objcopy \
		-I binary -O ihex \
		--change-section-address .data=$(BOARDLOADER_START) \
		$(PRODTEST_BUILD_DIR)/combined.bin $(PRODTEST_BUILD_DIR)/combined.hex

upload: ## upload firmware using trezorctl
	trezorctl firmware_update -s -f $(FIRMWARE_BUILD_DIR)/firmware.bin

upload_prodtest: ## upload prodtest using trezorctl
	trezorctl firmware_update -s -f $(PRODTEST_BUILD_DIR)/prodtest.bin

coverage:  ## generate coverage report
	./tools/coverage-report
	./tools/coverage-annotate.py $(shell find . -name '.coverage*.json*') > htmlcov/hits.md

unused:  ## find unused micropython code
	vulture src src/_vulture_ignore.txt --exclude "messages.py,*/enums/*"


.PHONY: templates translations templates_check translations_check
