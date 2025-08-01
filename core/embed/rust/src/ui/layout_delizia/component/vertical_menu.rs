use heapless::Vec;

use crate::{
    strutil::TString,
    time::{Duration, Stopwatch},
    ui::{
        component::{
            base::{AttachType, Component},
            paginated::SinglePage,
            Event, EventCtx, Paginate,
        },
        constant::screen,
        display::{Color, Icon},
        geometry::{Direction, Offset, Rect},
        lerp::Lerp,
        shape::{Bar, Renderer},
        util::{animation_disabled, Pager},
    },
};

use super::{
    super::component::button::{Button, ButtonContent, ButtonMsg, IconText},
    theme,
};

pub enum VerticalMenuChoiceMsg {
    Selected(usize),
}

/// Number of buttons.
/// Presently, VerticalMenu holds only fixed number of buttons.
const MENU_MAX_ITEMS: usize = 3;

/// Fixed height of each menu button.
const MENU_BUTTON_HEIGHT: i16 = 64;

/// Fixed height of a separator.
const MENU_SEP_HEIGHT: i16 = 2;

type VerticalMenuButtons = Vec<Button, MENU_MAX_ITEMS>;

#[derive(Default, Clone)]
struct AttachAnimation {
    pub attach_top: bool,
    pub timer: Stopwatch,
    pub active: bool,
    pub duration: Duration,
}

impl AttachAnimation {
    fn is_active(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        self.timer.is_running_within(self.duration)
    }

    fn eval(&self) -> f32 {
        if animation_disabled() {
            return 1.0;
        }

        self.timer.elapsed().to_millis() as f32 / 1000.0
    }

    fn get_offset(&self, t: f32) -> Offset {
        let value = if self.attach_top {
            1.0
        } else {
            pareen::constant(0.0)
                .seq_ease_in(
                    0.0,
                    easer::functions::Cubic,
                    self.duration.to_millis() as f32 / 1000.0,
                    pareen::constant(1.0).eval(t),
                )
                .eval(t)
        };

        Offset::lerp(Offset::new(-40, 0), Offset::zero(), value)
    }

    fn get_mask_width(&self, t: f32) -> i16 {
        let value = if self.attach_top {
            1.0
        } else {
            pareen::constant(0.0)
                .seq_ease_in(0.0, easer::functions::Circ, 0.15, pareen::constant(1.0))
                .eval(t)
        };

        //todo screen here is incorrect
        i16::lerp(screen().width(), 0, value)
    }

    pub fn get_mask_item1_opacity(&self, t: f32) -> u8 {
        let value = if self.attach_top {
            pareen::constant(0.0)
                .seq_ease_in(0.0, easer::functions::Cubic, 0.15, pareen::constant(1.0))
                .eval(t)
        } else {
            1.0
        };

        u8::lerp(255, 0, value)
    }

    pub fn get_mask_item2_opacity(&self, t: f32) -> u8 {
        let value = if self.attach_top {
            pareen::constant(0.0)
                .seq_ease_in(0.1, easer::functions::Cubic, 0.15, pareen::constant(1.0))
                .eval(t)
        } else {
            1.0
        };

        u8::lerp(255, 0, value)
    }

    pub fn get_mask_item3_opacity(&self, t: f32) -> u8 {
        let value = if self.attach_top {
            pareen::constant(0.0)
                .seq_ease_in(0.2, easer::functions::Cubic, 0.15, pareen::constant(1.0))
                .eval(t)
        } else {
            1.0
        };

        u8::lerp(255, 0, value)
    }

    fn start(&mut self) {
        self.active = true;
        self.timer.start();
    }

    fn reset(&mut self) {
        self.active = false;
        self.timer = Stopwatch::new_stopped();
    }

    fn lazy_start(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::Attach(_) = event {
            if let Event::Attach(AttachType::Swipe(Direction::Up))
            | Event::Attach(AttachType::Swipe(Direction::Down))
            | Event::Attach(AttachType::Initial) = event
            {
                self.attach_top = true;
                self.duration = Duration::from_millis(350);
            } else {
                self.attach_top = false;
                self.duration = Duration::from_millis(350);
            }
            self.reset();
            ctx.request_anim_frame();
        }
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if !self.timer.is_running() {
                self.start();
            }
            if self.is_active() {
                ctx.request_anim_frame();
                ctx.request_paint();
            } else if self.active {
                self.active = false;
                ctx.request_anim_frame();
                ctx.request_paint();
            }
        }
    }
}

pub struct VerticalMenu {
    /// buttons placed vertically from top to bottom
    buttons: VerticalMenuButtons,
    /// length of `buttons` prefix that is currently active, set by `place()`
    n_items: usize,

    attach_animation: AttachAnimation,
}

impl VerticalMenu {
    fn new(buttons: VerticalMenuButtons) -> Self {
        Self {
            buttons,
            n_items: MENU_MAX_ITEMS,
            attach_animation: AttachAnimation::default(),
        }
    }
    pub fn select_word(words: [TString<'static>; 3]) -> Self {
        let mut buttons_vec = VerticalMenuButtons::new();
        for word in words {
            let button = Button::with_text(word).styled(theme::button_default());
            unwrap!(buttons_vec.push(button));
        }
        Self::new(buttons_vec)
    }

    pub fn empty() -> Self {
        Self::new(VerticalMenuButtons::new())
    }

    pub fn item(mut self, icon: Icon, text: TString<'static>) -> Self {
        unwrap!(self.buttons.push(
            Button::with_icon_and_text(IconText::new(text, icon)).styled(theme::button_default())
        ));
        self
    }

    pub fn danger(mut self, icon: Icon, text: TString<'static>) -> Self {
        unwrap!(self.buttons.push(
            Button::with_icon_and_text(IconText::new(text, icon))
                .styled(theme::button_warning_high())
        ));
        self
    }
}

impl Component for VerticalMenu {
    type Msg = VerticalMenuChoiceMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // VerticalMenu is supposed to be used in Frame, the remaining space is just
        // enought to fit 3 buttons separated by thin bars. If there's footer only 2
        // buttons fit.
        let n_items = (bounds.height() + MENU_SEP_HEIGHT) / (MENU_BUTTON_HEIGHT + MENU_SEP_HEIGHT);
        self.n_items = n_items as usize;

        let mut remaining = bounds;
        let n_seps = self.buttons.len() - 1;
        for (i, button) in self.buttons.iter_mut().take(self.n_items).enumerate() {
            let (area_button, new_remaining) = remaining.split_top(MENU_BUTTON_HEIGHT);
            button.place(area_button);
            remaining = new_remaining;
            if i < n_seps {
                let (_area_sep, new_remaining) = remaining.split_top(MENU_SEP_HEIGHT);
                remaining = new_remaining;
            }
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.attach_animation.lazy_start(ctx, event);

        if !self.attach_animation.is_active() {
            for (i, button) in self.buttons.iter_mut().enumerate() {
                if let Some(ButtonMsg::Clicked) = button.event(ctx, event) {
                    return Some(VerticalMenuChoiceMsg::Selected(i));
                }
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let t = self.attach_animation.eval();

        let offset = self.attach_animation.get_offset(t);
        let mask_width = self.attach_animation.get_mask_width(t);
        let item1_opacity = self.attach_animation.get_mask_item1_opacity(t);
        let item2_opacity = self.attach_animation.get_mask_item2_opacity(t);
        let item3_opacity = self.attach_animation.get_mask_item3_opacity(t);

        let opacities = [item1_opacity, item2_opacity, item3_opacity];

        target.with_translate(offset, &|target| {
            // render buttons separated by thin bars
            for (i, button) in (&self.buttons).into_iter().take(self.n_items).enumerate() {
                button.render(target);

                Bar::new(button.area())
                    .with_fg(Color::black())
                    .with_bg(Color::black())
                    .with_alpha(opacities[i])
                    .render(target);

                if i + 1 < self.buttons.len().min(self.n_items) {
                    let area = button
                        .area()
                        .translate(Offset::y(MENU_BUTTON_HEIGHT))
                        .with_height(MENU_SEP_HEIGHT);
                    Bar::new(area)
                        .with_thickness(MENU_SEP_HEIGHT)
                        .with_fg(theme::GREY_EXTRA_DARK)
                        .render(target);
                    Bar::new(area)
                        .with_fg(Color::black())
                        .with_bg(Color::black())
                        .with_alpha(opacities[i])
                        .render(target);
                }
            }

            // todo screen here is incorrect
            let r = Rect::from_size(Offset::new(mask_width, screen().height()));

            Bar::new(r)
                .with_fg(Color::black())
                .with_bg(Color::black())
                .render(target);
        });
    }
}

impl SinglePage for VerticalMenu {}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for VerticalMenu {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("VerticalMenu");
        t.in_list("buttons", &|button_list| {
            for button in &self.buttons {
                button_list.child(button);
            }
        });
    }
}

pub type VerticalMenuItems = Vec<VerticalMenuItem, 6>;

pub enum VerticalMenuItem {
    Item(TString<'static>),
    Cancel(TString<'static>),
}

impl VerticalMenuItem {
    fn button(&self) -> Button {
        match self {
            VerticalMenuItem::Item(text) => {
                let content = IconText::new(*text, theme::ICON_CHEVRON_RIGHT);
                Button::with_icon_and_text(content).styled(theme::button_default())
            }
            VerticalMenuItem::Cancel(text) => {
                let content = IconText::new(*text, theme::ICON_CANCEL);
                Button::with_icon_and_text(content).styled(theme::button_warning_high())
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for VerticalMenuItem {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        match self {
            VerticalMenuItem::Item(text) => {
                t.string("item", *text);
            }
            VerticalMenuItem::Cancel(text) => {
                t.string("cancel", *text);
            }
        }
    }
}

pub struct ScrolledVerticalMenu {
    active: VerticalMenu,
    items: VerticalMenuItems,
    pager: Pager,
    menu_capacity: usize,

    up: Option<Button>,
    down: Option<Button>,
}

impl ScrolledVerticalMenu {
    pub fn new(items: VerticalMenuItems, mut item_index: usize) -> Self {
        let menu_capacity = match items.len() {
            0..=MENU_MAX_ITEMS => MENU_MAX_ITEMS,
            _ => MENU_MAX_ITEMS - 1,
        };
        let pages_count = items.chunks(menu_capacity).len() as u16;
        let mut pager = Pager::new(pages_count);
        while item_index >= menu_capacity {
            item_index -= menu_capacity;
            pager.goto_next();
        }
        Self {
            active: VerticalMenu::empty(),
            items,
            pager,
            menu_capacity,
            up: None,
            down: None,
        }
    }

    fn update_active_buttons(&mut self) {
        let chunks_to_skip = self.pager.current().into();
        let mut chunks = self.items.chunks(self.menu_capacity).skip(chunks_to_skip);
        let current_chunk = unwrap!(chunks.next());
        self.active.buttons.clear();
        for item in current_chunk {
            unwrap!(self.active.buttons.push(item.button()));
        }
    }
}

impl SinglePage for ScrolledVerticalMenu {}

impl Component for ScrolledVerticalMenu {
    type Msg = VerticalMenuChoiceMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.up = if self.pager.is_first() {
            None
        } else {
            Some(Button::with_icon(theme::ICON_CHEVRON_UP))
        };
        self.down = if self.pager.is_last() {
            None
        } else {
            Some(Button::with_icon(theme::ICON_CHEVRON_DOWN))
        };

        let bottom_height = match (self.up.as_ref(), self.down.as_ref()) {
            (None, None) => 0,
            _ => MENU_BUTTON_HEIGHT + MENU_SEP_HEIGHT,
        };
        let (top, bottom) = bounds.split_bottom(bottom_height);
        self.update_active_buttons();
        self.active.place(top);
        match (self.up.as_mut(), self.down.as_mut()) {
            (Some(up), Some(down)) => {
                let (left, _, right) = bottom.split_center(0);
                up.place(left);
                down.place(right);
            }
            (Some(up), None) => {
                up.place(bottom);
            }
            (None, Some(down)) => {
                down.place(bottom);
            }
            (None, None) => {}
        };
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let prev_pager = self.pager;
        if let Some(up) = self.up.as_mut() {
            if let Some(ButtonMsg::Clicked) = up.event(ctx, event) {
                self.pager.goto_prev();
            }
        }
        if let Some(down) = self.down.as_mut() {
            if let Some(ButtonMsg::Clicked) = down.event(ctx, event) {
                self.pager.goto_next();
            }
        };
        if prev_pager != self.pager {
            ctx.request_place();
            ctx.request_paint();
        }
        self.active.event(ctx, event).map(|msg| match msg {
            VerticalMenuChoiceMsg::Selected(i) => {
                let offset = usize::from(self.pager.current()) * self.menu_capacity;
                VerticalMenuChoiceMsg::Selected(offset + i)
            }
        })
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.active.render(target);
        if let Some(up) = self.up.as_ref() {
            up.render(target);
        }
        if let Some(down) = self.down.as_ref() {
            down.render(target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ScrolledVerticalMenu {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.active.trace(t);

        let chunks_to_skip = self.pager.current().into();
        let mut chunks = self.items.chunks(self.menu_capacity).skip(chunks_to_skip);
        let current_chunk = unwrap!(chunks.next());

        t.in_child("menu_items", &|t| {
            t.in_list("current", &|t| {
                for item in current_chunk {
                    t.in_child(&|t| item.trace(t));
                }
            });
            t.bool("has_next", self.pager.has_next());
            t.bool("has_prev", self.pager.has_prev());
        });
    }
}

// Polymorphic struct, avoid adding code as it gets duplicated, prefer
// extending VerticalMenu instead.
pub struct PagedVerticalMenu<F: Fn(u16) -> TString<'static>> {
    inner: VerticalMenu,
    page: u16,
    item_count: usize,
    label_fn: F,
}

impl<F: Fn(u16) -> TString<'static>> PagedVerticalMenu<F> {
    pub fn new(item_count: usize, label_fn: F) -> Self {
        let mut result = Self {
            inner: VerticalMenu::select_word(["".into(), "".into(), "".into()]),
            page: 0,
            item_count,
            label_fn,
        };
        result.change_page(0);
        result
    }
}

impl<F: Fn(u16) -> TString<'static>> Paginate for PagedVerticalMenu<F> {
    fn pager(&self) -> Pager {
        let num_pages =
            (self.item_count / self.inner.n_items) + (self.item_count % self.inner.n_items).min(1);
        Pager::new(num_pages as u16).with_current(self.page)
    }

    fn change_page(&mut self, active_page: u16) {
        let n_items = self.inner.n_items as u16;
        for b in 0..n_items {
            let i = active_page * n_items + b;
            let text = if i < self.item_count as u16 {
                (self.label_fn)(i)
            } else {
                "".into()
            };
            let mut dummy_ctx = EventCtx::new();
            let b = b as usize;
            self.inner.buttons[b].enable_if(&mut dummy_ctx, !text.is_empty());
            self.inner.buttons[b].set_content(ButtonContent::Text(text));
        }

        self.page = active_page
    }
}

impl<F: Fn(u16) -> TString<'static>> Component for PagedVerticalMenu<F> {
    type Msg = VerticalMenuChoiceMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.inner.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.inner.event(ctx, event);
        if let Some(VerticalMenuChoiceMsg::Selected(i)) = msg {
            return Some(VerticalMenuChoiceMsg::Selected(
                self.inner.n_items * self.page as usize + i,
            ));
        }
        msg
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target)
    }
}

#[cfg(feature = "ui_debug")]
impl<F: Fn(u16) -> TString<'static>> crate::trace::Trace for PagedVerticalMenu<F> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}
