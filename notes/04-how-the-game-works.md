# How the game works (the instruction manual, rebuilt from the code)

Everything here comes from the program itself (its messages, tables and checks), not from the printed inlay or
instructions, which we do not have. The technical detail is in `notes/03-level-map.md`; gaps are listed at the end.
If you have the original manual or remember the game, add to it.

## The object of the game
You are **Colin**, riding a motorbike round a small town seen from above. The messages suggest Colin is asleep and
dreaming: the game ends with "It's eight o'clock", "You've woken yourself up", "You've run out of fuel" or a win, and a
meter called **SLEEP** counts down as you crash.

The goal is to **find Martin and get him to the airport before eight o'clock**.
- Martin is in one of the houses ("You've found Martin. Get him to the airport quick"). Once he is on board the bike is
  drawn with a passenger (the second sprite set).
- Ride him to tile (105, 27), beside the airport terminal in the top right (a control tower, flags, and a red
  aeroplane parked next to it). You get "You're here just in time. WELL DONE, COLIN" and **50 points**.
- **Every ending starts a new game**: the finish, eight o'clock, "woken yourself up" and "out of fuel" differ only in the
  two lines of message ("It's eight o'clock" / "Time to get up Colin", "You've woken yourself up" / "You are so clumsy, Colin",
  "You've run out of fuel" / "Time to wake up colin", "You're here just in time" / "WELL DONE, COLIN") and, for the finish, a different tune.
  The messages take about 8.6 s, the tune about 7 s, then the next game starts. The high score is kept.

## How long you have
- The day lasts **3,600 game passes** (a pass is one step of the main loop); the hands on the clock at the bottom left move
  as it runs, and at eight o'clock the day is over.
- **SLEEP starts at 50.** Every crash costs 1; every 300 passes you get **5 back**, up to 50.
- **Fuel:** a full tank (an 18-step gauge at the bottom right) lasts about 512 passes at full speed and longer when you
  go slower. Three fixed fuel cans, at (111,19), (103,51) and (23,76), refill it, and they come back every 300 passes.

## What Colin can do
- **Ride in four directions** on roads and pavements only. Keys: **N left, M right, A up, Z down, Space** (the menu also
  offers Kempston, Sinclair (6 left, 7 right, 9 up, 8 down, 0 fire), Fuller and Cursor (5 left, 8 right, 7 up, 6 down, Space)). On the tape you first see the KP Skips
  advert and the title screen, then "Select Controls". The bike turns to face a new direction first, then moves one tile.
- **Speed:** hold a key and the bike speeds up over about 55 passes; let go and it coasts and slows. It is road-only:
  grass, fences, houses and the lake stop it (no penalty).
- **Collect KP Skips crisp packets** (yellow): 30 in the town, **2 points** each.
- **Refuel at fuel cans** (red): "Fill up with petrol".
- **Park at a house and go in.** Each house has a door marked by two invisible road tiles. Hold **Space** as the front of
  the bike reaches the door: the bike is parked on its stand, Colin is shown walking into the doorway (five frames, shrinking as he goes in) and then you see the inside of the house, a 12 x 12 room with
  furniture and whatever it holds. A visit is worth **3 points**; if there is nothing new, "No items in this house". Items score **10 points** each, and **Martin 100**.

## The items (inventory byte `$5B07`)
| Bit | Item | What it does |
|---|---|---|
| 0 | **Headlamp** | "You can see in the dark". Without it the dark area (bottom-left of the map) is drawn blank. |
| 1 | **New tyres** (special wheels) | "Good for oily roads". Oil slicks do no harm. |
| 2 | **Snorkel** | "That may come in handy". Needed with the periscope to ride into the lake. |
| 3 | **Periscope** | "Can you go in the water?" Needed with the snorkel. |
| 4 | **Turbo DIY kit** | "It is very easy to fit". **Does nothing**: no part of the program uses it. Just 10 points. |
| 5 | **Martin** | The passenger. Delivering him to the airport wins. |
| 6 | **Friend's mum** | "Stay for some tea please". **A tea break:** 600 passes of game time pass at once (a sixth of the day), you get 10 SLEEP back and the fuel cans return. Visit again for more. |

Items are placed when a game starts by a seeded random generator, so a fresh load gives **the same layout every time**
(checked: it reproduces the first game's items, all 30 crisp packets and all 20 oil slicks exactly). In the first game: the
passenger is in house 242, the headlamp in 226, the new tyres in 246, the snorkel in 227, the periscope in 231, the Turbo kit
in 214, and the friend's mum in 207, 233, 234, 236 and 247 (door numbers; see `assets/houses.json`).

## The hazards
- **Other road users:** 20 vans, motorbikes and saloon cars in several colours. Hitting one beeps, flashes the play area and
  **costs 1 SLEEP**.
- **Oil slicks:** 20 are placed. Riding onto one at full speed without the new tyres shows "Hit oil much too fast! You need
  special wheels" and costs 1 SLEEP. Slower is safe.
- **Water:** the big lake in the middle (an island with two houses sits in it). Riding in without both the snorkel and the
  periscope is a crash (1 SLEEP); with both the bike swims.
- **The dark area:** the bottom-left of the map. Entering shows "You enter the dark area. You need a headlamp"; without the
  headlamp you cannot see the map there (the headlamp lets you see more of the map). Leaving shows "You leave the dark area".
- **Running out of fuel, running out of SLEEP, or the clock reaching eight** all end the day.

Some places can only be reached with certain items: the lake (and its island) needs the snorkel and periscope, the dark area
needs the headlamp, and oily roads need the special wheels or a slow approach.

## The screen
The play area is 18 x 18 tiles at the top left. On the right are HIGH and SCORE, SLEEP, a speedometer and a picture of the
bike. At the bottom are the clock, the blue message bar and the FUEL gauge. Messages appear in the middle of the blue bar, one line at a time, each scrolling up into place. **The picture of the bike shows your equipment:** the
headlamp adds a beam of light in front, the new tyres fatter wheels, the snorkel and periscope a pipe each, and the Turbo kit a small badge. Scores: crisps 2, a house visit 3, an item 10 (Martin 100), the finish 50.

## Not known yet (please add anything you remember)
- Where the items are in a different game (the decoded layout is the first game's).
- Where Martin is if the layout changes per level (the decoded layout is the first game's).
- What "You are so clumsy, Colin", "Time to get up Colin" and "Time to wake up colin" are for.
- How the other vehicles move, and the real speed of a pass.
- Anything on the original inlay (story text, scoring) that is not visible in the program.
