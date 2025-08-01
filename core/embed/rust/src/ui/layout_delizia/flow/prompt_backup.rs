use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs},
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::{Frame, PromptScreen, SwipeContent, VerticalMenu},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum PromptBackup {
    Intro,
    Menu,
    SkipBackupIntro,
    SkipBackupConfirm,
}

impl FlowController for PromptBackup {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Intro, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::SkipBackupIntro, Direction::Up) => Self::SkipBackupConfirm.swipe(direction),
            (Self::SkipBackupConfirm, Direction::Down) => Self::SkipBackupIntro.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::SkipBackupIntro.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::SkipBackupIntro, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::SkipBackupConfirm, FlowMsg::Cancelled) => Self::SkipBackupIntro.swipe_right(),
            (Self::SkipBackupConfirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_prompt_backup() -> Result<SwipeFlow, error::Error> {
    let title: TString = TR::backup__title_create_wallet_backup.into();
    let text_intro: TString = TR::backup__it_should_be_backed_up.into();

    let paragraphs = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, text_intro));
    let content_intro = Frame::left_aligned(title, SwipeContent::new(paragraphs))
        .with_menu_button()
        .with_swipeup_footer(None)
        .map_to_button_msg();

    let content_menu = Frame::left_aligned(
        "".into(),
        VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::backup__title_skip.into()),
    )
    .with_cancel_button()
    .map(super::util::map_to_choice);

    let paragraphs_skip_intro = ParagraphVecShort::from_iter([
        Paragraph::new(&theme::TEXT_WARNING, TR::words__not_recommended),
        Paragraph::new(
            &theme::TEXT_MAIN_GREY_LIGHT,
            TR::backup__create_backup_to_prevent_loss,
        ),
    ])
    .into_paragraphs();
    let content_skip_intro = Frame::left_aligned(
        TR::backup__title_skip.into(),
        SwipeContent::new(paragraphs_skip_intro),
    )
    .with_cancel_button()
    .with_swipeup_footer(Some(TR::words__continue_anyway_question.into()))
    .with_swipe(Direction::Up, SwipeSettings::default())
    .map_to_button_msg();

    let content_skip_confirm = Frame::left_aligned(
        TR::backup__title_skip.into(),
        SwipeContent::new(PromptScreen::new_tap_to_cancel()),
    )
    .with_cancel_button()
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .with_swipe(Direction::Down, SwipeSettings::default())
    .map(super::util::map_to_confirm);

    let mut res = SwipeFlow::new(&PromptBackup::Intro)?;
    res.add_page(&PromptBackup::Intro, content_intro)?
        .add_page(&PromptBackup::Menu, content_menu)?
        .add_page(&PromptBackup::SkipBackupIntro, content_skip_intro)?
        .add_page(&PromptBackup::SkipBackupConfirm, content_skip_confirm)?;
    Ok(res)
}
