import asyncio
import random

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message, MessageTarget
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Header, Input, Label, Static


class PromoFooter(Widget):
    """Sticky footer saying the app was built with textual."""
    DEFAULT_CSS = """
    PromoFooter {
        dock: bottom;
        width: 100%;
        height: 1;
        content-align-horizontal: right;
        color: $text;
        background: $accent;
    }

    PromoFooter Label {
        width: auto;
        padding: 0 2 0 2;
    }

    PromoFooter #author {
        dock: right;
    }

    PromoFooter #promo {
        dock: left;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("[link=https://github.com/textualize/textual]Built with :purple_heart: and Textual[/link]", id="promo")
        yield Label("[link=https://twitter.com/mathsppblog]by @mathsppblog[/link]", id="author")


class WelcomeScreen(Screen):
    """A simple welcome screen."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Label("[u]Welcome 🎅[/u]", id="welcome"),
            Label("Let's prepare your Secret Santa draw!"),
        )
        yield Container(Button("Start"))
        yield PromoFooter()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()


class DrawEntrant(Static):
    """Widget to show entrants for the draw."""
    DEFAULT_CSS = """
    DrawEntrant {
        height: 3;
        margin: 1;
        background: $boost;
    }
    DrawEntrant > Label {
        align-vertical: middle;
        dock: left;
        padding-left: 2;
        max-height: 1;
        overflow-x: auto;
    }
    DrawEntrant > Button {
        dock: right;
        min-width: 5;
        width: 5;
        content-align-horizontal: center;
    }
    """

    class RemoveEntrant(Message):
        """Message emitted to remove entrant from parent widget."""
        def __init__(self, sender: MessageTarget, to_remove: "DrawEntrant"):
            super().__init__(sender)
            self.entrant = to_remove

    def __init__(self, label) -> None:
        print("Going to create a DrawEntrant.")
        super().__init__("")
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.label)
        yield Button("[b]X[/b]", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.emit_no_wait(self.RemoveEntrant(self, self))
        event.stop()

    def on_click(self, event) -> None:
        print(self.styles)
        print(self.styles.css)


class DrawMatch(Static):
    DEFAULT_CSS = ""

    def __init__(self, giver: str, receiver: str) -> None:
        super().__init__()
        self.giver = giver
        self.receiver = receiver

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label(self.giver, id="giver"),
            Label("👐🎁", id="emoji"),
            Label(self.receiver, id="receiver"),
        )

class DrawScreen(Screen):
    """The screen where the user inputs names to enter the draw."""

    class Ready(Message):
        """Message to be emitted when results are ready to be displayed."""
        def __init__(self, sender: MessageTarget, people: list[str]) -> None:
            super().__init__(sender)
            self.people = people

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Input(placeholder="Type a name...")
        yield Vertical(id="names")
        yield Container(Button("Generate 🎲🎁"), id="button-container")
        yield PromoFooter()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value or any(
            event.value == str(lbl.renderable) for lbl in self.query(Label)
        ):
            self.app.bell()
            return

        self.query_one("#names").mount(DrawEntrant(event.value))
        self.query_one(Input).value = ""

    async def on_button_pressed(self, _: Button.Pressed) -> None:
        """Handler to generate the secret santa drawing."""
        all_entrants = self.query_one("#names").query(Label)
        if len(all_entrants) < 2:
            self.app.bell()
            return

        people = [str(lbl.renderable) for lbl in all_entrants]
        await self.emit(self.Ready(self, people))

        self.app.pop_screen()
        for entrant_widget in self.query_one("#names").query(DrawEntrant):
            await entrant_widget.remove()
        self.query_one(Input).value = ""
        self.refresh(layout=True)

    async def on_draw_entrant_remove_entrant(self, event: DrawEntrant.RemoveEntrant) -> None:
        await event.entrant.remove()


class ResultsScreen(Screen):
    """Screen to show the results to the user."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Vertical(id="matches"),
            Container(Button("Reset draw")),
        )
        yield PromoFooter()

    async def on_button_pressed(self, _: Button.Pressed) -> None:
        self.app.push_screen("draw")
        for match in self.query_one("#matches").query(DrawMatch):
            await match.remove()

    def generate_matches(self, people: list[str]) -> None:
        """Method to generate matches and show them on screen."""
        self.query_one("#matches").mount(Label("Generating matchings..."))
        asyncio.create_task(self._generate_matches(people))

    async def _generate_matches(self, people: list[str]) -> None:
        """Private method that generates non-cyclical matches for the draws."""
        await asyncio.sleep(0.3)

        chain = people[:]
        random.shuffle(chain)

        results_container = self.query_one("#matches")
        await results_container.query_one(Label).remove()
        for giver, receiver in zip(chain, chain[1:] + chain[:1]):
            results_container.mount(DrawMatch(giver, receiver))


class SecretSanta(App):
    """TUI app to draw names for a Secret Santa."""

    CSS_PATH = "secretsanta.css"
    SCREENS = {
        "draw": DrawScreen,
        "results": ResultsScreen,
        "welcome": WelcomeScreen,
    }
    TITLE = "Secret Santa"

    def on_compose(self):
        self.push_screen("results")
        self.push_screen("draw")
        # self.push_screen("welcome")

    def on_draw_screen_ready(self, event: DrawScreen.Ready) -> None:
        self.query_one(ResultsScreen).generate_matches(event.people)


app = SecretSanta()
if __name__ == "__main__":
    app.run()
