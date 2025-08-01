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

/// package: trezorio.__init__

/// class WebUSB:
///     """
///     USB WebUSB interface configuration.
///     """
typedef struct _mp_obj_WebUSB_t {
  mp_obj_base_t base;
  usb_webusb_info_t info;
} mp_obj_WebUSB_t;

/// def __init__(
///     self,
///     iface_num: int,
///     ep_in: int,
///     ep_out: int,
///     emu_port: int,
///     subclass: int = 0,
///     protocol: int = 0,
///     polling_interval: int = 1,
///     max_packet_len: int = 64,
/// ) -> None:
///     """
///     """
STATIC mp_obj_t mod_trezorio_WebUSB_make_new(const mp_obj_type_t *type,
                                             size_t n_args, size_t n_kw,
                                             const mp_obj_t *args) {
  STATIC const mp_arg_t allowed_args[] = {
      {MP_QSTR_iface_num,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT,
       {.u_int = 0}},
      {MP_QSTR_ep_in,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT,
       {.u_int = 0}},
      {MP_QSTR_ep_out,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT,
       {.u_int = 0}},
      {MP_QSTR_emu_port,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT,
       {.u_int = 0}},
      {MP_QSTR_subclass, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0}},
      {MP_QSTR_protocol, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0}},
      {MP_QSTR_polling_interval, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 1}},
      {MP_QSTR_max_packet_len, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 64}},
  };
  mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)] = {0};
  mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args),
                            allowed_args, vals);

  const mp_int_t iface_num = vals[0].u_int;
  const mp_int_t ep_in = vals[1].u_int;
  const mp_int_t ep_out = vals[2].u_int;
  const mp_int_t emu_port = vals[3].u_int;
  const mp_int_t subclass = vals[4].u_int;
  const mp_int_t protocol = vals[5].u_int;
  const mp_int_t polling_interval = vals[6].u_int;
  const mp_int_t max_packet_len = vals[7].u_int;

  CHECK_PARAM_RANGE(iface_num, 0, 32)
  CHECK_PARAM_RANGE(ep_in, 0, 255)
  CHECK_PARAM_RANGE(ep_out, 0, 255)
  CHECK_PARAM_RANGE(emu_port, 0, 65535)
  CHECK_PARAM_RANGE(subclass, 0, 255)
  CHECK_PARAM_RANGE(protocol, 0, 255)
  CHECK_PARAM_RANGE(polling_interval, 1, 255)
  CHECK_PARAM_RANGE(max_packet_len, 64, 64)

  mp_obj_WebUSB_t *o = mp_obj_malloc(mp_obj_WebUSB_t, type);

  o->info.rx_buffer = m_new(uint8_t, max_packet_len);
  o->info.iface_num = (uint8_t)(iface_num);
#ifdef TREZOR_EMULATOR
  o->info.emu_port = (uint16_t)(emu_port);
#else
  o->info.ep_in = (uint8_t)(ep_in);
  o->info.ep_out = (uint8_t)(ep_out);
#endif
  o->info.subclass = (uint8_t)(subclass);
  o->info.protocol = (uint8_t)(protocol);
  o->info.polling_interval = (uint8_t)(polling_interval);
  o->info.max_packet_len = (uint8_t)(max_packet_len);

  return MP_OBJ_FROM_PTR(o);
}

/// def iface_num(self) -> int:
///     """
///     Returns the configured number of this interface.
///     """
STATIC mp_obj_t mod_trezorio_WebUSB_iface_num(mp_obj_t self) {
  mp_obj_WebUSB_t *o = MP_OBJ_TO_PTR(self);
  return MP_OBJ_NEW_SMALL_INT(o->info.iface_num);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_WebUSB_iface_num_obj,
                                 mod_trezorio_WebUSB_iface_num);

/// def write(self, msg: bytes) -> int:
///     """
///     Sends message using USB WebUSB (device) or UDP (emulator).
///     """
STATIC mp_obj_t mod_trezorio_WebUSB_write(mp_obj_t self, mp_obj_t msg) {
  mp_obj_WebUSB_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t buf = {0};
  mp_get_buffer_raise(msg, &buf, MP_BUFFER_READ);

  if (buf.len != USB_PACKET_LEN) {
    mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("Invalid buffer length"));
  }

  ssize_t r = usb_webusb_write(o->info.iface_num, buf.buf, buf.len);

  if (r != buf.len) {
    mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("Write failed"));
  }

  return MP_OBJ_NEW_SMALL_INT(r);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_WebUSB_write_obj,
                                 mod_trezorio_WebUSB_write);

/// def read(self, buf: bytearray, offset: int = 0) -> int:
///     """
///     Reads message using USB WebUSB (device) or UDP (emulator).
///     """
STATIC mp_obj_t mod_trezorio_WebUSB_read(size_t n_args, const mp_obj_t *args) {
  mp_obj_WebUSB_t *o = MP_OBJ_TO_PTR(args[0]);
  mp_buffer_info_t buf = {0};
  mp_get_buffer_raise(args[1], &buf, MP_BUFFER_WRITE);

  int offset = 0;
  if (n_args >= 2) {
    offset = mp_obj_get_int(args[2]);
  }

  if (offset < 0) {
    mp_raise_ValueError(MP_ERROR_TEXT("Negative offset not allowed"));
  }

  if (offset > buf.len) {
    mp_raise_ValueError(MP_ERROR_TEXT("Offset out of bounds"));
  }

  uint32_t buffer_space = buf.len - offset;

  if (buffer_space < USB_PACKET_LEN) {
    mp_raise_ValueError(MP_ERROR_TEXT("Buffer too small"));
  }

  ssize_t r = usb_webusb_read(o->info.iface_num, &((uint8_t *)buf.buf)[offset],
                              USB_PACKET_LEN);

  if (r != USB_PACKET_LEN) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Unexpected read length"));
  }

  return MP_OBJ_NEW_SMALL_INT(r);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorio_WebUSB_read_obj, 2, 3,
                                           mod_trezorio_WebUSB_read);

/// RX_PACKET_LEN: ClassVar[int]
/// """Length of one USB RX packet."""

/// TX_PACKET_LEN: ClassVar[int]
/// """Length of one USB TX packet."""

STATIC const mp_rom_map_elem_t mod_trezorio_WebUSB_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_iface_num),
     MP_ROM_PTR(&mod_trezorio_WebUSB_iface_num_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mod_trezorio_WebUSB_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&mod_trezorio_WebUSB_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_RX_PACKET_LEN), MP_ROM_INT(USB_PACKET_LEN)},
    {MP_ROM_QSTR(MP_QSTR_TX_PACKET_LEN), MP_ROM_INT(USB_PACKET_LEN)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_WebUSB_locals_dict,
                            mod_trezorio_WebUSB_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_WebUSB_type = {
    {&mp_type_type},
    .name = MP_QSTR_WebUSB,
    .make_new = mod_trezorio_WebUSB_make_new,
    .locals_dict = (void *)&mod_trezorio_WebUSB_locals_dict,
};
