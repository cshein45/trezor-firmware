
/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once

#include <rtl/sizedefs.h>
#include "secret_layout.h"

#include "bootloaders/bootloader_hashes.h"

#define MODEL_NAME "T3W1"
#define MODEL_FULL_NAME "Trezor T3W1"
#define MODEL_INTERNAL_NAME "T3W1"
#define MODEL_INTERNAL_NAME_TOKEN T3W1
#define MODEL_INTERNAL_NAME_QSTR MP_QSTR_T3W1
#define MODEL_USB_MANUFACTURER "Trezor Company"
#define MODEL_USB_PRODUCT MODEL_FULL_NAME
#define MODEL_HOMESCREEN_MAXSIZE 65536
#define MODEL_BLE_CODE 6

#define MODEL_BOARDLOADER_KEYS \
  (const uint8_t *)"\xe8\x91\x2f\x81\xb3\xe7\x80\xee\x65\x0e\xd3\x85\x6d\xb5\x32\x6e\x0b\x9e\xff\x10\x36\x4b\x33\x91\x93\xe7\xa8\xf1\x0f\x76\x21\xb9", \
  (const uint8_t *)"\xbd\xe7\x0a\x38\xee\xe6\x33\xd2\x6f\x43\x4e\xee\x2f\x53\x6d\xf4\x57\xb8\xde\xb8\xbd\x98\x82\x94\xf4\xa0\xc8\xd9\x05\x49\x03\xd2", \
  (const uint8_t *)"\xa8\x5b\x60\x1d\xfb\xda\x1d\x22\xcc\xb5\xdd\x49\x2d\x26\x03\x4d\x87\xf6\x7f\x2a\x0b\x85\x84\xb7\x77\x44\x39\x46\x1f\xc4\x71\xa9",

#define MODEL_BOOTLOADER_KEYS \
  (const uint8_t *)"\x32\x0e\x11\x1e\x9d\xde\xd5\xfe\x7f\x5d\x41\xfd\x37\x2e\xf0\xe9\x1b\x2d\xfa\x4c\x6c\xdc\x9f\xe5\x22\x1b\xfb\x16\xaa\xf9\x17\x75", \
  (const uint8_t *)"\x2e\x34\x9f\x8d\x06\xb2\x33\x42\x62\xec\xb6\x03\xed\x04\xcb\x5a\x7c\xc0\xb6\x60\xeb\xe3\xcd\x5c\x29\x72\xb5\xcd\x1f\x38\xef\x85", \
  (const uint8_t *)"\xab\x0d\x3f\x91\xa4\xad\xf7\x44\x71\x9d\xba\x66\x17\x83\xec\x54\x9f\x73\xa4\xe4\x54\x57\xcb\x6d\x02\x75\x2a\x40\xfb\x63\xd3\xbf",

// temporary dev keys until we have production keys
#define MODEL_SECMON_KEYS \
  (const uint8_t *)"\xdb\x99\x5f\xe2\x51\x69\xd1\x41\xca\xb9\xbb\xba\x92\xba\xa0\x1f\x9f\x2e\x1e\xce\x7d\xf4\xcb\x2a\xc0\x51\x90\xf3\x7f\xcc\x1f\x9d", \
  (const uint8_t *)"\x21\x52\xf8\xd1\x9b\x79\x1d\x24\x45\x32\x42\xe1\x5f\x2e\xab\x6c\xb7\xcf\xfa\x7b\x6a\x5e\xd3\x00\x97\x96\x0e\x06\x98\x81\xdb\x12", \
  (const uint8_t *)"\x22\xfc\x29\x77\x92\xf0\xb6\xff\xc0\xbf\xcf\xdb\x7e\xdb\x0c\x0a\xa1\x4e\x02\x5a\x36\x5e\xc0\xe3\x42\xe8\x6e\x38\x29\xcb\x74\xb6",

#define IMAGE_CHUNK_SIZE SIZE_256K
#define IMAGE_HASH_SHA256

#define DISPLAY_JUMP_BEHAVIOR DISPLAY_RESET_CONTENT

#define NORCOW_SECTOR_SIZE (16 * 8 * 1024)  // 128 kB
#define NORCOW_MIN_VERSION 0x00000006

#ifdef USE_SECMON_LAYOUT
#include "memory_secmon.h"
#else
#include "memory.h"
#endif
