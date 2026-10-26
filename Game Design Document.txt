# Mind Blower - Game Design Document

Oct 26, 2026 · @Elouan

## Overview

Mind Blower is a party mixer: guests join on their phones, get questions about each other, and chat to find the answers. The person with the most points after everyone marks the answers about themselves wins.

|  |  |
| --- | --- |
| Players | Built for 10 to 20, no hard limit |
| Platform | Hosted on the host's PC, played in phone browsers on the same Wi-Fi |
| Session length | Host decides; ends when the host presses End party, plus a 30-second grace period |
| Install | Nothing for guests: scan a QR code and play |
| Internet | Not needed |
| GitHub repo | mind-blower |
| Repo description | A party game for getting to know each other. Scan the QR code, snap a selfie, then mingle and chat to uncover answers about your friends. Points for every right answer, double for blowing minds, and a podium at the end. |

**Design pillars**

- **Talk, don't tap.** Every point comes from a real conversation. The phone is only a scorecard.
- **Friendly by default.** Questions are light and good natured. Nothing personal, sensitive or security-question-like.
- **Keep the room buzzing.** The TV shows live counts and reactions so the party feels the game going on.
- **Suspense to the end.** Scores stay hidden until the podium.

## Game flow

&#91;embedded content: game flow · 4 phases, 3 host buttons\]

The host's three buttons move the whole room from phase to phase. Players spend most of the night in the party loop, where each answer earns back a skip.

## Joining and lobby

The host joins first, using a private link shown only in the PyCharm console. After that, the TV shows the QR code for everyone else.

**Host first**

1. Starting the server prints a **host link** with a host code in the PyCharm console, plus the same link as a QR code drawn in text. The code only works while nobody is host, so after New game the host rejoins with the same link.
2. Until that link is used, the TV shows "Waiting for the host to join" and no QR code.
3. The host joins like any player (name and selfie) and plays the game too. Their tile wears a crown.
4. The host's phone has a small **Host controls** bar: Start game, End party, Show highlights, and Next to step through the highlights, awards and podium. The same buttons are on the TV when it is opened on the PC itself, so the host can run the game from either.
5. Once the host is in, the TV shows the QR code and address for everyone else.

**Phone: join flow**

1. **Name.** Big field with the label "Your real name" and the helper line "The name your friends call you in person. Not a username or gamertag, people need to find you in the room." The placeholder shows a first name, e.g. "Sam".
2. **Selfie.** A large "Take your selfie" button opens the front camera. The helper line reads "Make sure your face is clear, this is how people will find you." A preview shows with Retake and Looks good.
3. **Waiting.** "You're in!" with their own tile bouncing gently, and the number of players joined so far. The screen stays here until the host starts.

**Host TV: lobby**

- Left side: a large QR code, the address underneath in plain text for anyone who can't scan, and the game title.
- Right side: a grid of selfie tiles (round photo, first name). New tiles pop in with a bounce and a pop sound.
- A player count and a big **Start game** button. Start is disabled until at least 3 players have joined.

**Rules**

- Late joiners are not allowed once the game starts.
- Each phone keeps a player ID, so a refresh or a locked screen drops them straight back in with their points.
- Names must be 1 to 20 characters. If a name is already taken, the phone asks them to add a last initial, e.g. "Sam K".

## Party phase

Players loop through pick, find, ask and answer as many times as they can until the host presses End party. A 30-second grace period then lets everyone finish the answer they're on.

**The loop on the phone**

1. **Pick a category.** Four big buttons, each showing its name and points (see Categories and scoring).
2. **Get a question.** The game picks a person and a question from that category.
3. **Find them and chat.** The question card stays on screen while they look for the person.
4. **Answer.** A short text box, up to 100 characters, then Submit. Back to step 1.

**Question card layout**

- Category name and points at the top.
- The question with the player's name written in, e.g. "What did **Sam** want to be when they were seven?"
- Underneath: Sam's selfie, large, with their name, so the player can find them.
- Answer box, Submit button, and a Skip button with the skips left shown as three dots.

**Skips**

- Everyone starts with 3 skips and can hold at most 3.
- Each submitted answer gives back 1 skip, up to the max.
- A skip sends the player back to the category menu and re-rolls both the person and the question. The skipped question goes back into the pool.
- With 0 skips left, the Skip button is greyed out.

**Matching rules**

- Never yourself, never someone whose phone is disconnected, and never the same person twice in a row.
- Prefer people this player has asked about the fewest times, then people the whole room has asked about the least. Questions this player hasn't had before come first.
- Avoid anyone who already has 2 open questions about them, so nobody gets mobbed. With very few players this rule relaxes.
- Each question is asked about each person once per game, so nobody answers the same thing twice and nobody marks duplicates.
- If a category has no questions left for any available person, its button is greyed out.

**Answer counter**

- On the TV, each player's count sits in a large badge **beneath their selfie, half overlapping the photo**, so it clearly belongs to them.
- When it goes up, the badge does a squash-and-stretch bounce and the TV plays a pop.
- The room total sits at the top of the TV and ticks up too.
- Each phone shows the player's own count at the top at all times.
- It counts answers submitted, not correct ones, so scores stay hidden.

**How-to-play help**

- During the party phase the TV always shows a small **How to play** panel: pick a category, find the person, chat, submit. A highlight cycles through the four steps with a little animation.
- Every phone screen, in every phase, has a **?** button in the top bar. It opens a short help sheet written for the current phase, e.g. how marking and Mind blown work during review.
- The first time a player reaches the category menu, the help sheet opens by itself once.

**Ending: the 30-second grace period**

- The host presses **End party**. A 30-second countdown appears on every phone and on the TV.
- Anyone holding a question can still submit it, but Skip is switched off. The ring around the timer turns red and ticks for the last 10 seconds.
- Players on the category menu can't start a new question; they see "Time's up! Waiting for the others".
- When the timer hits 0, any unsent answer is dropped and everyone moves into the review phase. The grace period ends early once everyone holding a question has answered, and is skipped if nobody was holding one.

## Categories and scoring

Categories are ranked by how hard the answer is to get out of someone, not by how important it is to them. Harder to uncover means more points.

| Category | Points | What makes it this hard | Example |
| --- | --- | --- | --- |
| Small Talk | 1 | Comes up naturally in any chat | What is Sam's favourite snack? |
| Digging | 2 | Needs a bit of steering | What is Sam's go-to karaoke song? |
| Detective | 3 | Nobody brings it up unprompted | What did Sam want to be when they were seven? |
| Top Secret | 4 | People are a bit shy to admit it, but it's still light | What is Sam's guilty-pleasure song? |

**How a marked answer scores**

| Mark | Points to the answer's author | Small Talk | Digging | Detective | Top Secret |
| --- | --- | --- | --- | --- | --- |
| Correct | Full category points | 1 | 2 | 3 | 4 |
| Partly right | Half the category points | 0.5 | 1 | 1.5 | 2 |
| Wrong | Nothing | 0 | 0 | 0 | 0 |
| Mind blown | Double the category points | 2 | 4 | 6 | 8 |

**Giver bonus:** each Mind blown a player hands out also earns **them** 1 point, so everyone is tempted to use all 3.

Scores are kept to one decimal place. Ties on the podium share the spot.

## Review phase

Each player marks every answer written about them, without seeing who wrote it. The TV shows that marking is happening but never the totals.

**Phone: marking cards**

- One card at a time: the question about you, with your own name in it ("What is Sam's guilty-pleasure song?") and the answer someone gave. Each new card slides in from the right.
- The author's name and photo are never shown, to avoid bias.
- Four buttons: **Correct**, **Partly right**, **Wrong**, **Mind blown**. Each mark is exactly one of the four.
- Mind blown is for outstanding answers. Each marker has 3 to give; a counter shows how many are left, and the button greys out at 0. Each one given earns the marker 1 bonus point.
- An **Undo** button reverses the last mark, in case of a mis-tap.
- When the stack is empty: "All done! Watch the TV." A player with nothing to mark sees the same screen.

**Phone: "Show it on the TV?"**

- When one of a player's answers gets a Mind blown, their phone shows a card: "Your answer about Sam blew their mind! Show it on the TV before the results?" with **Show it** and **Keep it private**.
- The card waits until that player has finished their own marking, so it never interrupts them.
- Choosing Show it adds the answer to the Highlights (see Highlights and results). The points are not revealed there. If they haven't chosen by the time the host shows highlights, it stays private.

**Host TV: what the room sees**

- The same grid of selfie tiles. In the spot where the answer counter was, **beneath each selfie and half overlapping it**, there is now that player's own small paper stack, with the number left to mark printed on the top page.
- When someone marks an answer, the top page of **their** stack lifts and flutters away with a whoosh, tinted with the mark's colour, and the number drops by one.
- At the same moment, the **author's** tile flashes that colour and plays a matching sound:
  - Correct: green
  - Partly right: amber
  - Wrong: red
  - Mind blown: grape, with a starburst animation
- When a stack runs out, it turns into a green tick badge.
- No totals or scores are shown. Sharp-eyed players can count flashes, and that's part of the fun.
- **Show highlights** stays locked until every answer has been marked. While it's locked, the TV shows who is still marking; once the last stack is gone, the button lights up and pulses. If nobody chose to show a highlight, it reads Show results instead.

## Highlights and results

The ending runs in three steps: Mind blown highlights, then awards, then the podium. The host taps to advance each reveal, so they can build suspense.

**1. Highlights**

- One card per Mind blown answer whose author chose Show it, in random order.
- Each card shows the question with the subject's selfie, then the answer pops in, then the author's selfie is revealed with a starburst and a sparkle sound.
- No points are shown. If nobody chose Show it, this step is skipped.

**2. Awards**

Each award only appears if someone qualifies, and one player can win several. Under the winner's name, the TV shows exactly what the award was for, with their number. Tied players share the award, but an award is skipped if every eligible player is tied. Decorated needs at least 2 awards.

| Award | Subtext shown on the TV (example) |
| --- | --- |
| Social Butterfly | Most answers submitted: 12 |
| Mind Blower | Most Mind blowns received: 4 |
| Hype Squad | First to hand out all 3 Mind blowns |
| Daredevil | Most Top Secret answers submitted: 5 |
| Quick Draw | Fastest average answer: 1 min 40 s (3+ answers) |
| Close Enough | Most Partly right marks received: 4 |
| Picky Picker | Most skips used: 9 |
| Most Wanted | Most questions asked about them: 11 |
| Open Book | Most often guessed right: 8 of 9 |
| Most Mysterious | Least often guessed right: 2 of 7 |
| Were You Even Listening? | Fewest answers marked right: 1 of 5 |
| Decorated | Most awards: 3 |

"Guessed right" and "marked right" mean Correct, Partly right or Mind blown. Those awards need at least 3 answers to count.

**3. Podium**

- A drumroll, then 3rd, 2nd and 1st rise up one tap at a time, each with a large selfie, name and points.
- Confetti and a fanfare for the winner.
- After the podium, the full leaderboard slides in beside it, in two columns for more than 10 players (top 24 shown).

**Phone: personal results**

- Once the leaderboard is on the TV: their rank, total points, and a breakdown: answers submitted, Correct, Partly right, Wrong, Mind blown received, Mind blown bonus.
- Any awards they won are shown as badges that spin in, each with its subtext.

The host can press **New game** to go back to an empty lobby.

## Visual and UI direction

Cute, orange and bubbly: warm colours, round everything, and bouncy motion. No emojis anywhere in the app; any icons are simple custom shapes.

**Palette**

| Role | Name | Hex |
| --- | --- | --- |
| Background | Cream | #FFF6EC |
| Primary | Tangerine | #FF8A3D |
| Primary, pressed | Burnt orange | #E8681A |
| Soft fill | Peach | #FFD9BD |
| Text | Cocoa | #4A2C1D |
| Correct | Mint green | #2FBF71 |
| Partly right | Amber | #FFB020 |
| Wrong | Coral red | #F2545B |
| Mind blown | Grape | #8B5CF6 |

Mind blown uses grape rather than gold so it stands out against all the orange.

**Type**

- Fredoka for everything: bold for titles and buttons, regular for body text.
- The font files ship with the project, so nothing loads from the internet.
- Phone text is never smaller than 16 px; TV names are at least 28 px so they read from across the room.

**Shapes**

- Cards with 24 px rounded corners; pill-shaped buttons.
- Buttons have a chunky darker base, like a 4 px ledge, and squish down when pressed.
- Selfies are always circles with a thick white ring.
- Soft round blobs float slowly in the background of the TV screen.

**Motion on every screen**

Every screen has something gently moving at rest, and a clear visual reaction to every event.

| Screen | Always moving | Reacts to events |
| --- | --- | --- |
| Phone: join | Logo starburst slowly turns; camera button breathes | Shutter flash when the selfie is taken |
| Phone: waiting | Own tile bobs; joined count ticks up | New players' faces slide along the bottom |
| Phone: categories | Buttons float in one after another; one wiggles every few seconds | Tapped button squishes, then the question card flips in |
| Phone: question | Selfie gently bobs; a small arrow nudges "go find them" | Submit: card flies up, counter bounces, a skip dot refills |
| Phone: grace period | Timer ring drains | Last 10 seconds pulse red |
| Phone: review | New card slides in | Card flicks away tinted with the mark colour |
| TV: lobby | Background blobs drift; QR card breathes | New tiles pop in |
| TV: party | Blobs drift; How to play highlight cycles | Counter badge squash-and-stretch |
| TV: review | Stacks rustle slightly | Page flies off; author's tile flashes |
| TV: ending | Confetti; spotlight sweep | Cards and podium steps rise on each tap |

All motion respects the device's reduce-motion setting.

**Sound**

Short sound effects for every event and button press; no background music. The TV is the main speaker. Phones only play sounds for their own actions, kept short and quiet so 20 phones don't clash.

| Event | Sound | Plays on |
| --- | --- | --- |
| Any button press | Soft click | Phone, TV |
| Player joins | Pop | TV |
| Selfie taken | Shutter | Phone |
| Answer submitted | Pop | TV (and a soft ding on the phone) |
| Skip used | Quick swoop down | Phone |
| Skip earned back | Little plink | Phone |
| End party pressed | Whistle | TV, phones |
| Last 10 seconds | Ticks | TV, phones |
| Time's up | Gong | TV, phones |
| Page flies off a stack | Paper whoosh | TV |
| Correct | Bright ding | TV, marker's phone |
| Partly right | Two-note boop | TV, marker's phone |
| Wrong | Soft bonk | TV, marker's phone |
| Mind blown | Sparkle and boom | TV, marker's phone |
| Highlight revealed | Sparkle | TV |
| Award revealed | Short jingle | TV |
| Podium | Drumroll, then fanfare | TV |

Sounds are generated in the browser, so there are no audio files to manage. Phones switch sound on with the first tap (browsers require this), and both the TV and the help sheet have a mute toggle.

## Concept art

These mockups set the look; the selfies are stand-in cartoon faces. Exact spacing and copy can shift during the build.

**Phone: joining and picking a category**

&#91;image: Phone screens: join with real-name prompt and selfie button, then the category menu with points and a help button\]

The join screen leads with "Your real name" and calls out that usernames won't work. Every phone screen has the **?** help button in its top bar.

**Phone: question card and review**

&#91;image: Phone screens: question card with Sam's selfie, then a review card with four marking buttons\]

The question writes the player's name in, with their selfie underneath to find them. Review shows only the question and answer, never the author.

**Phone: grace timer, help sheet and highlight prompt**

&#91;image: Phone screens: 30-second grace countdown, the phase help sheet with a sound switch, and the Show it on the TV prompt\]

**TV: lobby**

&#91;image: TV lobby with QR code, address and a grid of 12 player tiles, the host wearing a crown\]

**TV: party phase**

&#91;image: TV party screen with answer counts in badges beneath each selfie and a How to play panel\]

Each count sits beneath its owner's selfie, half overlapping it. Mia's badge is mid-bounce after a new answer. The How to play panel cycles its highlight through the four steps.

**TV: review phase**

&#91;image: TV review screen with each player's paper stack beneath their selfie, flying pages and coloured flashes\]

Each player's stack sits beneath their own selfie with the number left on top, so it's clear whose it is. Sam's green page is flying off his stack while Mia, the author, flashes green. Ella gets the grape starburst for a Mind blown.

**TV: highlights**

&#91;image: TV highlight card: Sam's question, Mia's answer in a grape-bordered bubble and Mia revealed as the author\]

**TV: results**

&#91;image: TV results screen with a three-step podium and award cards whose subtext states each award's criteria\]

Mia wins two awards here; each card's subtext says exactly what it was for.

## Question bank

There are 100 questions, 25 per category. The app replaces {player} with the person's name, shown in bold, and puts their selfie underneath.

Left out on purpose: anything that works like an account-recovery question (first pet, school, street, middle name, birthplace, first car, nicknames, birthdays), and anything about money, relationships, health or family.

**Small Talk (1 point)**

1. What does {player} study or do for work?
2. What is {player}'s favourite snack?
3. What is {player}'s dream pet?
4. What is {player}'s go-to café order?
5. What is {player}'s favourite season?
6. What time does {player} usually go to bed?
7. What is {player}'s favourite movie?
8. What kind of music does {player} listen to most?
9. What is {player}'s favourite cuisine?
10. How does {player} take their coffee or tea?
11. What is {player}'s ideal way to spend a weekend?
12. What was the last show {player} binge-watched?
13. Where is {player}'s dream holiday destination?
14. What is {player}'s favourite dessert?
15. What sport does {player} most like to watch or play?
16. What does {player} usually have for breakfast?
17. What is {player}'s favourite colour?
18. What is the best place {player} has ever travelled to?
19. What is {player}'s go-to takeaway order?
20. What is {player}'s favourite spot in town?
21. What hobby does {player} spend the most time on?
22. What is {player}'s favourite board or card game?
23. What is {player}'s favourite ice cream flavour?
24. What is {player}'s favourite fruit?
25. What does {player} do to relax after a long day?

**Digging (2 points)**

1. What weird food combo does {player} love?
2. What is {player}'s go-to karaoke song?
3. What hidden talent does {player} have?
4. Which app does {player} spend the most time on?
5. What was the last thing {player} bought online?
6. What food does {player} refuse to eat?
7. What movie has {player} watched way too many times?
8. What was {player}'s favourite subject at school?
9. Which celebrity have people said {player} looks like?
10. What is on {player}'s phone wallpaper?
11. What would {player} choose as their last meal?
12. Which fictional world would {player} most like to live in?
13. What is the best gift {player} has ever received?
14. What is {player}'s signature dish?
15. What would {player} buy first if they won the lottery?
16. Which superpower would {player} choose?
17. What was the last book {player} read?
18. What is {player}'s favourite smell?
19. What skill would {player} love to learn?
20. What are {player}'s ideal pizza toppings?
21. What is the furthest {player} has ever been from home?
22. What song does {player} have on repeat right now?
23. What would {player}'s theme song be?
24. What is {player}'s favourite word?
25. Which decade's fashion would {player} bring back?

**Detective (3 points)**

1. What did {player} want to be when they were seven?
2. What was {player}'s favourite cartoon as a kid?
3. What was the first video game {player} played?
4. What was {player}'s favourite toy growing up?
5. What was the first album or song {player} bought?
6. What was {player}'s worst-ever haircut?
7. What is the strangest job {player} has ever done?
8. What is the best concert {player} has been to?
9. What was {player}'s favourite lunchbox snack as a kid?
10. What was {player}'s most memorable birthday party?
11. What instrument did {player} learn, or try to learn, as a kid?
12. Who is the most famous person {player} has met?
13. What was the first thing {player} learned to cook?
14. What random award or trophy has {player} won?
15. What was {player}'s favourite book as a kid?
16. What was {player}'s favourite school trip?
17. Which Halloween or dress-up costume is {player} proudest of?
18. What was {player}'s favourite after-school activity?
19. Which movie scared {player} the most as a kid?
20. What did {player} collect as a kid?
21. What is the most spontaneous thing {player} has ever done?
22. What sport or activity did {player} try once and never again?
23. What was {player}'s favourite holiday as a kid?
24. What is the most unusual food {player} has ever tried?
25. What TV show did {player} love as a teenager?

**Top Secret (4 points)**

1. What is {player}'s guilty-pleasure song?
2. What harmless thing is {player} irrationally scared of?
3. What is {player}'s funniest embarrassing moment?
4. Which show does {player} secretly love?
5. What is the pettiest thing that annoys {player}?
6. What popular thing does {player} secretly not like?
7. What childish thing does {player} still enjoy?
8. What did {player} believe as a kid that turned out to be wrong?
9. What is {player}'s worst cooking disaster?
10. What is the cringiest outfit {player} wore proudly?
11. What does {player} pretend to understand but doesn't?
12. Which word does {player} always mispronounce?
13. What is {player}'s go-to dance move when no one's watching?
14. Which fictional character does {player} relate to a bit too much?
15. What has {player} been meaning to do for over a year?
16. What is the strangest thing {player} has kept or collected?
17. Which trend did {player} fully commit to and now regret?
18. What is the silliest thing {player} has bought on impulse?
19. What is {player}'s go-to excuse for running late?
20. Which famous movie does {player} pretend to have seen?
21. What is {player}'s most embarrassing autocorrect or typo?
22. What was {player}'s cringiest phase as a teenager?
23. What was {player}'s worst DIY attempt?
24. When was {player} the most lost they've ever been?
25. Which song does {player} always sing the wrong lyrics to?

## Code outline

The game's rules live in plain Python that knows nothing about the web. A thin server layer passes taps in and sends screens out. The browsers only draw what they're told.

**Project layout**

```text
mind-blower/
├── run.py                 Start here: reads options, starts the server, prints the host link
├── requirements.txt       flask, flask-socketio, simple-websocket, qrcode, pytest
├── pytest.ini             Points pytest at tests/
├── README.md              Setup and how to run a party
├── .gitignore
├── .run/                  PyCharm run configurations: Mind Blower, solo test, Tests
├── mindblower/
│   ├── config.py          Every tunable number in one place
│   ├── models.py          Dataclasses: Player, Assignment, Answer, Question; Phase and Mark
│   ├── questions.py       Loads and checks data/questions.json
│   ├── matching.py        Chooses who and what to ask (pure functions)
│   ├── scoring.py         Points per mark, giver bonus, totals, ranking
│   ├── awards.py          One small function per award, plus Decorated
│   ├── game.py            The Game class: phases and every rule, no web code
│   ├── views.py           Turns game state into exactly what each screen needs
│   ├── server.py          Flask routes and Socket.IO events: calls Game, sends views
│   ├── timers.py          Grace-period countdown
│   ├── network.py         Local IP, QR code as SVG (TV) and as text (console)
│   └── bots.py            Fake players and the "mark everything" shortcut
├── data/questions.json    The 100 questions, by category
├── static/
│   ├── css/               theme.css (shared), phone.css, tv.css
│   ├── fonts/             Fredoka files and their licence
│   ├── img/icon.svg       Browser tab icon
│   ├── vendor/            socket.io.min.js, bundled so no internet is needed
│   └── js/
│       ├── connection.js  Socket, player ID, reconnecting, toasts
│       ├── sound.js       Sound effects made in the browser
│       ├── motion.js      Shared animations: bump, flash, fly away, burst, confetti
│       ├── phone.js       Draws phone screens from views
│       └── tv.js          Draws TV screens from views, plus the dev panel
├── templates/             phone.html, tv.html, dev.html
├── uploads/               Selfies (git ignores everything but .gitkeep)
└── tests/                 pytest tests (see Testing on your own)
```

**.gitignore:** the usual Python clutter plus `.idea/` and everything in `uploads/` except `.gitkeep`. `data/` (the question bank) and `.run/` (the shared PyCharm run configurations) are committed.

**Rules the code follows**

1. **Game logic has no web code.** game.py, matching.py, scoring.py and awards.py can all be tested without a browser.
2. **The server is the only source of truth.** Phones and the TV send what the player wants ("pick Detective") and draw what comes back. They never decide anything.
3. **Whole screens, not patches.** After every change, each screen gets a small snapshot of everything it shows (a "view"). A phone that reconnects just gets the latest view, so screens can't drift out of sync.
4. **Effects are separate.** One-off cues such as "pop Mia's badge" or "fly a page off Leo's stack" travel as fx messages that only trigger animation and sound. Missing one never breaks the game.
5. **One lock around the game.** Every handler runs inside `with game.lock:`, so two taps at the same moment can't corrupt anything.
6. **Every action is checked.** Right phase, right player, right question id, or the phone gets a friendly message. Actions name the thing they act on, so a double tap counts once.
7. **The server owns time.** The grace deadline is a server timestamp; phones count down to it, corrected for clock differences measured when they connect.
8. **Small and cacheable images.** Selfies are shrunk on the phone to 400 px JPEGs (about 40 KB) and uploaded once. Screens get a link, not the image data. Selfies are deleted each time the server starts.

**Data model**

```python
class Phase(str, Enum): LOBBY, PARTY, GRACE, REVIEW, HIGHLIGHTS, RESULTS
class Mark(str, Enum):  CORRECT, PARTLY, WRONG, MIND_BLOWN

@dataclass(frozen=True)
class Question:
    id: str                                  # e.g. "detective-1"
    category: str
    text: str                                # contains "{player}"

@dataclass
class Player:
    id: str
    name: str
    selfie_url: str
    joined_at: float
    is_host: bool = False
    is_bot: bool = False
    skips: int = 3
    skips_used: int = 0                      # Picky Picker
    mind_blowns_left: int = 3
    all_mind_blowns_given_at: float | None   # Hype Squad
    current: Assignment | None = None        # the question they're holding
    last_subject_id: str | None = None       # never the same person twice in a row
    connections: int = 0                     # open browser tabs; bots always count as connected
    mark_history: list[str]                  # answer ids, newest last, for Undo

@dataclass
class Assignment:                            # one question given to one player
    id: str
    asker_id: str
    subject_id: str
    question_id: str
    category: str
    given_at: float

@dataclass
class Answer:
    id: str
    asker_id: str                            # the author
    subject_id: str                          # the marker
    question_id: str
    category: str
    text: str
    given_at: float
    submitted_at: float                      # Quick Draw uses the difference
    mark: Mark | None = None
    show_on_tv: bool | None = None           # author's Highlights choice
```

**The Game class (its public methods)**

```python
class Game:
    lock: threading.RLock                  # the server wraps every call in `with game.lock:`
    def join(self, name, selfie_url, host_key=None, is_bot=False) -> Player
    def connect(self, player_id) / disconnect(self, player_id)
    def start(self)
    def category_options(self, player_id) -> list[dict]   # greyed-out buttons
    def pick_category(self, player_id, category) -> Assignment
    def skip(self, player_id, assignment_id)
    def submit_answer(self, player_id, assignment_id, text) -> Answer | None
    def end_party(self) -> float | None    # PARTY -> GRACE (returns deadline), or straight to REVIEW
    def finish_grace(self)                 # GRACE -> REVIEW, called by the timer
    def review_queue(self, player_id) -> list[Answer]
    def mark(self, player_id, answer_id, mark)
    def undo_mark(self, player_id)
    def pending_highlight(self, player_id) -> Answer | None
    def choose_highlight(self, player_id, answer_id, show)
    def show_highlights(self)              # only once everything is marked
    def advance(self)                      # next highlight, award or podium step
    def new_game(self)
    def drain_fx(self) -> list[dict]       # one-off animation and sound cues for the TV
```

**Messages between screens and server**

| From | Message | Carries | What happens |
| --- | --- | --- | --- |
| Phone | POST /api/join (web request) | Name, selfie, host code if any | Creates the player, returns their ID |
| Phone | hello | Player ID | Re-attaches after a refresh; server replies with the view |
| Phone | pick | Category | Game.pick\_category |
| Phone | skip | Assignment ID | Game.skip |
| Phone | answer | Assignment ID, text | Game.submit\_answer |
| Phone | mark | Answer ID, mark | Game.mark |
| Phone | undo | Nothing | Game.undo\_mark |
| Phone | highlight | Answer ID, yes or no | Game.choose\_highlight |
| Host phone or TV | host | start, end, highlights, next or new game | The matching Game method |
| Server | view | Everything one screen shows | The screen redraws |
| Server | fx | Effect name and who it's for | Animation and sound only |
| Server | oops | A friendly message | Toast on that phone |
| Server | forget | Nothing | Phone clears a saved player ID the server doesn't know (e.g. after a restart) |
| TV on the PC (dev mode) | dev | add\_bots, bots\_now, skip\_timer, mark\_all or reset | Dev shortcuts |

**One action end to end**

1. Mia taps Submit. Her phone sends `answer` with the assignment ID and her text.
2. server.py takes the lock and calls `game.submit_answer(...)`.
3. The game checks the phase and that Mia holds that assignment, stores the answer, adds a skip back and clears her question.
4. The server sends fresh views to the TV and every phone, plus `fx: counter_up` for Mia.
5. The TV bounces Mia's badge and plays a pop. Mia's phone shows the category menu.

**Known gotchas**

- **Camera over plain HTTP.** Phones block live camera access on non-HTTPS pages. A file input set to the front camera opens the camera directly and needs no certificates.
- **Firewall.** Windows asks the first time the server runs. Allow it on private networks.
- **Guest Wi-Fi.** Guest networks often stop devices from seeing each other. Everyone needs the main network.
- **Sound on phones.** Browsers only allow sound after a tap, so the Join button also switches sound on.

## Testing on your own

Four layers let you test every part of the game alone: automatic tests, bot players, a multi-phone dev page and shortcut controls.

**1. Automatic tests (pytest)**

| Test file | What it checks |
| --- | --- |
| test\_matching.py | Never yourself, no repeats, balancing, the 2-open-questions cap, greyed-out categories |
| test\_scoring.py | Every mark in every category, half points, double points, giver bonus |
| test\_awards.py | Every award, minimums, ties, one player winning several |
| test\_game\_flow.py | A whole game with 5 fake players: skips, undo, grace period, highlights locked until everything is marked |
| test\_server.py | Socket.IO test client: joining, host code, reconnecting with the same ID, bad input rejected |

They run in a few seconds from a PyCharm run configuration.

**2. Bot players**

`python run.py --bots 12 --speed 10` adds 12 fake players with cartoon selfies as soon as the host joins. They pick categories, "chat" for a random 5 to 20 seconds (divided by the speed), answer with silly sample answers, sometimes skip, mark answers and opt into highlights. You can play alongside them from your own phone.

**3. Dev page**

Opening /dev on the PC shows the TV view next to 4 phone-sized frames. Each frame is its own player, so you can play several people at once with the mouse. Phone 1 is the host, and each frame has a "No camera? Use a cartoon face" button instead of a selfie.

**4. Dev controls**

With `--dev`, the TV gets a small **Dev tools** panel at the top centre, closed until clicked: Add 1 bot, Add 5 bots, Bots act now, Skip timer, Mark all randomly, Reset game, Slow motion, and a sound board that plays every effect.

**PyCharm run configurations**

| Name | Runs |
| --- | --- |
| Mind Blower | `python run.py` |
| Mind Blower: solo test | `python run.py --dev --bots 12 --speed 10` |
| Tests | `pytest tests/` |

Before the party, do one real check with your own phone on the Wi-Fi: scan the QR code, take a selfie, and make sure sound plays.

## Build notes

The first version is built: 49 automated tests pass, and full games ran end to end in a browser with 2 people plus 6, then 20 bots. The doc above now matches the code; these are the details settled while building.

- **Grace period** ends early once everyone holding a question has answered, and is skipped if nobody was holding one.
- **Marking cards** show the question with the marker's own name. Rewriting every question to say "you" would break the grammar of many questions.
- **Host code** works whenever nobody is host, so the same link is reused after New game. The TV's host buttons only appear when the TV page is open on the PC.
- **Show results** replaces the Show highlights label when nobody chose to show a highlight.
- **Awards** are skipped when every eligible player is tied; Decorated needs at least 2 awards.
- **Personal results** appear on phones once the leaderboard is on the TV, so the podium stays a surprise.
- **Leaderboard** uses two columns for more than 10 players and shows the top 24.
- **Matching** also prefers questions the asker hasn't had before.
- **Selfies** are deleted each time the server starts.
- **Dev mode**: bots join as soon as the host does; the dev page phones can use a cartoon face instead of a camera; the planned "Jump to phase" control became Mark all randomly and Reset game, which cover the same need more safely.
- **Requirements**: Python 3.10 or newer. PyCharm run configurations ship in `.run/`.
