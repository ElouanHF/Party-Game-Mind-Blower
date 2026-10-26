# Mind Blower

A party game for getting to know each other. Scan the QR code, snap a selfie, then mingle and chat to uncover answers about your friends. Points for every right answer, double for blowing minds, and a podium at the end.

Everything runs on your own PC. Guests play in their phone's browser over your Wi-Fi: no app to install, no accounts and no internet needed.

Designed by Elouan Hay-Fourmond.

Coded by Claude Opus 5.5.

## How a game goes

1. **Lobby.** The host joins first using a private link, then everyone scans the QR code on the TV, types their real name and takes a selfie.
2. **Party.** Pick a category, get a question about someone in the room, go and chat to find out the answer, submit, repeat. Harder categories are worth more. You hold up to 3 skips and earn one back for every answer.
3. **Grace period.** When the host ends the party, anyone holding a question gets 30 seconds to finish it.
4. **Review.** Everyone marks the answers written about them (without seeing who wrote them): Correct, Partly right, Wrong or Mind blown. Mind blown doubles the points, and each one you give earns you a bonus point.
5. **Ending.** Mind blown highlights (if their authors agree), then the awards, then the podium.

## Setup in PyCharm

You need **Python 3.10 or newer**.

1. Open PyCharm and choose **File > Open**, then pick the `mind-blower` folder (or clone the repo with **Get from VCS**).
2. When PyCharm asks to create a virtual environment from `requirements.txt`, say yes. If it doesn't ask, open **Settings > Project > Python Interpreter**, add a new **Virtualenv** interpreter, then open the **Terminal** tab and run:

```
   pip install -r requirements.txt
   ```

3. Three run configurations are already set up (top right of the window, next to the green play button):

   * **Mind Blower**: a normal party.
   * **Mind Blower solo test**: dev tools plus 12 bot players, 10x faster.
   * **Tests**: runs the automated tests.

   If PyCharm shows them with a red cross, open the configuration, set the interpreter to your project interpreter and save. That happens if your project folder isn't called `mind-blower`.

## Running a party

1. Run **Mind Blower**. The console prints a **host link** and a QR code for it, and the TV screen opens in your browser.
2. **Host:** open the host link on your phone first (scan the console QR code, or type the link). Join with your name and selfie. You'll get a crown and the host buttons.
3. The TV now shows the QR code for everyone else. Put the browser in full screen (button at the bottom right of the TV).
4. When everyone's in, press **Start game** (on your phone or the TV). Later press **End party**, then **Show highlights**, then **Next** to step through the ending.

Tips:

* Everyone must be on the **same Wi-Fi** as the PC. Guest networks often block this, so use the main network.
* The first time you run it, **Windows Firewall** asks for permission. Allow it on **private networks**.
* If a phone locks or the page closes, just open the same link again. Players come straight back with their points.
* The host buttons on the TV only appear when the TV page is open on the PC itself.
* Selfies are deleted every time the server starts.

## Testing on your own

* **Mind Blower solo test** adds 12 bots once you've joined as host. They pick questions, answer, skip, mark and opt into highlights on their own.
* With dev mode on, the console also prints a **dev page** link (`http://localhost:5000/dev`): the TV plus four phones side by side, each one a separate player. Phone 1 is the host. Use **"No camera? Use a cartoon face"** instead of a selfie.
* The TV gets a **Dev tools** panel (top centre): add bots, make bots act now, skip the timer, mark everything randomly, reset, slow motion and a sound board.
* Command line options: `python run.py --help`

```
  --dev            dev tools and the /dev page
  --bots N         add N bots once the host joins
  --speed X        bots act X times faster
  --port 5000      change the port
  --no-browser     don't open the TV page automatically
  ```

* Run **Tests** (or `pytest`) for the automated tests. They take under a second.

## Changing things

* **Questions:** edit `data/questions.json`. Each category needs at least one question, and each question needs exactly one `{player}` where the name goes.
* **Numbers** (points, skips, grace period, minimum players and so on): `mindblower/config.py`.
* **Colours and fonts:** `static/css/theme.css`.

## Project layout

```
run.py                  Start here
mindblower/
  config.py             Every tunable number
  models.py             Player, Assignment, Answer, Phase, Mark
  questions.py          Loads and checks the question bank
  matching.py           Chooses who and what to ask
  scoring.py            Points and totals
  awards.py             One small function per award
  game.py               The Game class: every rule, no web code
  views.py              What each screen is sent
  server.py             Flask routes and Socket.IO events
  timers.py             The 30-second grace countdown
  network.py            Local IP address and QR codes
  bots.py               Fake players for testing
data/questions.json     The 100 questions
static/                 CSS, JavaScript, fonts
templates/              phone.html, tv.html, dev.html
tests/                  pytest tests
.run/                   PyCharm run configurations
```

The game rules live in plain Python with no web code, so they can be tested without a browser. The server is the only source of truth: phones and the TV send what the player wants to do and redraw whatever the server sends back.

## Credits

Font: [Fredoka](https://github.com/hafontia/Fredoka-One), SIL Open Font License (see `static/fonts/OFL-LICENSE.txt`). Real-time messaging: [Socket.IO](https://socket.io/) (MIT).

