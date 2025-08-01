use super::super::{
    component::{ButtonStyle, ButtonStyleSheet, ResultStyle},
    fonts,
    theme::{BLACK, FG, GREY_DARK, GREY_LIGHT, WHITE},
};
use crate::ui::{
    component::{text::TextStyle, LineBreaking::BreakWordsNoHyphen},
    constant::{HEIGHT, WIDTH},
    display::Color,
    geometry::{Offset, Point, Rect},
    util::include_res,
};

use super::GREY_MEDIUM;

pub const BLD_BG: Color = Color::rgb(0x00, 0x1E, 0xAD);
pub const BLD_FG: Color = WHITE;
pub const BLD_WIPE_COLOR: Color = Color::rgb(0xE7, 0x0E, 0x0E);
pub const BLD_WIPE_TEXT_COLOR: Color = WHITE;

pub const BLD_WARN_COLOR: Color = Color::rgb(0xFF, 0x00, 0x00);

pub const BLD_WIPE_BTN_COLOR: Color = WHITE;
pub const BLD_WIPE_BTN_COLOR_ACTIVE: Color = Color::rgb(0xFA, 0xCF, 0xCF);

pub const BLD_WIPE_CANCEL_BTN_COLOR: Color = Color::rgb(0xFF, 0x41, 0x41);
pub const BLD_WIPE_CANCEL_BTN_COLOR_ACTIVE: Color = Color::rgb(0xAE, 0x09, 0x09);

pub const BLD_INSTALL_BTN_COLOR_ACTIVE: Color = Color::rgb(0xCD, 0xD2, 0xEF);

pub const BLD_BTN_COLOR: Color = Color::rgb(0x2D, 0x42, 0xBF);
pub const BLD_BTN_COLOR_ACTIVE: Color = Color::rgb(0x04, 0x10, 0x58);

pub const BLD_BTN_INITIAL_COLOR: Color = GREY_MEDIUM;
pub const BLD_BTN_INITIAL_ACTIVE: Color = GREY_DARK;

pub const BLD_TITLE_COLOR: Color = WHITE;

pub const WELCOME_COLOR: Color = BLACK;
pub const WELCOME_HIGHLIGHT_COLOR: Color = Color::rgb(0x28, 0x28, 0x28);

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// Commonly used constants for UI elements.
pub const CONTENT_PADDING: i16 = 6;
pub const TITLE_AREA: Rect = Rect::new(
    Point::new(CONTENT_PADDING, CONTENT_PADDING),
    Point::new(WIDTH, CORNER_BUTTON_SIZE + CONTENT_PADDING),
);

pub const CORNER_BUTTON_TOUCH_EXPANSION: i16 = 13;
pub const CORNER_BUTTON_SIZE: i16 = 44;
pub const CORNER_BUTTON_AREA: Rect = Rect::from_top_left_and_size(
    Point::new(
        WIDTH - CORNER_BUTTON_SIZE - CONTENT_PADDING,
        CONTENT_PADDING,
    ),
    Offset::uniform(CORNER_BUTTON_SIZE),
);
pub const BUTTON_AREA_START: i16 = HEIGHT - 56;
pub const BUTTON_HEIGHT: i16 = 50;

// BLD icons
pub const X24: &[u8] = include_res!("layout_bolt/res/x24.toif");
pub const X32: &[u8] = include_res!("layout_bolt/res/x32.toif");
pub const FIRE24: &[u8] = include_res!("layout_bolt/res/fire24.toif");
pub const FIRE32: &[u8] = include_res!("layout_bolt/res/fire32.toif");
pub const FIRE40: &[u8] = include_res!("layout_bolt/res/fire40.toif");
pub const REFRESH24: &[u8] = include_res!("layout_bolt/res/refresh24.toif");
pub const MENU32: &[u8] = include_res!("layout_bolt/res/menu32.toif");
pub const INFO32: &[u8] = include_res!("layout_bolt/res/info32.toif");
pub const DOWNLOAD32: &[u8] = include_res!("layout_bolt/res/download32.toif");
pub const WARNING40: &[u8] = include_res!("layout_bolt/res/warning40.toif");
pub const CHECK24: &[u8] = include_res!("layout_bolt/res/check24.toif");
pub const CHECK40: &[u8] = include_res!("layout_bolt/res/check40.toif");

pub const DEVICE_NAME: &[u8] = include_res!("layout_bolt/res/device_name_T.toif");
pub const START_URL: &[u8] = include_res!("layout_bolt/res/start.toif");

pub fn button_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: BLD_BG,
            button_color: WHITE,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: BLD_BG,
            button_color: BLD_INSTALL_BTN_COLOR_ACTIVE,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: FG,
            button_color: GREY_DARK,
            background_color: FG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub fn button_wipe_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: WHITE,
            button_color: BLD_WIPE_CANCEL_BTN_COLOR,
            background_color: BLD_WIPE_COLOR,
            border_color: BLD_WIPE_COLOR,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: WHITE,
            button_color: BLD_WIPE_CANCEL_BTN_COLOR_ACTIVE,
            background_color: BLD_WIPE_COLOR,
            border_color: BLD_WIPE_COLOR,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            background_color: WHITE,
            border_color: WHITE,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub fn button_wipe_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: BLD_WIPE_COLOR,
            button_color: BLD_WIPE_BTN_COLOR,
            background_color: BLD_WIPE_COLOR,
            border_color: BLD_WIPE_COLOR,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: BLD_WIPE_COLOR,
            button_color: BLD_WIPE_BTN_COLOR_ACTIVE,
            background_color: BLD_WIPE_COLOR,
            border_color: BLD_WIPE_COLOR,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: FG,
            button_color: GREY_DARK,
            background_color: FG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub fn button_bld_menu() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: BLD_FG,
            button_color: BLD_BG,
            background_color: BLD_BG,
            border_color: BLD_BTN_COLOR,
            border_radius: 2,
            border_width: 2,
        },
        active: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: BLD_FG,
            button_color: BLD_BG,
            background_color: BLD_BG,
            border_color: BLD_BTN_COLOR_ACTIVE,
            border_radius: 2,
            border_width: 2,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: GREY_LIGHT,
            button_color: BLD_BG,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 2,
            border_width: 2,
        },
    }
}

pub fn button_bld() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: BLD_FG,
            button_color: BLD_BTN_COLOR,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: BLD_FG,
            button_color: BLD_BTN_COLOR_ACTIVE,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: GREY_LIGHT,
            button_color: BLD_BTN_COLOR,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
    }
}

pub fn button_confirm_initial() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: WELCOME_COLOR,
            button_color: WHITE,
            background_color: WELCOME_COLOR,
            border_color: WELCOME_COLOR,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: WELCOME_COLOR,
            button_color: GREY_LIGHT,
            background_color: WELCOME_COLOR,
            border_color: WELCOME_COLOR,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: FG,
            button_color: GREY_DARK,
            background_color: FG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub fn button_initial() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: WHITE,
            button_color: BLD_BTN_INITIAL_COLOR,
            background_color: WELCOME_COLOR,
            border_color: WELCOME_COLOR,
            border_radius: 4,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: WHITE,
            button_color: BLD_BTN_INITIAL_ACTIVE,
            background_color: WELCOME_COLOR,
            border_color: WELCOME_COLOR,
            border_radius: 4,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_BOLD_UPPER,
            text_color: GREY_LIGHT,
            button_color: BLD_BTN_COLOR,
            background_color: WELCOME_COLOR,
            border_color: WELCOME_COLOR,
            border_radius: 4,
            border_width: 0,
        },
    }
}

pub const fn text_title(bg: Color) -> TextStyle {
    TextStyle::new(
        fonts::FONT_BOLD_UPPER,
        BLD_TITLE_COLOR,
        bg,
        BLD_TITLE_COLOR,
        BLD_TITLE_COLOR,
    )
}

pub const TEXT_NORMAL: TextStyle =
    TextStyle::new(fonts::FONT_NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_WARNING: TextStyle = TextStyle::new(
    fonts::FONT_BOLD_UPPER,
    BLD_WARN_COLOR,
    BLD_BG,
    BLD_WARN_COLOR,
    BLD_WARN_COLOR,
);
pub const fn text_fingerprint(bg: Color) -> TextStyle {
    TextStyle::new(fonts::FONT_NORMAL, BLD_FG, bg, BLD_FG, BLD_FG)
        .with_line_breaking(BreakWordsNoHyphen)
}
pub const TEXT_BOLD: TextStyle =
    TextStyle::new(fonts::FONT_BOLD_UPPER, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_WIPE_BOLD: TextStyle = TextStyle::new(
    fonts::FONT_BOLD_UPPER,
    BLD_WIPE_TEXT_COLOR,
    BLD_WIPE_COLOR,
    BLD_WIPE_TEXT_COLOR,
    BLD_WIPE_TEXT_COLOR,
);
pub const TEXT_WIPE_NORMAL: TextStyle = TextStyle::new(
    fonts::FONT_NORMAL,
    BLD_WIPE_TEXT_COLOR,
    BLD_WIPE_COLOR,
    BLD_WIPE_TEXT_COLOR,
    BLD_WIPE_TEXT_COLOR,
);

pub const RESULT_WIPE: ResultStyle = ResultStyle::new(
    BLD_WIPE_TEXT_COLOR,
    BLD_WIPE_COLOR,
    BLD_WIPE_CANCEL_BTN_COLOR,
);

pub const RESULT_FW_INSTALL: ResultStyle = ResultStyle::new(BLD_FG, BLD_BG, BLD_BTN_COLOR);

pub const RESULT_INITIAL: ResultStyle =
    ResultStyle::new(FG, WELCOME_COLOR, WELCOME_HIGHLIGHT_COLOR);
