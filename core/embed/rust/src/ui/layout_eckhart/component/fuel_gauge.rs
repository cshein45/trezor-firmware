use crate::{
    trezorhal::power_manager::{self, ChargingState},
    ui::{
        component::{Component, Event, EventCtx, Never},
        display::{Color, Font, Icon},
        geometry::{Alignment, Alignment2D, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

#[cfg(feature = "micropython")]
use crate::ui::{component::Timer, util::animation_disabled};

use super::super::{
    fonts,
    theme::{
        GREY_LIGHT, ICON_BATTERY_EMPTY, ICON_BATTERY_FULL, ICON_BATTERY_LOW, ICON_BATTERY_MID,
        ICON_BATTERY_ZAP, RED, YELLOW,
    },
};

#[cfg(feature = "micropython")]
use super::super::theme::firmware::FUEL_GAUGE_DURATION;

/// Component for showing a small fuel gauge (battery status) consisting of:
/// - icon indicating charging or discharging state
/// - percentage
#[derive(Clone)]
pub struct FuelGauge {
    /// Area where the fuel gauge is rendered
    area: Rect,
    /// Alignment of the fuel gauge within its area
    alignment: Alignment,
    /// Mode of the fuel gauge (Always or OnChrgStatusChange)
    mode: FuelGaugeMode,
    /// State of battery charging
    charging_state: ChargingState,
    /// State of charge (0-100) [%]
    soc: Option<u8>,
    /// Font used for the soc percentage
    font: Font,
}

#[derive(Clone)]
pub enum FuelGaugeMode {
    /// Always show the fuel gauge
    Always,
    /// Show the fuel gauge only when charging state changes
    #[cfg(feature = "micropython")]
    OnChargingChange(Timer),
    /// Show the fuel gauge when charging state changes or when attached
    #[cfg(feature = "micropython")]
    OnChargingChangeOrAttach(Timer),
}

impl FuelGauge {
    pub const fn always() -> Self {
        Self::new(FuelGaugeMode::Always)
    }

    #[cfg(feature = "micropython")]
    pub const fn on_charging_change() -> Self {
        Self::new(FuelGaugeMode::OnChargingChange(Timer::new()))
    }

    #[cfg(feature = "micropython")]
    pub const fn on_charging_change_or_attach() -> Self {
        Self::new(FuelGaugeMode::OnChargingChangeOrAttach(Timer::new()))
    }

    pub const fn with_alignment(mut self, alignment: Alignment) -> Self {
        self.alignment = alignment;
        self
    }

    pub const fn with_font(mut self, font: Font) -> Self {
        self.font = font;
        self
    }

    pub fn update_pm_state(&mut self) {
        self.soc = Some(power_manager::soc());
        self.charging_state = power_manager::charging_state();
    }

    pub fn should_be_shown(&self) -> bool {
        match &self.mode {
            FuelGaugeMode::Always => true,
            #[cfg(feature = "micropython")]
            FuelGaugeMode::OnChargingChange(timer)
            | FuelGaugeMode::OnChargingChangeOrAttach(timer) => timer.is_running(),
        }
    }

    const fn new(mode: FuelGaugeMode) -> Self {
        #[cfg(feature = "micropython")]
        let font = fonts::FONT_SATOSHI_REGULAR_22;
        #[cfg(not(feature = "micropython"))]
        let font = fonts::FONT_SATOSHI_MEDIUM_26;
        Self {
            area: Rect::zero(),
            alignment: Alignment::Start,
            mode,
            charging_state: ChargingState::Idle,
            soc: None,
            font,
        }
    }

    /// Returns the icon, color for the icon, and color for the text based on
    /// the charging state and state of charge (soc).
    fn battery_indication(&self, charging_state: ChargingState, soc: u8) -> (Icon, Color, Color) {
        const SOC_THRESHOLD_FULL: u8 = 80;
        const SOC_THRESHOLD_MID: u8 = 25;
        const SOC_THRESHOLD_LOW: u8 = 9;
        match charging_state {
            ChargingState::Charging => (ICON_BATTERY_ZAP, YELLOW, GREY_LIGHT),
            ChargingState::Discharging | ChargingState::Idle => {
                if soc > SOC_THRESHOLD_FULL {
                    (ICON_BATTERY_FULL, GREY_LIGHT, GREY_LIGHT)
                } else if soc > SOC_THRESHOLD_MID {
                    (ICON_BATTERY_MID, GREY_LIGHT, GREY_LIGHT)
                } else if soc > SOC_THRESHOLD_LOW {
                    (ICON_BATTERY_LOW, YELLOW, GREY_LIGHT)
                } else {
                    (ICON_BATTERY_EMPTY, RED, RED)
                }
            }
        }
    }
}

impl Component for FuelGauge {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Attach(_) => {
                if self.soc.is_none() {
                    self.update_pm_state();
                }
                #[cfg(feature = "micropython")]
                if let FuelGaugeMode::OnChargingChangeOrAttach(timer) = &mut self.mode {
                    if !animation_disabled() {
                        timer.start(ctx, FUEL_GAUGE_DURATION.into());
                    }
                }
                ctx.request_paint();
            }
            Event::PM(_e) => {
                self.update_pm_state();
                match &mut self.mode {
                    FuelGaugeMode::Always => {
                        ctx.request_paint();
                    }
                    #[cfg(feature = "micropython")]
                    FuelGaugeMode::OnChargingChange(timer)
                    | FuelGaugeMode::OnChargingChangeOrAttach(timer) => {
                        if _e.charging_status_changed {
                            timer.start(ctx, FUEL_GAUGE_DURATION.into());
                            ctx.request_paint();
                        }
                    }
                }
            }
            #[cfg(feature = "micropython")]
            Event::Timer(_) => match &mut self.mode {
                FuelGaugeMode::OnChargingChange(timer)
                | FuelGaugeMode::OnChargingChangeOrAttach(timer) => {
                    if timer.expire(event) {
                        ctx.request_paint();
                    }
                }
                _ => {}
            },
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        const ICON_PERCENT_GAP: i16 = 16;

        let soc = self.soc.unwrap_or(0);
        let (icon, color_icon, color_text) = self.battery_indication(self.charging_state, soc);
        let soc_percent_fmt = if self.soc.is_none() {
            uformat!("?")
        } else {
            uformat!("{} %", soc)
        };
        let text_width = self.font.text_width(&soc_percent_fmt);
        let text_height = self.font.text_height();
        let icon_width = icon.toif.width();
        let icon_height = icon.toif.height();

        let (point, alignment) = match self.alignment {
            Alignment::Start => (self.area.left_center(), Alignment2D::CENTER_LEFT),
            Alignment::End => (self.area.right_center(), Alignment2D::CENTER_RIGHT),
            Alignment::Center => (self.area.center(), Alignment2D::CENTER),
        };

        let area = Rect::snap(
            point,
            Offset::new(
                icon_width + ICON_PERCENT_GAP + text_width,
                text_height.max(icon_height),
            ),
            alignment,
        );
        let text_y_coord = self.font.vert_center(area.y0, area.y1, &soc_percent_fmt);

        shape::ToifImage::new(area.left_center(), icon.toif)
            .with_fg(color_icon)
            .with_align(Alignment2D::CENTER_LEFT)
            .render(target);

        shape::Text::new(
            Point::new(area.x1, text_y_coord),
            &soc_percent_fmt,
            self.font,
        )
        .with_fg(color_text)
        .with_align(Alignment::End)
        .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for FuelGauge {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("FuelGauge");
        t.int("soc", self.soc.unwrap_or(0) as i64);
    }
}
