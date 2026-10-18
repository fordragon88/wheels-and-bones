# Wheels & Bones — all quests

Generated from `game.py` by `python docs/export_quests.py` — do not edit by hand.

Found a mistake? Note the quest number and step, what is wrong and how it should be (or use the ⚑ flag in the game — it attaches a screenshot).

## Workshop jobs

### 1. Rear wheel puncture
- **Client:** Martin (you)  
- **Wheelchair:** Invacare 9000 (standard folding)  
- **Symptom:** The rear wheel is flat: the chair “dips” its nose and rolls heavily. And it's a long way to the party.

**Inspection clues (what the player sees)**

- *Tire* — The tire is soft; there's a mark from something sharp on the side.
- *Inner tube* — The inner tube is completely flat.
- *Valve* — The valve is intact, but there's no air.
- *Rim* — The rim is true, no dents.
- *Wheel lock* — The wheel lock is fine — it has nothing to do with this.
- *Spokes* — The spokes ring normally.

**Diagnosis options**

- ✅ (correct) Punctured tube — remove the tire, replace/patch the tube
- ❌ Bent rim — The rim is true. Rims rarely bend, and only from a hard impact.
- ❌ Loose wheel lock — The wheel lock doesn't cause a flat tire.

**Repair steps**

1. Let the remaining air out completely through the valve.  
   *Tool:* Hands → *Part:* Valve  
   *Hint:* Barty: “The master always let the spirit out of the wheel first. Solemnly.”  
   *After the step:* With the tube deflated, the tire comes off easily.
2. Pry the tire bead up with a tire lever over a spoke, hook it onto the spoke.  
   *Tool:* Tire lever → *Part:* Tire (also accepted: Rim)  
   *Hint:* Barty: “He did it with two shoehorns! ...or not.”  
   *After the step:* Tire levers are plastic — hold them at the end; they break easily.  
   *If wrong:* The tire bead is pried up with a tire lever, between the rim and the tire.
3. Run a second tire lever around the wheel — take one bead off the rim.  
   *Tool:* Tire lever → *Part:* Tire  
   *After the step:* Remove only one bead; leave the other on the rim.
4. Pull the tube out of the tire.  
   *Tool:* Hands → *Part:* Inner tube  
   *After the step:* Carefully, so you don't snag the valve.
5. Run a finger inside the tire and along the rim — remove glass/splinters.  
   *Tool:* Hands → *Part:* Tire (also accepted: Rim)  
   *Hint:* Barty: “Oh, I remember this — he once found a coin in here. Moneybags.”  
   *After the step:* Miss a shard and the new tube will puncture right away.
6. Pump a little air into the new tube through the valve so it keeps its round shape.  
   *Tool:* Pump → *Part:* Inner tube (also accepted: Valve)  
   *After the step:* A half-inflated tube sits in the tire more easily and evenly.
7. Guide the valve through the hole in the rim.  
   *Tool:* Hands → *Part:* Valve (also accepted: Rim)
8. Lay the tube into the tire all the way around.  
   *Tool:* Hands → *Part:* Inner tube (also accepted: Tire)  
   *After the step:* The tube should sit evenly, with no twists.
9. Tuck the tire bead in by hand, working around from the valve.  
   *Tool:* Hands → *Part:* Tire  
   *After the step:* Push the last section on with your palms; a tire lever is a last resort here — it easily pinches the tube.
10. Check that the valve stands straight, not at an angle.  
   *Tool:* Eyes → *Part:* Valve  
   *After the step:* A crooked valve will chafe through over time.
11. Attach the pump to the valve and inflate to the pressure printed on the tire sidewall.  
   *Tool:* Pump → *Part:* Tire (also accepted: Valve)  
   *Mini-game:* pump  
   *Hint:* Barty: “Pump until it rings! ...not until it bursts, of course.”  
   *After the step:* Correct pressure reduces rolling resistance and strain on the shoulders.

**Test:** You spin the wheel — it holds air and rolls smoothly and easily.  
**What you learn:** The recommended pressure is printed on the tire sidewall. Low pressure = harder pushing and more strain on the shoulders (injury risk). Check pressure once a week.  
**Client says:** Martin: “I... fixed a wheelchair? Hey, this is actually kind of addictive.”  

---

### 2. Caster flutter — Variant 1/2
- **Client:** Aelin the Elf  
- **Wheelchair:** Progeo Ego (active, rigid frame)  
- **Symptom:** At speed the front wheel starts to shake rapidly and the chair veers to one side.

**Inspection clues (what the player sees)**

- *Caster (front)* — The front wheel wobbles; long hair is wound around the axle (elven!).
- *Caster stem* — The caster stem wobbles in its housing — there's play. The fork mounting itself is tight.
- *Tire* — The rear tire is properly inflated.
- *Wheel lock* — The wheel lock holds.
- *Bearing* — The rear bearing is quiet.

**Diagnosis options**

- ✅ (correct) Caster stem play + dirt/hair in the axle
- ❌ Loose fork mounting bolts — The fork is firmly seated — it's the stem itself that has play.
- ❌ Flat rear tire — The tire is fine. The shaking comes from the front.

**Repair steps**

1. Remove the caster wheel from the fork.  
   *Tool:* Hex key → *Part:* Caster (front)  
   *After the step:* It's usually held by a single bolt.
2. Clean hair and dirt out of the caster axle with tweezers/brush.  
   *Tool:* Brush/tweezers → *Part:* Caster (front)  
   *Hint:* Barty: “So much hair — as if someone's been shedding for centuries. Ah yes, that's me.”  
   *After the step:* Wound-up hair is a common reason a caster won't spin freely.
3. Spin the caster wheel by hand: does it turn freely without wobbling?  
   *Tool:* Hands → *Part:* Caster (front)  
   *After the step:* If it wobbles, the tread is worn or it won't spin freely, the wheel needs replacing.
4. Tighten the caster stem bearing assembly until there's slight friction.  
   *Tool:* Adjustable wrench → *Part:* Caster stem  
   *Hint:* Barty: “Tighter! Even tighter! ...actually no, he cursed later when it seized.”  
   *After the step:* A little more friction in the stem damps flutter.  
   *If wrong:* The caster stem assembly is tightened with an adjustable wrench.
5. Bolt the caster wheel back onto the fork.  
   *Tool:* Hex key → *Part:* Caster (front)  
   *After the step:* Overtighten the mount and the wheel will bind.
6. Spin and rock the caster: it turns freely with no play.  
   *Tool:* Hands → *Part:* Caster (front) (also accepted: Caster stem)  
   *After the step:* Spins freely with no play — the bolt is tightened just right.

**Test:** A run across the workshop — no flutter, the chair tracks straight.  
**What you learn:** Three causes of caster flutter: high speed, stem play and misalignment. A little friction in the stem bearing stops the shaking; clean hair from the axle regularly.  
**Client says:** Aelin: “Now it glides silently, like an elven boat. My thanks!”  

---

### 2. Caster flutter — Variant 2/2
- **Client:** Aelin the Elf  
- **Wheelchair:** Progeo Ego (active, rigid frame)  
- **Symptom:** At speed the front wheel starts to shake rapidly and the chair veers to one side.

**Inspection clues (what the player sees)**

- *Caster (front)* — The wheel is intact, the axle is clean and it spins freely — but the whole fork wobbles about.
- *Caster stem* — The stem has no play — it's the fork mounting itself that's loose.
- *Bolts/nuts* — The caster fork mounting bolts are noticeably loose.
- *Tire* — The rear tire is fine.
- *Bearing* — The bearings are quiet.

**Diagnosis options**

- ✅ (correct) Loose caster fork mounting bolts
- ❌ Stem play + hair in the axle — The stem is tight, the axle is clean — it's not them.
- ❌ Flat rear tire — The tire is fine. The shaking comes from the front.

**Repair steps**

1. Rock the caster fork by hand — find the play.  
   *Tool:* Hands → *Part:* Caster (front) (also accepted: Caster stem)  
   *After the step:* The fork rocks on a sound stem — so it's the mounting.
2. Tighten the fork mounting bolts.  
   *Tool:* Hex key → *Part:* Bolts/nuts  
   *Hint:* Barty: “Tap it with a hammer, it'll seat itself!” — no. Only the hex key.  
   *After the step:* Hex key of exactly the right size: a stripped bolt has to be drilled out.
3. Check: the caster spins freely, no play.  
   *Tool:* Hands → *Part:* Caster (front)  
   *After the step:* Too tight and it binds; too loose and it'll shake loose again.

**Test:** A run across the workshop — the front is solid, the shaking is gone.  
**What you learn:** Front-end shaking isn't always the stem or bearing: check the fork mounting first. Tighten bolts with a correctly sized wrench and don't overtighten.  
**Client says:** Aelin: “Good as new! And I was about to replace the whole wheel.”  

---

### 3. Wheel lock doesn't hold
- **Client:** Durgin the Dwarf  
- **Wheelchair:** Progeo Tekna Advance (active folding)  
- **Symptom:** A heavyset dwarf complains: the chair rolls down slopes even with the lock engaged.

**Inspection clues (what the player sees)**

- *Tire* — The rear tire is a bit low — that's already suspicious.
- *Wheel lock* — The wheel lock shoe doesn't press the tire properly; the mount has shifted slightly.
- *Frame* — The frame is intact.
- *Bolts/nuts* — The wheel lock clamp bolts are slightly loose.
- *Rear wheel* — The wheel spins freely.

**Diagnosis options**

- ✅ (correct) Check tire pressure first, then the wheel lock mounting
- ❌ Replace the whole wheel lock assembly right away — Simple causes first: pressure and mounting.
- ❌ Bent frame — The frame is fine.

**Repair steps**

1. Check tire pressure — a soft tire “pulls away” from the lock shoe.  
   *Tool:* Pressure gauge → *Part:* Tire (also accepted: Rear wheel)  
   *Hint:* Barty: “Go straight for the bolts!” ...nope — pressure first.  
   *After the step:* The #1 cause of “the lock won't hold” is low tire pressure.
2. Top up the tire through the valve to the correct pressure.  
   *Tool:* Pump → *Part:* Tire (also accepted: Valve, Rear wheel)
3. Tighten the wheel lock mechanism bolts.  
   *Tool:* Hex key → *Part:* Wheel lock (also accepted: Bolts/nuts)  
   *After the step:* Don't overdo it: overtighten them and the lock gets stiff to engage.
4. Didn't help? Loosen the two clamp bolts holding the lock to the frame.  
   *Tool:* Hex key → *Part:* Wheel lock (also accepted: Bolts/nuts)  
   *After the step:* The clamp lets you slide the whole assembly.
5. Slide the wheel lock toward the tire: 3–6 mm gap between shoe and tire when released.  
   *Tool:* Hands → *Part:* Wheel lock  
   *Mini-game:* gap  
   *After the step:* That's 1/8–1/4 inch — the working gap per the manual. Set it while the clamp is loose.
6. Tighten the clamp bolts, alternating between them (evenly).  
   *Tool:* Hex key → *Part:* Wheel lock (also accepted: Bolts/nuts)  
   *After the step:* Even tightening keeps the assembly straight.
7. Engage the wheel lock: the shoe presses firmly into the tire.  
   *Tool:* Hands → *Part:* Wheel lock  
   *After the step:* The engaged shoe holds the wheel — the chair won't roll away.
8. Release the wheel lock and spin the wheel: the shoe doesn't touch the tire.  
   *Tool:* Hands → *Part:* Tire (also accepted: Wheel lock, Rear wheel)  
   *After the step:* The released shoe doesn't rub — the wheel spins freely.

**Test:** The dwarf sets the lock and leans hard — the wheel won't budge. It holds!  
**What you learn:** “The wheel lock won't hold” is most often fixed with tire pressure and tightening/shifting the mount. Use a hex key of EXACTLY the right size: a stripped bolt has to be drilled out.  
**Client says:** Durgin: “Now that's proper dwarf work. Solid!”  

---

### 4. Rattle: loose spokes
- **Client:** Tilly the Fairy  
- **Wheelchair:** Progeo Exelle Junior (pediatric)  
- **Symptom:** Something rattles while rolling and the rear wheel wobbles a bit — the tiny fairy is worried.

**Inspection clues (what the player sees)**

- *Spokes* — Three spokes feel softer than their neighbors — they've come loose.
- *Rim* — The rim wanders by a fraction of a millimeter — slight wheel wobble.
- *Bolts/nuts* — A few bolts on the frame have worked loose.
- *Bearing* — The bearing is quiet — it's a rattle, not a whine.
- *Inner tube* — The inner tube holds pressure.

**Diagnosis options**

- ✅ (correct) Loose spokes (and check the bolts too)
- ❌ Dead bearing — A bearing whines or knocks; this is a rattle.
- ❌ Flat inner tube — The inner tube is fine.

**Repair steps**

1. Ping test: run a pencil across the spokes while turning the wheel.  
   *Tool:* Pencil → *Part:* Spokes  
   *Mini-game:* ping  
   *Hint:* Barty: “How musical! He used to play whole tunes this way. Bad ones.”  
   *After the step:* A clear “ping” = fine, a dull sound = a loose spoke.
2. Squeeze neighboring spokes in pairs — confirm by feel the ones that sounded dull.  
   *Tool:* Hands → *Part:* Spokes
3. Tighten the loose spokes' nipples a little at a time with a spoke wrench.  
   *Tool:* Spoke wrench → *Part:* Spokes (also accepted: Rim)  
   *Hint:* Barty: “Crank it hard, half a turn at a time... fine, little by little.”  
   *After the step:* Little by little and evenly: spokes are tensioned to a set value; pros use a truing stand.
4. Tighten the loose bolts/nuts on the frame.  
   *Tool:* Hex key → *Part:* Bolts/nuts  
   *After the step:* A stripped bolt is replaced with one of the same strength grade (number on the head).

**Test:** You roll the wheel — the rattle is gone and the rim runs true.  
**What you learn:** Spoke tension is checked with a ping test. Tension them to a set value and evenly — overtighten and the rim wobbles. Bolts are only replaced with ones of equal strength grade.  
**Client says:** Tilly: “So quiet! Now you can hear me buzz. Thank you!”  

---

### 5. Whine at the rear wheel — Variant 1/2
- **Client:** Gra the Orc  
- **Wheelchair:** Progeo Noir 2.0 (rigid frame)  
- **Symptom:** Rolling makes a whine and a rustle; the rear wheel turns stiffly and stops quickly.

**Inspection clues (what the player sees)**

- *Bearing* — The bearing hums and sticks slightly when turning.
- *Axle (QR)* — Dirt and hair are wound around the axle.
- *Rear wheel* — The wheel barely spins and stops right away.
- *Wheel lock* — The wheel lock is released and not rubbing.
- *Tire* — The tire is inflated.

**Diagnosis options**

- ✅ (correct) Axle bearing dirty/worn
- ❌ Wheel lock rubs the tire — The lock is released. The sound comes from the hub.
- ❌ Flat tire — The tire is fine.

**Repair steps**

1. Remove the rear wheel: press the quick-release axle button and pull.  
   *Tool:* Hands → *Part:* Axle (QR) (also accepted: Rear wheel)  
   *After the step:* Quick-release: the button at the end of the axle frees the wheel.
2. Clean hair/dirt out of the axle and bearing with tweezers/a brush.  
   *Tool:* Brush/tweezers → *Part:* Bearing (also accepted: Axle (QR))  
   *Hint:* Barty: “With an orc, in there... don't ask. Just clean.”  
   *After the step:* Hair on the axle is a common cause of whining and stiff rolling.
3. Assess the bearing: knocking/whining/sticking = replace it.  
   *Tool:* Hands → *Part:* Bearing  
   *After the step:* Noise is the first sign of a dying bearing.
4. Replace the bearing, since it's noisy and sticking.  
   *Tool:* Socket wrench → *Part:* Bearing  
   *After the step:* A worn bearing can't be fixed — only replaced.
5. Lightly lubricate the axle.  
   *Tool:* Lubricant → *Part:* Axle (QR)  
   *Hint:* Barty: “Douse everything in oil!” — no, lubricant only where it's needed.  
   *After the step:* Do NOT pressure-wash the wheelchair — it blasts grease out of sealed bearings and rust follows.
6. Refit the wheel: press the axle button and push the axle fully home.  
   *Tool:* Hands → *Part:* Axle (QR) (also accepted: Rear wheel)  
   *After the step:* Let go of the button — the axle's locking balls must pop out and lock the wheel.
7. Pull the wheel away from the frame: the axle has locked and the wheel won't come off.  
   *Tool:* Hands → *Part:* Rear wheel (also accepted: Axle (QR))  
   *After the step:* A quick-release axle that hasn't clicked home can let the wheel come off while riding.

**Test:** The wheel spins up and turns long and quietly. The orc is pleased.  
**What you learn:** The first sign of a dying bearing is noise (whine/knock/grinding); it's replaced as a whole. Pressure washing kills sealed bearings: water blasts the grease out.  
**Client says:** Gra: “QUIET. GOOD. Gra likes quiet.”  

---

### 5. Whine at the rear wheel — Variant 2/2
- **Client:** Gra the Orc  
- **Wheelchair:** Progeo Noir 2.0 (rigid frame)  
- **Symptom:** Rolling makes a whine and a rustle; the rear wheel turns stiffly and stops quickly.

**Inspection clues (what the player sees)**

- *Bearing* — The bearing turns smoothly and quietly — not the culprit.
- *Axle (QR)* — The axle is clean.
- *Rear wheel* — The wheel drags on one side — the side with the lock.
- *Wheel lock* — The lock shoe sits right against the tire and catches it even when released.
- *Tire* — The tire is inflated, but there's a wear stripe on the side — something was rubbing.

**Diagnosis options**

- ✅ (correct) Wheel lock slipped and rubs the tire
- ❌ Axle bearing worn — The bearing is quiet and smooth. The sound is outside, by the tire.
- ❌ Flat tire — The tire is inflated.

**Repair steps**

1. Loosen the two wheel lock clamp bolts.  
   *Tool:* Hex key → *Part:* Wheel lock  
   *After the step:* The clamp lets you slide the whole unit along the frame.
2. Slide the wheel lock away from the tire: 3–6 mm gap between shoe and tire when released.  
   *Tool:* Hands → *Part:* Wheel lock  
   *Mini-game:* gap  
   *Hint:* Barty: “Why not just remove the lock entirely?” — and roll downhill without one? No.  
   *After the step:* Working gap is 3–6 mm: no rubbing, but it grips when engaged. Set it while the clamp is loose.
3. Tighten the clamp bolts, alternating between them.  
   *Tool:* Hex key → *Part:* Wheel lock  
   *After the step:* Even tightening keeps the assembly straight.
4. Release the wheel lock and spin the wheel: the shoe doesn't touch the tire.  
   *Tool:* Hands → *Part:* Tire (also accepted: Wheel lock, Rear wheel)  
   *After the step:* The wheel spins for a long time without a scrape.
5. Engage the wheel lock: the shoe presses firmly into the tire.  
   *Tool:* Hands → *Part:* Wheel lock  
   *After the step:* The engaged lock holds — the wheel doesn't turn.

**Test:** The wheel spins long and freely; the lock grips only when asked.  
**What you learn:** “Whines and drags” isn't always the bearing: first check whether the wheel lock rubs. Working shoe gap is 3–6 mm; a rubbing lock eats the tire and the user's arm strength.  
**Client says:** Gra: “QUIET. ROLLS. Gra was wrong about the bearing. Gra is glad.”  

---

### 6. Leaking air cushion
- **Client:** Bomm the Troll  
- **Wheelchair:** Invacare 9000 XDT (heavy-duty, up to 159 kg)  
- **Symptom:** The cushion deflates; the troll “bottoms out” all the way to the seat base.

**Inspection clues (what the player sees)**

- *Cushion* — The air cushion (ROHO-type) slowly deflates — there's a puncture somewhere.
- *Seat* — The seat sling is fine.
- *Frame* — The frame is intact.
- *Valve* — The cushion valve holds — it's not leaking.

**Diagnosis options**

- ✅ (correct) Air cushion puncture
- ❌ Sagging seat sling — The sling is fine; the sinking is from the deflated cushion.
- ❌ Loose backrest — Bomm sinks down to the seat base, not backwards — and on inspection the cushion was losing air.

**Repair steps**

1. Overinflate the cushion through its valve — pump it harder than usual.  
   *Tool:* Pump → *Part:* Cushion (also accepted: Valve)  
   *After the step:* An overinflated cushion is easier to check for punctures.
2. Submerge the cushion in a bowl of water and find the puncture by the bubbles.  
   *Tool:* Bowl of water → *Part:* Cushion  
   *Hint:* Barty: “Drown it! ...in a good way, for diagnosis.”  
   *After the step:* Bubbles show the exact spot of the leak.
3. Mark the puncture (toothpick/marker).  
   *Tool:* Hands → *Part:* Cushion
4. Dry and degrease the patch area with a cloth.  
   *Tool:* Cloth → *Part:* Cushion  
   *After the step:* A patch only sticks to a clean, dry surface.
5. Apply a patch from the patch kit and press it down.  
   *Tool:* Patch → *Part:* Cushion  
   *After the step:* A ROHO kit always includes a patch.
6. Inflate the cushion through the valve until it starts to arch upward slightly.  
   *Tool:* Pump → *Part:* Cushion (also accepted: Valve)  
   *After the step:* ROHO instructions: inflate with extra air first; fine-tune with the person sitting on the cushion.
7. Bomm sits down. Ask his permission and slide your hand under his lowest pelvic bone.  
   *Tool:* Hands → *Part:* Cushion  
   *After the step:* ROHO hand check: your hand between the cushion and the pelvis tells you how much air is left.
8. Let air out through the valve until your fingertips under the pelvis can just move.  
   *Tool:* Hands → *Part:* Valve (also accepted: Cushion)  
   *Hint:* Barty: “Pump till it rings!” — no, here it's the opposite: overinflating is harmful.  
   *After the step:* 1.5–2.5 cm of air under the lowest pelvic bone (~1 finger). Bottoming out risks pressure sores; an overinflated cushion is like sitting on a rock.

**Test:** The troll sits down — the cushion holds and doesn't bottom out.  
**What you learn:** A properly inflated pressure-relief cushion prevents pressure sores: keep a ~1 finger gap under the pelvic bones. Find punctures by bubbles in water and patch them.  
**Client says:** Bomm: “Soft! Bomm sit. Bomm not fall. Bomm friend.”  

---

### 7. Seat elevator won't rise — Variant 1/2
- **Client:** Zix the Goblin Mechanic  
- **Wheelchair:** Quantum Edge 4 (mid-wheel drive, power seat elevator)  
- **Symptom:** Zix selects lift mode on the joystick, pushes the joystick forward — and the seat won't budge. “I only tweaked it a little! Well, maybe not a little. I need to reach the top shelf with the nuts, and the elevator's on strike!”

**Inspection clues (what the player sees)**

- *Seat elevator* — The scissor mechanism is folded, clean, nothing stuck between the parts.
- *Seat lift actuator* — The actuator housing is intact. But its connector at the electronics block is pulled out half a finger's width — the latch won't hold.
- *Connectors/wiring* — The elevator wiring harness is cinched with new zip ties to a homemade cup holder and pinched by the seat frame at the bend. The braiding is still intact for now.
- *Joystick* — The seat screen opens, lift mode can be selected, no error codes. The lockout indicator is green.
- *Battery* — The charge indicator is full — Zix charged it all night.
- *Flip-up armrest* — On the armrest is a brand-new “Zix-Turbo” cup holder, bolted on tight.

**Diagnosis options**

- ✅ (correct) Signal isn't reaching the actuator: connector not fully seated, harness pinched — power down, push in until it clicks, reroute the harness
- ❌ The factory lift lockout has tripped — If it were locked out, the indicator would be red or yellow, but it's green.
- ❌ Battery is dead — Charge is full, and if drained the Q-Logic 3 would show error 20 “Undervoltage”.

**Repair steps**

1. Put the wheelchair on the level floor of the workshop: nothing above the seat, clear space next to the scissor mechanism.  
   *Tool:* Hands → *Part:* Seat elevator  
   *After the step:* Edge 4 manual: the elevator — only on level ground, not under a table or shelf.
2. Turn on the joystick.  
   *Tool:* Hands → *Part:* Joystick
3. Press key 2 to open the seat screen and select “lift”.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* Lift mode is selected — the joystick now moves the seat.
4. Push the joystick forward.  
   *Tool:* Hands → *Part:* Joystick (also accepted: Seat elevator)  
   *After the step:* The seat doesn't move. Now read the joystick display — it will tell us whether it's a lockout or a broken connection.
5. Look at the lockout indicator on the joystick.  
   *Tool:* Eyes → *Part:* Joystick  
   *Mini-game:* meter  
   *After the step:* The indicator and codes are the first thing you check before digging into the wiring.
6. Turn off the joystick.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* Connectors are only touched with the chair powered down: switch off the joystick first, then the breaker.
7. Take off the rear cover: turn the two yellow clips (no tools).  
   *Tool:* Hands → *Part:* Battery  
   *After the step:* Under the cover is the battery tray with the main circuit breaker.
8. Press the yellow button on the circuit breaker — the batteries are disconnected from the system.  
   *Tool:* Hands → *Part:* Battery  
   *After the step:* The circuit breaker on the Edge 4 doubles as the battery disconnect.
9. Inspect the scissor mechanism from the outside, with a flashlight. Keep hands out of the scissors.  
   *Tool:* Eyes → *Part:* Seat elevator  
   *Hint:* Barty: “Stick your paw between the scissors and give it a push — it's just being lazy!” — no! That's a pinch point: you don't put your hands in the mechanism even on a switched-off wheelchair.  
   *After the step:* The scissors are pinch points. We look with our eyes, not our fingers.
10. Inspect the actuator connector: is the housing intact, the contacts free of green corrosion?  
   *Tool:* Eyes → *Part:* Seat lift actuator (also accepted: Connectors/wiring)  
   *After the step:* Intact and clean — you can plug it in. Cracked or scorched — we don't repair it; it goes to a certified technician.
11. Push the actuator connector in until the latch clicks.  
   *Tool:* Hands → *Part:* Seat lift actuator (also accepted: Connectors/wiring)  
   *After the step:* The latch clicked — vibration won't pull the connector out any more.
12. Move the lift harness from the cup-holder zip ties to the factory mounting points, away from the seat frame.  
   *Tool:* Hands → *Part:* Connectors/wiring  
   *After the step:* The elevator moves up and down: the harness needs free travel. Chafed braiding isn't taped up — it's replaced at the service center.
13. Flip the circuit breaker lever down — battery power is back.  
   *Tool:* Hands → *Part:* Battery  
   *After the step:* The breaker button disconnects the batteries; the lever down reconnects them.
14. Put the rear cover back and close both yellow clips.  
   *Tool:* Hands → *Part:* Battery  
   *After the step:* Without the cover, dirt gets into the tray and fingers wander into the wiring.
15. Turn on the joystick.  
   *Tool:* Hands → *Part:* Joystick
16. Press key 2 to open the seat screen and select “lift”.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* Lift mode is selected — the joystick now moves the seat.
17. Push the joystick forward: the seat rises.  
   *Tool:* Hands → *Part:* Joystick (also accepted: Seat elevator)  
   *After the step:* The seat went up — so the command reaches the actuator.
18. Look at the joystick display: the iLevel icon and a yellow indicator — speed is limited, about 3 km/h.  
   *Tool:* Eyes → *Part:* Joystick  
   *After the step:* The manual says to check the speed reduction system before every trip with the seat raised.
19. Lower the seat fully with the joystick, making sure the harness doesn't stretch.  
   *Tool:* Hands → *Part:* Seat elevator (also accepted: Joystick, Connectors/wiring)  
   *After the step:* Outdoors, on a ramp and over a threshold — only with the seat lowered.

**Test:** The seat rises smoothly, the yellow indicator lights up, Zix slowly rolls to the shelving and takes a jar of nuts off the top shelf. It lowers — the harness lies free.  
**What you learn:** A green indicator and silence mean there's no lockout and the command is lost along the way. The Edge 4 manual says to check that all connectors are tight and the harness isn't pinched by the seat frame; a cracked connector or chafed harness is replaced only at the service center.  
**Client says:** Zix: “I'll keep the cup holder, but I won't touch the wires anymore. Almost. Thanks, bony!”  

---

### 7. Seat elevator won't rise — Variant 2/2
- **Client:** Zix the Goblin Mechanic  
- **Wheelchair:** Quantum Edge 4 (mid-wheel drive, power seat elevator)  
- **Symptom:** Zix selects lift mode on the joystick, pushes the joystick forward — and the seat won't budge. “I only tweaked it a little! Well, maybe not a little. I need to reach the top shelf with the nuts, and the elevator's on strike!”

**Inspection clues (what the player sees)**

- *Seat elevator* — The scissors are folded, clean, nothing stuck.
- *Seat* — The seat is tilted back, the backrest reclined almost flat: Zix “upgraded” the wheelchair to “siesta mode” and dozed in it.
- *Joystick* — A RED lockout indicator is lit on the screen; in lift mode the seat doesn't move.
- *Seat lift actuator* — The actuator connector is seated tight, the cable intact.
- *Battery* — Charge is full.
- *Freewheel lever* — The freewheel levers are up — the motors are in drive mode.

**Diagnosis options**

- ✅ (correct) Factory lockout: tilt or recline greater than 20° prohibits lifting — return the seat closer to level
- ❌ The lift actuator burned out — A red indicator isn't a breakdown, it's a lockout based on seat position.
- ❌ Motors in freewheel — The levers are up, and freewheel doesn't interfere with the elevator.

**Repair steps**

1. Check: the wheelchair is on level ground, nothing above, clear space around the scissors and backrest.  
   *Tool:* Eyes → *Part:* Seat elevator (also accepted: Seat)  
   *After the step:* The backrest and seat are about to move — they need room.
2. Turn on the joystick.  
   *Tool:* Hands → *Part:* Joystick
3. Press key 2 to open the seat screen and select “lift”.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* Lift mode is selected — the joystick now moves the seat.
4. Push the joystick forward.  
   *Tool:* Hands → *Part:* Joystick (also accepted: Seat elevator)  
   *After the step:* The seat doesn't move. The joystick display will tell you first whether it's a fault or a safety lockout.
5. Look at the lockout indicator on the joystick.  
   *Tool:* Eyes → *Part:* Joystick  
   *Mini-game:* meter  
   *After the step:* The indicator color tells a fault from a safety lockout.
6. Use the joystick left-right to select seat tilt mode.  
   *Tool:* Hands → *Part:* Joystick  
   *Hint:* Barty: “Reprogram the lockout — and the elevator will move at any tilt!” — no! The manual explicitly forbids bypassing or reconfiguring factory lockouts: it's protection against tipping over.  
   *After the step:* We work with the standard modes — no “tricks”.
7. Use the joystick to reduce the seat tilt until the angle is 20° or less.  
   *Tool:* Hands → *Part:* Joystick (also accepted: Seat)  
   *Mini-game:* gap  
   *After the step:* Lifting is permitted only when tilt and recline are no more than 20°.
8. Use the joystick left-right to select backrest mode.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* Backrest mode is selected — now the joystick moves the backrest.
9. Use the joystick to bring the backrest closer to upright: recline no more than 20°.  
   *Tool:* Hands → *Part:* Joystick (also accepted: Seat)  
   *After the step:* A reclined backrest blocks the lift just like tilt.
10. Look at the indicator: red should change to green.  
   *Tool:* Eyes → *Part:* Joystick  
   *After the step:* Green — no limits, you can lift.
11. Use the joystick left-right to select “lift” mode.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* Lift mode is selected — the joystick now moves the seat.
12. Push the joystick forward: the seat rises and the iLevel icon appears on the joystick display.  
   *Tool:* Hands → *Part:* Joystick (also accepted: Seat elevator)  
   *After the step:* iLevel turns on by itself as soon as the seat starts moving up.
13. Look at the joystick display with the seat raised: the yellow indicator is on — speed is limited, about 3 km/h.  
   *Tool:* Eyes → *Part:* Joystick  
   *After the step:* If it says “iLevel not engaged” on level ground — don't use the elevator, see the service center.
14. Lower the seat all the way with the joystick.  
   *Tool:* Hands → *Part:* Joystick (also accepted: Seat elevator)  
   *After the step:* Outdoors, on a ramp and over a threshold — only with the seat lowered.

**Test:** The indicator is green, the seat glides up, the yellow lights up. Zix solemnly takes a jar of nuts off the top shelf and lowers back down.  
**What you learn:** On TRU-Balance systems the lift is locked out if the seat is tilted or the backrest is reclined more than 20°: the red Q-Logic 3 indicator is a safety lockout, not a fault. Return the angle — the indicator will turn green. A raised seat limits speed to about 3 km/h.  
**Client says:** Zix: “So ‘siesta mode’ and the elevator don't get along. I'll doze lower down. Thanks, bony!”  

---

### 8. Jerky joystick, torn boot
- **Client:** Mora the Sorceress  
- **Wheelchair:** Permobil M3 Corpus (mid-wheel drive)  
- **Symptom:** The wheelchair veers and jerks when steering; the rubber boot at the joystick base is torn. Mora was recently caught in a downpour.

**Inspection clues (what the player sees)**

- *Joystick knob* — The joystick sticks a little and doesn't always return to center.
- *Joystick boot* — The rubber boot at the base is torn — moisture may have gotten inside.
- *Connectors/wiring* — The joystick cable connector is loose.
- *Joystick* — The joystick beeps now and then; the display shows a joystick error (not a motor one).
- *Battery* — Charge is fine.

**Diagnosis options**

- ✅ (correct) Joystick: dry out, restart, clean, connector + replace the boot right away
- ❌ Burnt-out motor — The display shows a joystick error, not a motor error, and the joystick sticks — that's what makes it veer.
- ❌ Dead battery — Charge is normal — see the battery inspection.

**Repair steps**

1. Turn the chair off with the button on the joystick.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* Wet electronics aren't left powered: water + current = short circuit.
2. Blot the joystick with a dry cloth.  
   *Tool:* Cloth → *Part:* Joystick (also accepted: Joystick knob)  
   *Hint:* Barty: “Switch it on right away — let's see if it's alive!” — no: wet electronics are dried first.  
   *After the step:* Now the chair dries somewhere warm for ~12 h: a wet chair is never switched on.
3. Once it's dry, turn on the joystick.  
   *Tool:* Hands → *Part:* Joystick  
   *Hint:* Barty: “Turn it off and on again. The great magic of the 21st century, they say.”  
   *After the step:* A restart often “wakes up” the joystick.
4. Look at the joystick display: what code is it showing?  
   *Tool:* Eyes → *Part:* Joystick  
   *After the step:* The code tells you where to look: here it's the joystick, not a motor.
5. Switch the joystick off again — the rest is done with the chair off.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* With the power on, a deflected joystick is a command to drive.
6. Push the joystick knob over and let go: it should spring back to center by itself.  
   *Tool:* Hands → *Part:* Joystick knob  
   *After the step:* The chair is off, so handling the knob is safe. A bent knob or a weak spring is a job for a technician.
7. Wipe dirt and dust off the joystick with a dry cloth.  
   *Tool:* Cloth → *Part:* Joystick knob (also accepted: Joystick, Joystick boot)  
   *After the step:* Dirt at the base dulls the response.
8. Check and reseat the joystick cable connector (power off).  
   *Tool:* Hands → *Part:* Connectors/wiring  
   *After the step:* A loose cable connector is a common cause of jerking. Connectors are only touched with the chair switched off.
9. Replace the torn rubber joystick boot right away.  
   *Tool:* Hands → *Part:* Joystick boot  
   *Hint:* Barty: “Wrap it in tape!” — no, moisture will kill the board; it needs a new boot.  
   *After the step:* A torn boot lets moisture into the electronics — replace it right away, while the chair is off.
10. Turn on the joystick.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* New boot, tight connector — you can switch on.
11. Drive slowly and check the joystick response.  
   *Tool:* Hands → *Part:* Joystick (also accepted: Joystick knob)  
   *After the step:* If it still jerks, a technician calibrates it with a service programmer — don't reprogram it yourself.

**Test:** The joystick snaps back to center, the wheelchair drives straight, the boot is intact and dry.  
**What you learn:** A wet wheelchair is dried first and only then switched on. A joystick is fixed by restarting, cleaning and checking the connector (with the chair off), while calibration is done by a technician with a programmer. A torn boot is replaced right away: moisture ruins electronics. Leave complex electronics to a certified technician. Mora's Permobil M3 Corpus is mid-wheel drive, turns on the spot in ~1.1 m; the drive-wheel tires hold 200–250 kPa.  
**Client says:** Mora: “And no magic at all — just hands. Impressive, dead man.”  

---

### 9. Stalled; motor whine and veering
- **Client:** Grund the Golem  
- **Wheelchair:** Drive Trident HD (bariatric, front-wheel drive)  
- **Symptom:** The golem's heavy wheelchair stalled in the middle of the workshop (the power died), and before that a motor was whining and pulling to one side.

**Inspection clues (what the player sees)**

- *Freewheel lever* — Each motor has a freewheel lever with a yellow tip. They're up now — the motors are in drive mode, so the chair can't be pushed by hand.
- *Motor* — One motor whines louder than the other.
- *Connectors/wiring* — One motor's connector is loose.
- *Battery* — The battery is completely drained.
- *Axle (QR)* — Debris is wound around the axle.
- *Joystick* — The joystick is dark — no power.
- *Frame* — The frame is intact.

**Diagnosis options**

- ✅ (correct) Put it in freewheel and roll it away; then motor connectors, noise and charging the battery
- ❌ Drag it with the motors engaged — It won't roll with the motors engaged; you could damage the drive.
- ❌ Replace the motor right away — Simple things first: connectors, debris in the wheels, noise.

**Repair steps**

1. Switch the power off with the joystick's power button — even if the display is already dark: otherwise the chair will wake up switched on after charging.  
   *Tool:* Hands → *Part:* Joystick  
   *Hint:* Barty: “Pull the levers while it's moving!” — absolutely not; turn off the power first.  
   *After the step:* Freewheel is engaged ONLY with the power off, otherwise the controller throws an error.
2. On level ground, lower both freewheel levers (yellow tips).  
   *Tool:* Hands → *Part:* Freewheel lever  
   *After the step:* Freewheel disengages the motors — and the brakes! Never do this on a slope.
3. Roll the wheelchair to the workbench, standing to its side.  
   *Tool:* Hands → *Part:* Frame  
   *After the step:* No brakes in freewheel; stay to the side, not in front or behind.
4. Clear debris and anything wound up from the wheels and axle.  
   *Tool:* Brush/tweezers → *Part:* Axle (QR)  
   *After the step:* Obstructions in the wheels cause jerking and veering.
5. Reseat the motor and sensor connectors (refresh the contact).  
   *Tool:* Hands → *Part:* Connectors/wiring  
   *After the step:* A loose motor connector interrupts the signal — hence the whine and veering.
6. Return the freewheel levers up (drive mode).  
   *Tool:* Hands → *Part:* Freewheel lever  
   *After the step:* Always return the motors to drive mode — otherwise the brakes don't work.
7. Put the battery on charge with the stock charger.  
   *Tool:* Charger → *Part:* Battery (also accepted: Joystick)  
   *After the step:* The battery is completely drained — that's why it “died”.
8. After charging, turn on the joystick.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* Levers in drive mode — you can switch on.
9. Drive slowly and listen to the motors: both should sound the same.  
   *Tool:* Hands → *Part:* Joystick (also accepted: Motor)  
   *After the step:* Whine/knock = worn bearings or belt → see a certified technician.

**Test:** Battery charged, levers in drive mode, connectors tight. Grund drives a lap — the motors sound even, and the chair no longer pulls to the side.  
**What you learn:** Freewheel (yellow levers by the motors) lets you push the wheelchair by hand — only with the power OFF and on level ground, since the brakes are disengaged. Many “motor failures” are just loose connectors; motor and controller internals are a job for a technician.  
**Client says:** Grund: “GRUND. ROLLS. GRUND PLEASED.”  

---

### 10. Wheel lock doesn't hold on a slope
- **Client:** Yuki the Kitsune  
- **Wheelchair:** TiLite Aero Z (active, rigid frame)  
- **Symptom:** Yuki sets the chair on its locks by the coffee shop ramp, and it slowly creeps down: the left wheel slips under the lock.

**Inspection clues (what the player sees)**

- *Tire* — The left tire feels soft. The sidewall says 90–110 psi — clearly less.
- *Wheel lock* — In the locked position the lock shoe barely touches the left tire. On the frame tube there's a light mark: the clamp has slipped back from its old spot.
- *Bolts/nuts* — The two wheel-lock clamp screws (3/16" hex key) have worked loose.
- *Anti-tipper* — The anti-tippers are down and latched, the little wheels are intact. They have nothing to do with the lock.
- *Axle (QR)* — The quick-release axle is latched, the button is fully out, no play.
- *Spokes* — The spokes are evenly tensioned, the wheel doesn't wobble.

**Diagnosis options**

- ✅ (correct) Low tire pressure + slipped wheel-lock clamp: the shoe doesn't dig 5 mm (3/16") into the tire
- ❌ The lock is broken — replace the whole assembly — The lock is fine, it just shifted. Per the manual, pressure first, then clamp position.
- ❌ Loose quick-release axle — The axle is latched and has no play. The wheel turns because the lock isn't holding it.
- ❌ You need to pull the lock lever harder on descents — Locks are NOT brakes: you can't slow a moving chair with them. They only hold a parked one.

**Repair steps**

1. Check the pressure in both rear tires with a gauge and compare with the number on the sidewall.  
   *Tool:* Pressure gauge → *Part:* Tire  
   *Hint:* Barty: “The Master used to say: it's not the lever that holds, it's the air. I didn't understand then. I still don't understand.”  
   *After the step:* TiLite: check pressure EVERY week. If the tire is low, the lock on that side may slip.
2. Inflate the tire through the valve to the sidewall pressure. Wheel locks are only adjusted on an inflated tire!  
   *Tool:* Pump → *Part:* Tire (also accepted: Valve)  
   *Mini-game:* pump  
   *Hint:* Barty: “Pump, pump... I'm counting out loud. One. Two. Uh... lots.”  
   *After the step:* If you set the lock on a flat tire, it will work wrong after you pump it up.
3. Loosen, but do NOT unscrew, the two wheel-lock clamp screws.  
   *Tool:* Hex key → *Part:* Wheel lock (also accepted: Bolts/nuts)  
   *Hint:* Barty: “Unscrew them completely so they don't get in the way!”  
   *After the step:* 3/16" hex key (≈4.8 mm). The screws are loosened so the clamp can be slid along the frame.  
   *If wrong:* The clamp is loosened with a 3/16" hex key, and the screws are not unscrewed all the way.
4. Slide the clamp toward the tire so the locked shoe presses into the tire by at least 5 mm (3/16").  
   *Tool:* Hands → *Part:* Wheel lock  
   *Mini-game:* gap  
   *After the step:* TiLite: the shoe must press into the tire by at least 3/16" (≈5 mm), otherwise the chair may roll.
5. Tighten both clamp screws, one at a time.  
   *Tool:* Hex key → *Part:* Wheel lock (also accepted: Bolts/nuts)  
   *After the step:* After any adjustment, all fasteners are tightened securely before riding.
6. Release the wheel lock.  
   *Tool:* Hands → *Part:* Wheel lock  
   *After the step:* The wheel-lock lever goes to the “released” position.
7. Spin the wheel: the lock's shoe must not touch the tire.  
   *Tool:* Hands → *Part:* Tire (also accepted: Spokes)  
   *After the step:* TiLite checklist: when released the lock doesn't touch the tire, hinges free of wear and play.
8. Engage both wheel locks.  
   *Tool:* Hands → *Part:* Wheel lock  
   *After the step:* The shoe is pressed into the tire — now the push test.
9. Give the chair a hard push: the wheels under the locks must not turn.  
   *Tool:* Hands → *Part:* Tire (also accepted: Wheel lock)  
   *Hint:* Barty: “Great, now we can brake on the descent with these locks!” No! Wheel locks are not brakes.  
   *After the step:* The manual requires this test after every wheel lock adjustment.  
   *If wrong:* Simple check: push the chair by hand and watch the wheels.

**Test:** Yuki sets the wheelchair on its locks on the ramp and leans back: not a millimeter. Releases: the wheels spin freely and nothing rubs.  
**What you learn:** TiLite: an engaged wheel lock shoe presses into the tire at least 3/16" (≈5 mm). Adjust it only on a fully inflated tire (spec on the sidewall, check once a week). Wheel locks are not brakes, you must not slow a moving wheelchair with them, and the manual forbids slopes steeper than 10%.  
**Client says:** Yuki: “Three tails of thanks! Now I drink coffee instead of chasing the wheelchair.”  

---

### 11. Backrest skewed
- **Client:** Ivushka the Dryad  
- **Wheelchair:** Etac Cross 6 (folding, adjustable)  
- **Symptom:** Ivushka is pulled sideways all day: the backrest supports on one side and “buckles” on the other. By evening her back aches.

**Inspection clues (what the player sees)**

- *Backrest (posts, upholstery)* — The left backrest post is tilted back more than the right. The upholstery is stretched askew.
- *Bolts/nuts* — The 13 mm nut on the inner side of the left wheel mount is slightly loose. Marks are visible on the metal: the post has been rotating.
- *Cushion* — The cushion sits correctly: rounded corners between the backrest posts.
- *Tire* — Tires are inflated correctly: 110 psi (7.5 bar), as on the sidewall.
- *Wheel lock* — The wheel locks hold. The pin in the released position is 15–20 mm from the tire, which is normal.
- *Anti-tipper* — Anti-tippers are in place, the catch is snapped shut.

**Diagnosis options**

- ✅ (correct) The backrest posts are at different angles: the angle nut on one side came loose and the post “slid”
- ❌ The upholstery stretched: tightening the straps will do — The straps change the shape of the backrest, but not the angle of the posts. The skew is in the posts themselves.
- ❌ The client “sits wrong” — It's not about seating. Look at the posts: they're at different angles, no one could sit straight like that.

**Repair steps**

1. Engage both wheel locks with the chair on a level floor. Ivushka moves over to the bench.  
   *Tool:* Hands → *Part:* Wheel lock  
   *Hint:* Barty: “The master always said: first the wheel locks, then philosophy.”  
   *After the step:* We change the post angle on an empty wheelchair: it's safer, and the post moves freely.
2. Use a tape measure to measure the distance from each backrest post to the armrest plate.  
   *Tool:* Tape measure → *Part:* Backrest (posts, upholstery)  
   *After the step:* This is exactly how Etac checks the backrest angle: the post ↔ armrest plate distance must match on both sides.
3. Loosen the 13 mm nut on the inner side of the left wheel mount.  
   *Tool:* Adjustable wrench → *Part:* Bolts/nuts  
   *Hint:* Barty: “Just turn every screw on the backrest one after another, one of them has to be the right one!”  
   *After the step:* This nut holds the backrest angle. The 4 and 8 mm screws on the posts control the backrest HEIGHT, we don't touch them.  
   *If wrong:* The post angle is held by a 13 mm nut at the wheel mount — loosen it with the adjustable wrench.
4. Set the left post so the distance matches the right side.  
   *Tool:* Hands → *Part:* Backrest (posts, upholstery)  
   *Mini-game:* gap  
   *After the step:* Etac: the angle of both posts is the same.
5. Tighten the 13 mm nut.  
   *Tool:* Adjustable wrench → *Part:* Bolts/nuts  
   *After the step:* The tightened nut won't let the post rotate again under weight.
6. Ivushka sits back down. Adjust the lower upholstery strap — pelvic support.  
   *Tool:* Hands → *Part:* Backrest (posts, upholstery)  
   *After the step:* Etac: the upholstery is adjusted with the person sitting in the wheelchair — from the bottom up.
7. Adjust the upper upholstery straps without overtightening.  
   *Tool:* Hands → *Part:* Backrest (posts, upholstery)  
   *Hint:* Barty: “Tighten everything like a drum!” No: the backrest should follow the curve of the back.  
   *After the step:* Don't overtighten the upper straps: the wheelchair will fold worse.
8. Check the anti-tippers: lowered, catch snapped shut.  
   *Tool:* Hands → *Part:* Anti-tipper  
   *Hint:* Barty: “Take those little wheels off the back, they just get in the way!”  
   *After the step:* Etac: after ANY wheelchair adjustment, check that the anti-tippers work. If they don't work, the wheelchair can tip over.  
   *If wrong:* Anti-tippers aren't removed, they're checked by hand: lowered and snapped shut.

**Test:** Ivushka rides between the shelves: sits straight, the backrest supports equally on both sides, no more pull to the side.  
**What you learn:** Etac Cross 6: the backrest angle is set by a 13 mm nut on the inner side of the wheel mount, separately for each post. The manual requires setting both posts the same and checking the distance to the armrest plate. After any adjustment, check the anti-tippers.  
**Client says:** Ivushka (whispering): “Like the roots grew back straight. Thank you, master. Your book can come back with no late fee.”  

---

### 12. The tilt “clunks”, the wheelchair rocks backward
- **Client:** Iskra the Dragonling  
- **Wheelchair:** Zippie Iris (pediatric, tilt-in-space)  
- **Symptom:** When Iskra's chair is tilted back, it gives a dull “clunk” and seems to sag a little more. And on the carpet the wheelchair rocks backward and sideways.

**Inspection clues (what the player sees)**

- *Anti-tipper* — The left anti-tipper wheel is one hole higher than the right: to the floor about 62 mm on the left, about 45 mm on the right.
- *Tilt cable* — The right tilt trigger cable is slack, the trigger has noticeable free play.
- *Tilt lock (rocker/teeth)* — On the right, the plunger pin doesn't fully enter the rocker and barely catches.
- *Tilt trigger* — Both triggers are intact and spring back. The locking pin on the cord is in place.
- *Tire* — Tires 22": pressure 65 psi, as in the manual's table.
- *Wheel lock* — The locks engage and press into the tire more than 3 mm, which is normal.

**Diagnosis options**

- ✅ (correct) Anti-tippers at different heights + slack cable: the right pin doesn't fully enter the rocker
- ❌ The whole tilt mechanism is broken, replace the frame — The mechanism is intact: the pin just doesn't reach because of the slack cable. This is an adjustment, not a replacement.
- ❌ The child fidgets too much — It's not the child: the wheelchair must be reliable under any movement. Look for the cause in the mechanics.
- ❌ Grease the cable with oil and it'll all go away — The Iris manual forbids lubricating the tilt mechanism. The slack is removed with the adjuster.

**Repair steps**

1. Engage both wheel locks with the chair on a level floor. Iskra moves into her mom's arms.  
   *Tool:* Hands → *Part:* Wheel lock  
   *Hint:* Barty: “Hi, little one! I'm a ghost, but a kind one. Almost not scary. Well, a little.”  
   *After the step:* On a level surface the measurements are honest. The lock should press into the tire at least 3 mm (1/8").
2. Use a tape measure to measure the gap from the anti-tipper wheels to the floor on both sides.  
   *Tool:* Tape measure → *Part:* Anti-tipper  
   *After the step:* Iris spec: 38–51 mm (1½–2") in the lowered position.
3. Press the button on the left anti-tipper wheel and move it to the hole below.  
   *Tool:* Hands → *Part:* Anti-tipper  
   *Mini-game:* gap  
   *After the step:* Iris: both anti-tipper wheels must be at EXACTLY the same height.
4. Loosen the locknut on the right trigger's cable adjuster.  
   *Tool:* Adjustable wrench → *Part:* Tilt cable (also accepted: Tilt trigger)  
   *After the step:* The cable adjuster sits at the handle, next to the trigger.
5. Turn the cable adjuster until the slack is gone.  
   *Tool:* Hands → *Part:* Tilt cable (also accepted: Tilt trigger)  
   *Hint:* Barty: “Drip some oil on the cable, it'll tighten itself!”  
   *After the step:* Don't overtighten: the pin must extend and retract freely.  
   *If wrong:* The Iris tilt mechanism is not lubricated. The slack is taken up with the adjuster, by hand.
6. Check the plunger pin: trigger pressed — fully retracted, trigger released — fully seated in the rocker.  
   *Tool:* Hands → *Part:* Tilt lock (rocker/teeth)  
   *After the step:* The main criterion for correct cable tension per the manual.
7. Tighten the locknut.  
   *Tool:* Adjustable wrench → *Part:* Tilt cable (also accepted: Tilt trigger)  
   *After the step:* Otherwise the adjuster will unscrew from vibration and the cable will go slack again.
8. Squeeze both triggers and tilt the seat back.  
   *Tool:* Hands → *Part:* Tilt trigger  
   *Hint:* Barty: “Tilt it all the way, let the backrest lie flat, it's more fun!”  
   *After the step:* The mechanism only releases with both triggers. When a child is in the chair, their hands are on the armrests, feet on the footrest.  
   *If wrong:* The tilt is tested with both triggers and by hand. And never past the point where the backrest is parallel to the floor.
9. Release the triggers: the seat must lock solidly.  
   *Tool:* Hands → *Part:* Tilt lock (rocker/teeth) (also accepted: Tilt trigger)  
   *After the step:* When the triggers are released the rockers lock — the seat stays rock-solid.

**Test:** Iskra is back in the chair: the backward tilt is smooth, without a “clunk”, and the chair locks firmly in any position. On the carpet it no longer rocks: the anti-tippers are at the same height.  
**What you learn:** Zippie Iris: anti-tippers are set 38–51 mm (1½–2") from the floor, both sides strictly equal. The tilt cable is tensioned with the adjuster until the pin fully seats in the rocker, and the mechanism must not be lubricated. The weekly checklist covers cables, plunger, rocker and anti-tippers. Slopes — no steeper than 6°.  
**Client says:** Iskra: “Hooray! Now I can lean back and watch the clouds like a real stargazer!”  

---

### 13. The tilt “creeps” and sticks
- **Client:** Granny Agatha  
- **Wheelchair:** Ki Mobility Focus CR (tilt-in-space)  
- **Symptom:** The grandson presses the trigger and the chair tilts in jerks. He releases the trigger and the seat still “creeps” back a little. Sometimes the trigger doesn't release the tilt at all.

**Inspection clues (what the player sees)**

- *Tilt cable* — Under the seat the tilt cable is pinched by a zip tie and bent almost at a right angle. There's a kink in the housing.
- *Tilt trigger* — The trigger moves stiffly and doesn't always return. The locking pin on its lanyard is in place.
- *Tilt lock (rocker/teeth)* — The teeth of the rotating frame are clean and intact, but the locking tooth doesn't sit fully into them.
- *Backrest gas spring* — The backrest gas springs hold their angle. They handle recline, not tilt.
- *Anti-tipper* — The anti-tippers are lowered and sit level.
- *Wheel lock* — The wheel locks clamp and hold.

**Diagnosis options**

- ✅ (correct) Kink in the tilt cable: the cable pulls with friction, the locking tooth doesn't seat fully. Replace the cable
- ❌ Tighten the adjuster harder and the kink is nothing to worry about — Ki Mobility: a cable with a kink or one that can't be adjusted is REPLACED. A kink isn't cured with the adjuster.
- ❌ The backrest gas springs are worn out — The gas springs recline the backrest, they don't tilt the seat. And they hold.
- ❌ Soak the cable in WD-40 — The manual explicitly forbids WD-40 and petroleum solvents: they damage the components.

**Repair steps**

1. Engage the wheel locks with the chair on a level floor. Agatha moves to the armchair by the window.  
   *Tool:* Hands → *Part:* Wheel lock  
   *Hint:* Barty: “Madame Agatha! I'm the ghost of this workshop. Yes, the one and only. No, I did not drop your telescope in 1987.”  
   *After the step:* Ki: tilt and recline adjustments are made on a level surface with the wheel locks engaged.
2. Inspect the tilt cable along its whole length: kinks, sharp bends, incorrect routing.  
   *Tool:* Eyes → *Part:* Tilt cable  
   *After the step:* Ki: cables are checked every week: operation, routing, bends and kinks.
3. Replace the kinked cable with a new genuine Ki Mobility cable.  
   *Tool:* Adjustable wrench → *Part:* Tilt cable  
   *Hint:* Barty: “Straighten it with pliers, it'll be as good as new!”  
   *After the step:* A cable with a kink or one that can't be adjusted is only replaced. Use only Ki-approved parts.  
   *If wrong:* A kink isn't straightened, the cable is replaced entirely.
4. Route the new cable along the standard path: smoothly, without sharp bends, and without pinching it with zip ties.  
   *Tool:* Hands → *Part:* Tilt cable  
   *After the step:* Ki: the cable should have as few bends as possible, that means less friction.
5. Loosen the locknut of the cable adjuster with 10 mm and 3/8" wrenches.  
   *Tool:* Adjustable wrench → *Part:* Tilt cable  
   *After the step:* You hold the adjuster body with one wrench and loosen the nut with the other.
6. Screw the adjuster in or out until the slack is gone. The locking tooth must stay fully in the teeth.  
   *Tool:* Hands → *Part:* Tilt cable  
   *After the step:* Rough adjustment done: most of the slack is gone. Checking through the full range will show what fine-tuning is left.
7. Rock the tilt through the whole range and listen to the lock.  
   *Tool:* Hands → *Part:* Tilt lock (rocker/teeth)  
   *Mini-game:* meter  
   *After the step:* The tilt must lock in any position, and the tooth must not scrape against the teeth.
8. Back the adjuster out a little more — until the tooth stops chattering and the trigger has no play.  
   *Tool:* Hands → *Part:* Tilt cable  
   *After the step:* Ki: the locking tooth sits fully in the teeth and doesn't chatter at any tilt position.
9. Tighten the locknut. Turn only the nut, not the adjuster or the body.  
   *Tool:* Adjustable wrench → *Part:* Tilt cable  
   *After the step:* If you turn the adjuster or the body, you'll ruin the setting you just found.
10. Return the seat to the tilt position she needs.  
   *Tool:* Hands → *Part:* Tilt trigger (also accepted: Tilt lock (rocker/teeth))  
   *After the step:* The tilt is chosen for the task: resting, eating, pressure relief.
11. Insert the lock pin into the trigger.  
   *Tool:* Hands → *Part:* Tilt trigger  
   *Hint:* Barty: “Just lock the trigger OPEN and go have some tea, let it settle itself!”  
   *After the step:* Ki: the trigger is locked with the pin after positioning — so the tilt can't release by accident.  
   *If wrong:* You must never leave a person in the chair with the triggers locked open: they could tip over.
12. Squeeze the trigger lightly and push the handles: the tilt must not release.  
   *Tool:* Hands → *Part:* Tilt trigger (also accepted: Tilt lock (rocker/teeth))  
   *After the step:* The pin holds: the trigger doesn't release the tilt.

**Test:** The grandson presses the trigger: the chair tilts smoothly and locks firmly in any position. Nothing creeps or rustles, and the trigger returns on its own.  
**What you learn:** Ki Mobility Focus CR: a kinked tilt cable isn't adjusted but replaced, and routed with a minimum of bends. The adjuster is set so there's no slack and the tooth sits fully in the teeth of the rotating frame. Cables are checked every week. You must never leave a person in the chair with the triggers locked open. Slopes — no steeper than 9°.  
**Client says:** Agatha: “Mm-hm. Now I tilt smoothly, like the moon setting. Thank you, master. You're accepted into my constellations.”  

---

### 14. A red code on the joystick — and it won't move — Variant 1/3
- **Client:** Saira the Lizardfolk Cartographer  
- **Wheelchair:** WHILL Model C2 (omni-wheels, solid rear tires)  
- **Symptom:** Saira turns on her WHILL, a red number flashes on the joystick display, a beep sounds — and the wheelchair shuts itself off. “It was running this morning! I even wrote it down!”

**Inspection clues (what the player sees)**

- *Joystick* — Joystick display: a red “02” with a vertical bar, then everything goes dark.
- *Joystick knob* — The joystick moves smoothly and returns to center on its own. But Saira switches the chair on with her map tube resting on the joystick — the tube pushes the knob.
- *Flip-up armrest* — The armrests are lowered and latched.
- *Freewheel lever* — The freewheel levers are up — the brakes are locked.
- *Battery* — The battery is clicked into place, charge nearly full.
- *Tire* — The rear tires are airless — nothing to inflate, tread is fine.

**Diagnosis options**

- ✅ (correct) Code 02: the joystick was not in neutral at power-on — turn it on without touching the joystick
- ❌ Battery discharged — Low charge is codes 05/06, and the battery is nearly full.
- ❌ Brakes released — That would be code 03. The levers are up — the brakes are locked.

**Repair steps**

1. Read the code on the joystick display and find it in the code table.  
   *Tool:* Eyes → *Part:* Joystick  
   *Mini-game:* meter  
   *After the step:* Codes other than 01–06 are usually handled by the dealer, but the table always comes first.
2. Make sure the power is off: the display has gone dark.  
   *Tool:* Eyes → *Part:* Joystick  
   *After the step:* A switched-off wheelchair won't jerk from an accidental touch.
3. Clear off everything pressing on the joystick knob: the map tube, a bag, the edge of a cloak.  
   *Tool:* Hands → *Part:* Joystick knob (also accepted: Joystick)  
   *After the step:* It takes just 1 N to move the joystick — the weight of a small apple.
4. Check that the joystick moves smoothly and returns to center on its own.  
   *Tool:* Hands → *Part:* Joystick knob  
   *After the step:* A daily inspection item from the manual.
5. Wipe the joystick with a cloth dampened with 70% alcohol — no water or solvents.  
   *Tool:* Cloth → *Part:* Joystick (also accepted: Joystick knob)  
   *After the step:* Only the wheels can be washed with water; the joystick and electronics cannot.
6. Check that the freewheel levers are up (brakes locked).  
   *Tool:* Eyes → *Part:* Freewheel lever  
   *After the step:* Otherwise code 03 will pop up next.
7. Turn on the power without touching the joystick knob. Hand on the joystick only afterwards.  
   *Tool:* Hands → *Part:* Joystick  
   *Hint:* Barty: “Hold the joystick forward while you turn it on — it'll go faster!” — no: don't touch the joystick at power-on, or you'll get code 02.  
   *After the step:* A one-second pause after power-on — and no codes.

**Test:** The display shows the charge, no “02”. Saira starts off smoothly and does a lap around the workshop.  
**What you learn:** Codes 01–04 on the WHILL C2 are safeguards against accidental starts: a raised joystick armrest, a deflected joystick, released brakes, a connected charger. These aren't faults: remove the cause and turn it on again. The C2's rear tires are airless — they are not inflated.  
**Client says:** Saira: “Logged it in the journal: ‘map tube — NOT on the joystick’. Thanks, bone master!”  

---

### 14. A red code on the joystick — and it won't move — Variant 2/3
- **Client:** Saira the Lizardfolk Cartographer  
- **Wheelchair:** WHILL Model C2 (omni-wheels, solid rear tires)  
- **Symptom:** Saira turns on her WHILL, a red number flashes on the joystick display, a beep sounds — and the wheelchair shuts itself off. “It was running this morning! I even wrote it down!”

**Inspection clues (what the player sees)**

- *Joystick* — Joystick display: a red “01”, a beep, the wheelchair shuts off.
- *Flip-up armrest* — The right (joystick) armrest is lowered, but not until it clicks: the latch lever moves stiffly, and there's desert sand in the base.
- *Joystick knob* — The joystick is centered and moves smoothly.
- *Battery* — The battery is clicked into place, charge full.
- *Freewheel lever* — The freewheel levers are up — the brakes are locked.
- *Seat* — The seat sits squarely on the post, the latch lever is down.

**Diagnosis options**

- ✅ (correct) Code 01: the armrest with the joystick did not reach the operating position — sand in the base
- ❌ The joystick was touched at power-on — That is code 02. Here it's 01 — it's the armrest.
- ❌ The motor failed — Motor errors are codes 60–86. Code 01 is a safeguard, not a fault.

**Repair steps**

1. Read the code on the joystick display and find it in the code table.  
   *Tool:* Eyes → *Part:* Joystick  
   *Mini-game:* meter
2. Make sure the power is off: the display has gone dark.  
   *Tool:* Eyes → *Part:* Joystick  
   *After the step:* The armrest is moved only on a switched-off wheelchair.
3. Inspect the armrest base and the latch lever: what's stopping it from latching?  
   *Tool:* Eyes → *Part:* Flip-up armrest  
   *After the step:* Manual: a stiff latch lever = dust and sand in the base.
4. Brush out the armrest base.  
   *Tool:* Brush/tweezers → *Part:* Flip-up armrest  
   *Hint:* Barty: “Douse the hinge with machine oil, nice and thick!” — no: the manual forbids lubricant and wax on moving parts — sand sticks to them.  
   *After the step:* Dry cleaning only (brush or blower bulb): lubricant is sticky and collects sand.
5. Rotate the armrest forward until it clicks and check that it's locked.  
   *Tool:* Hands → *Part:* Flip-up armrest  
   *After the step:* Keep your fingers away from the hinge: it's easy to pinch them there.
6. Turn on the power without touching the joystick.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* No code — the joystick is in the operating position.

**Test:** The armrest sits with a clear click, the display shows the charge. Saira transfers in from the side and back — everything works.  
**What you learn:** The WHILL C2 joystick sits on a flip-up armrest: it is raised to transfer in from the side. If the armrest is not latched, the wheelchair shows code 01 and won't drive. A stiff latch lever is cleaned with a brush or blown out, and no lubricant is used.  
**Client says:** Saira: “Desert sand — in every crevice. Now I know where my brush is. Thanks!”  

---

### 14. A red code on the joystick — and it won't move — Variant 3/3
- **Client:** Saira the Lizardfolk Cartographer  
- **Wheelchair:** WHILL Model C2 (omni-wheels, solid rear tires)  
- **Symptom:** Saira turns on her WHILL, a red number flashes on the joystick display, a beep sounds — and the wheelchair shuts itself off. “It was running this morning! I even wrote it down!”

**Inspection clues (what the player sees)**

- *Joystick* — Joystick display: a red “10”, a beep, the wheelchair shuts off.
- *Seat* — The seat sits on the post, but Saira recently removed it for a trip in a cart.
- *Seat connector* — There's sand and fine dust on the connector contacts between the seat and the base.
- *Battery* — The battery is inserted, charge full.
- *Freewheel lever* — The freewheel levers are up — the brakes are locked.
- *Joystick knob* — The joystick is centered and moves smoothly.

**Diagnosis options**

- ✅ (correct) Code 10: communication fault through the seat connector — restart, reinstall the seat, clean the contacts
- ❌ The battery froze — Cold is code 14: the wheelchair just drives slower, it doesn't shut off.
- ❌ Replace the joystick and the controller at once — Replacing the joystick, the seat cable or the controller is the last item in the table, and it's dealer work.

**Repair steps**

1. Read the code on the joystick display and find it in the code table.  
   *Tool:* Eyes → *Part:* Joystick  
   *Mini-game:* meter
2. Make sure the power is off: the display has gone dark.  
   *Tool:* Eyes → *Part:* Joystick  
   *After the step:* The battery is only removed with the chair switched off.
3. Press the release button and take the battery out.  
   *Tool:* Hands → *Part:* Battery  
   *After the step:* The battery weighs 2.7 kg — don't drop it.
4. After 10 s, push the battery back in until it clicks.  
   *Tool:* Hands → *Part:* Battery  
   *After the step:* 10 seconds without the battery — the electronics fully restart.
5. After 5 s, switch the chair on without touching the joystick.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* Watch the display: does the code clear?
6. Look at the display: code 10 is back and the chair has shut off again.  
   *Tool:* Eyes → *Part:* Joystick  
   *After the step:* So it's the seat connector. From here on, disassembly only with the chair off.
7. Take the battery out again.  
   *Tool:* Hands → *Part:* Battery  
   *After the step:* The seat is only removed with the battery out.
8. Check: the floor is level, the freewheel levers are up.  
   *Tool:* Eyes → *Part:* Freewheel lever  
   *After the step:* Disassembly is done on a level floor, without the battery and with the brakes locked.
9. Pull the seat release lever.  
   *Tool:* Hands → *Part:* Seat  
   *After the step:* Lever up — the seat is no longer locked to the post.
10. Lift the seat straight up by the armrests and set it down cushion side up.  
   *Tool:* Hands → *Part:* Seat  
   *Hint:* Barty: “Flip the seat upside down — it's easier!” — no: that's how you break the joystick.  
   *After the step:* Set the seat down cushion-up: nothing should press on the joystick.
11. Inspect the contacts of the connector between the seat and the base.  
   *Tool:* Eyes → *Part:* Seat connector  
   *After the step:* Sand and dust on the contacts. The connector is magnetic: keep a pacemaker no closer than 20 cm.
12. Sweep the sand off the connector contacts with a brush.  
   *Tool:* Brush/tweezers → *Part:* Seat connector  
   *After the step:* Don't touch the contacts with fingers or metal.
13. Wipe the connector's contact surface with a dry cloth.  
   *Tool:* Cloth → *Part:* Seat connector  
   *After the step:* Connectors must not get wet — dry cleaning only.
14. Set the seat straight onto the post, checking through the inspection window.  
   *Tool:* Hands → *Part:* Seat  
   *After the step:* The seat must sit level, without tilting.
15. Lower the seat locking lever.  
   *Tool:* Hands → *Part:* Seat  
   *After the step:* The lever should sit across the seat — that means it's locked.
16. Push the battery in until it clicks.  
   *Tool:* Hands → *Part:* Battery
17. After 5 s, switch the chair on without touching the joystick.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* No code — the connection is back. Had the code stayed, the table's next step would be a new joystick or cables — dealer work.

**Test:** The display is clean, no code. Saira drives a figure eight between the workbenches — the connection holds.  
**What you learn:** Code 10 is a communication fault through the connector between the seat and the base. WHILL table: remove the battery for 10 seconds; reinstall the seat; clean the contacts. If that doesn't help, the dealer replaces the joystick, cables or controller. The connector is magnetic — keep a pacemaker no closer than 20 cm.  
**Client says:** Saira: “Ten is my least favorite number. It was. Thank you!”  

---

### 15. Won't charge after winter
- **Client:** Matilda the Badger Beekeeper  
- **Wheelchair:** Permobil F5 Corpus (front-wheel drive, 2×12 V SLA)  
- **Symptom:** Matilda's wheelchair sat in a cold garden shed all winter. In spring Matilda plugged in the charger — and nothing: the joystick is dark, no charge. “I did everything by the instructions!”

**Inspection clues (what the player sees)**

- *Main circuit breaker* — The main circuit breaker lever at the back is in the OFF position. Matilda switched it off for the winter, as the manual says.
- *Battery* — The batteries were fully charged in autumn. Now not a single bar lights up: the circuit is cut off.
- *Joystick* — The joystick is dark. The charging socket on the front of the joystick is clean and dry.
- *Freewheel lever* — The freewheel levers are in the “drive” position.
- *Tire* — The drive-wheel tires are noticeably soft: the pressure dropped after the frosts.
- *Motor* — The motors are cold but intact.
- *Frame* — There's frost on the frame. The thermometer on the shed wall reads about +1 °C.

**Diagnosis options**

- ✅ (correct) The main circuit breaker is off for storage, and the shed is colder than +5 °C: switch the breaker on and charge somewhere warm
- ❌ The batteries died over the winter — replace the pair right away — They were fully charged in autumn, and the circuit is now cut off by the breaker. Switch it on first.
- ❌ The charging breaker burned out — open up the electronics — The charging breaker resets itself after 5 minutes. And only a technician touches the electronics.

**Repair steps**

1. Use the power button to make sure the joystick is switched off: a dark screen proves nothing — the breaker is cutting the power right now.  
   *Tool:* Hands → *Part:* Joystick  
   *After the step:* Work on the main circuit breaker only with the joystick switched off.
2. Look at the thermometer in the shed and compare the temperature with the manual.  
   *Tool:* Eyes → *Part:* Frame  
   *Mini-game:* meter  
   *After the step:* Cold and damp stop the batteries from charging fully and corrode the contacts.
3. On a level floor, with a helper, engage freewheel: levers down (wheelchair off).  
   *Tool:* Hands → *Part:* Freewheel lever  
   *After the step:* In freewheel the brakes are off — only on level ground and with someone holding the wheelchair.
4. Roll the wheelchair to the dry, warm workshop, holding it from the side.  
   *Tool:* Hands → *Part:* Frame  
   *Hint:* Barty: “Just charge it in the shed, there's a socket!” — no: below +5 °C the batteries won't take a full charge.  
   *After the step:* The wheelchair weighs 189 kg: roll it slowly and with two people.
5. Disengage freewheel: levers up, wheelchair off.  
   *Tool:* Hands → *Part:* Freewheel lever  
   *After the step:* An F5 can't drive in freewheel — and the brakes don't hold.
6. Switch on the main circuit breaker with the lever at the back of the wheelchair.  
   *Tool:* Hands → *Part:* Main circuit breaker  
   *After the step:* It's switched off for winter storage, but you need it on to charge. If it trips again — call service.
7. Connect the charger first to the socket on the front of the joystick, then to the wall outlet.  
   *Tool:* Charger → *Part:* Joystick  
   *Hint:* Barty: “Wall outlet first, then the wheelchair — what's the difference?” There is a difference: the manual says the opposite.  
   *After the step:* Only the stock Permobil charger. If charging doesn't start, wait 5 minutes: the charging breaker resets itself.
8. While it charges, inflate the drive tires through the valves to 250 kPa.  
   *Tool:* Pump → *Part:* Tire (also accepted: Valve)  
   *Mini-game:* pump  
   *After the step:* Check the pressure once a week and after a sharp temperature change. An overinflated tire can burst.
9. Charge is full — unplug the charger: while it's connected, the F5 won't drive.  
   *Tool:* Charger → *Part:* Battery (also accepted: Joystick)  
   *After the step:* When the chair goes back into storage: charge it fully and switch the breaker off; once a month switch it on and top up the batteries.

**Test:** The charge indicator on the joystick is full, the tires are firm. Matilda does a lap around the workshop and stops right by the jar of honey.  
**What you learn:** Before long storage, charge the F5 fully and switch off the main circuit breaker. Once a month, switch the breaker on, charge the batteries and switch it off again. Store and charge in a dry place no lower than +5 °C. Connect the charger to the wheelchair first, then to the wall outlet. Drive-wheel tires — 250 kPa (35 psi).  
**Client says:** Matilda: “So switching the breaker off is right, you just have to switch it back on later! Here's some honey, master, and don't argue.”  

---

## Wheelwrights' Guild (technician level)

### G1. Truing a wobbly rim
- **Client:** Aelin the Elf  
- **Symptom:** Guild task: after the tournament, the rim of Aelin's rear wheel wobbles side to side. Correct the runout by the rules: measure before truing, turn nipples a little at a time.

**Repair steps**

1. Remove the rear wheel from the chair (quick-release axle button)  
   *Tool:* Hands  
   *After the step:* Press the button in the end of the axle — the wheel comes off whole, axle and all.
2. Mount the wheel in the truing stand  
   *Tool:* Hands  
   *Order: free; must come after:* 1  
   *Hint:* Barty: “A staaand! The lady master had one just like it. I thought it was a harp.”  
   *After the step:* The stand holds the axle rigidly — runout shows precisely.
3. Spin the wheel and find where the rim strays with the dial indicator  
   *Tool:* Dial indicator  
   *Order: free; must come after:* 2  
   *After the step:* The dial indicator shows where and which way the rim wobbles.
4. Measure spoke tension on both sides of the wobble zone with the tension meter  
   *Tool:* Tension meter  
   *Order: free; must come after:* 2  
   *After the step:* Numbers come before truing, or you won't know what you changed.
5. Correct the wobble: tighten spokes on the opposite flange in the runout zone  
   *Tool:* Spoke wrench  
   *Order: free; must come after:* 3, 4  
   *Value from the manual:* How far should you turn the nipples per pass? — ✅ No more than 1/4 turn — then recheck the runout; ❌ 2 full turns each — it'll true faster; ❌ Turn until it rings clearest  
   *After the step:* The rim pulls toward the flange whose spokes you tighten.
6. Spin the wheel again: runout should be within tolerance  
   *Tool:* Dial indicator  
   *Order: free; must come after:* 5  
   *After the step:* Tolerance is no more than 1–2 mm. Not there yet? Another 1/4-turn pass.
7. Compare neighboring spokes' tension with the tension meter  
   *Tool:* Tension meter  
   *Order: free; must come after:* 5  
   *After the step:* One overtightened spoke means a future wobble or a cracked rim.
8. Take the wheel out of the truing stand  
   *Tool:* Hands  
   *Order: free; must come after:* 6, 7  
   *After the step:* Runout within tolerance, tension even — the wheel is ready.
9. Put the wheel back on the chair (quick-release axle)  
   *Tool:* Hands  
   *Order: free; must come after:* 8  
   *Hint:* Barty: “Click! I love that sound. Means nothing fell off.”

**Test:** The wheel spins true in the stand; the indicator needle barely twitches.  
**What you learn:** A rim is trued by dial indicator in small steps: no more than 1/4 nipple turn per pass; the rim moves toward the flange being tightened. Tension is checked with a tension meter; runout tolerance is 1–2 mm.  
**Client says:** Aelin: “A perfectly round wheel. The Guild will make a master of you, Martin.”  

---

### G2. Replacing a battery pair
- **Client:** Master Brenna  
- **Wheelchair:** Quantum Edge 4 (22NF / group 24 batteries)  
- **Symptom:** The Guild's exam wheelchair: the batteries are going on four years old and no longer hold a charge. Replace the PAIR by the rules. Brenna is watching. Closely.

**Repair steps**

1. Turn off the power at the joystick  
   *Tool:* Hands  
   **SAFETY step**  
   *Hint:* Brenna: “First rule of electrics: kill the power. Second: check that you killed it.”  
   *After the step:* Work only on a powered-down wheelchair.
2. Check that the freewheel levers are in drive mode  
   *Tool:* Eyes  
   **SAFETY step**  
   *After the step:* Drive mode means the motor brakes are on: the chair won't roll while you're in the battery bay.
3. Remove the front cover by its release handles  
   *Tool:* Hands  
   *After the step:* No tools needed: the cover is held by latches.
4. Remove the rear shroud: turn the two yellow clips  
   *Tool:* Hands  
   *After the step:* Under the rear shroud: the battery tray with the main circuit breaker.
5. Open the battery compartment door  
   *Tool:* Hands  
   *Order: free; must come after:* 3, 4  
   *After the step:* Terminal bolts go in the magnetic tray later, not “somewhere on the workbench”.
6. Press the yellow button on the main circuit breaker — the batteries are disconnected from the system  
   *Tool:* Hands  
   *Order: free; must come after:* 4  
   **SAFETY step**  
   *After the step:* On the Edge 4 the breaker doubles as the battery isolation switch: the circuit is open before a wrench touches the terminals.
7. Disconnect the NEGATIVE terminal — always first  
   *Tool:* Adjustable wrench  
   *Order: free; must come after:* 1, 2, 5, 6  
   **SAFETY step**  
   *After the step:* Negative off — the ground circuit is broken; the wrench can no longer cause a short.
8. Disconnect the positive terminal  
   *Tool:* Adjustable wrench  
   *Order: free; must come after:* 7
9. Take the old batteries out of the compartment  
   *Tool:* Hands  
   *Order: free; must come after:* 8  
   *Hint:* Barty: “Let me lift it! ...ah, right. Fine, you do it.”  
   *After the step:* Batteries are heavy: lift from a squat and keep them upright.
10. Fit a new pair from the Guild catalog  
   *Tool:* Hands  
   *Order: free; must come after:* 9  
   *Value from the manual:* Which battery pair are we fitting? — ✅ Two new 12 V AGMs — same capacity, type and age; ❌ One new + last year's of the same capacity (savings!); ❌ A new AGM + a new gel — they're both 12 V  
   *After the step:* Secure the new pair: a loose battery chafes through its wires on the first bump.
11. Connect the POSITIVE terminal first  
   *Tool:* Adjustable wrench  
   *Order: free; must come after:* 10  
   **SAFETY step**  
   *After the step:* Assembly mirrors disassembly: positive first, negative last.
12. Connect the negative terminal  
   *Tool:* Adjustable wrench  
   *Order: free; must come after:* 11
13. Flip the main circuit breaker lever down — battery power is back  
   *Tool:* Hands  
   *Order: free; must come after:* 12  
   *After the step:* The breaker button disconnects the batteries; the lever down reconnects them.
14. Close the battery compartment door  
   *Tool:* Hands  
   *Order: free; must come after:* 12
15. Refit the covers  
   *Tool:* Hands  
   *Order: free; must come after:* 14, 13  
   *After the step:* Without the covers, dirt gets into the compartment and fingers wander to the terminals.
16. Put the new pair on a full first charge  
   *Tool:* Charger  
   *Order: free; must come after:* 15  
   *After the step:* First charge: a full one, and only with the stock charger — it sets the pair's lifespan.

**Test:** The joystick wakes up, the charge gauge creeps up. Brenna checks the terminal torque. She nods!  
**What you learn:** Batteries are replaced only in pairs of the same type, capacity and age. Disassembly: negative off first. Assembly: positive on first. A new pair's first charge is a full one, with the stock charger.  
**Client says:** Brenna: “By the book, no fuss. You'll make a technician yet, zombie.”  

---

### G3. Toe: chair pulls sideways
- **Client:** Tavr the Centaur (courier)  
- **Symptom:** The centaur's courier chair: wheels intact, pressure seems fine, but it pulls sideways and “eats” the tires. A classic — the toe is out. Measure, don't guess.

**Repair steps**

1. Check both tires with the pressure gauge: the pressures must match  
   *Tool:* Pressure gauge  
   *Hint:* Barty: “See, I said pump it up! I'm right this time, aren't I?!”  
   *After the step:* Unequal pressure mimics bad toe alignment — rule it out first.
2. Measure the distance between the rims, front and back, with the tape measure  
   *Tool:* Tape measure  
   *Order: free; must come after:* 1  
   *After the step:* The difference between the front and back measurements is the toe.
3. Loosen the axle plate bolts  
   *Tool:* Hex key  
   *Order: free; must come after:* 2  
   *After the step:* The plate holds the axle: loosen it and you can move the wheel.
4. Set the wheels parallel (bring the measurement difference to zero)  
   *Tool:* Hands  
   *Order: free; must come after:* 3  
   *Mini-game:* gap
5. Tighten the plate bolts in a criss-cross pattern  
   *Tool:* Hex key  
   *Order: free; must come after:* 4  
   *After the step:* Criss-cross — so the plate doesn't skew while tightening.
6. Re-measure with the tape, front and back  
   *Tool:* Tape measure  
   *Order: free; must come after:* 5  
   *After the step:* Tightening may have shifted the geometry — always re-measure.

**Test:** You push the chair across the workshop — it rolls straight as an arrow. Tavr stamps a hoof with delight.  
**What you learn:** Chair pulls sideways with sound wheels? First equalize the tire pressure, then check the toe: the distance between the rims at the front and back should match (tolerance ~1 mm). Adjust at the axle plate, tighten criss-cross, then re-measure.  
**Client says:** Tavr: “It rolls straight! Four legs good, but true wheels — better.”  

---

### G4. VR2: 2 bars flash
- **Client:** Master Brenna  
- **Wheelchair:** Quickie Pulse 6 (mid-wheel drive, VR2 joystick)  
- **Symptom:** The Guild's exam wheelchair: on power-up the VR2 battery indicator flashes quickly with two bars, the wheelchair won't move. Find the cause by measuring, not guessing.

**Repair steps**

1. Decode the VR2 indicator flash using the code table  
   *Tool:* Eyes  
   *Value from the manual:* 2 bars flash quickly. What is it? — ✅ Left motor disconnected (the controller can't see it); ❌ Battery voltage low; ❌ Brake fault (solenoid)  
   *After the step:* Fast flashing of the indicator bars is a fault code, not the charge level.
2. Check charge: multimeter on the joystick charging socket, contacts 1(+) and 2(−)  
   *Tool:* Multimeter  
   *Order: free; must come after:* 1  
   *Mini-game:* meter  
   *After the step:* The Code 2 flowchart starts with battery charge.
3. Turn off power on the VR2 joystick  
   *Tool:* Hands  
   **SAFETY step**  
   *Hint:* Brenna: “Turned it off? Now check that you turned it off.”  
   *After the step:* Connectors and brushes are only touched with the chair powered off.
4. Disconnect the left motor's 4-pin connector from the control module  
   *Tool:* Hands  
   *Order: free; must come after:* 3, 1  
   *After the step:* The connector is intact, no signs of overheating, it sat tight. So the problem is deeper.
5. Measure resistance between the two lower (thick) contacts of the motor connector  
   *Tool:* Multimeter  
   *Order: free; must come after:* 4, 2  
   *Mini-game:* meter  
   *After the step:* This is the “brushes + winding” circuit. Normal is about 0.5–0.9 Ω.
6. Unscrew the brush holder caps with a flat screwdriver  
   *Tool:* Screwdriver  
   *Order: free; must come after:* 5, 3  
   *Hint:* Barty: “Cap tight? Lean on it with all your weight!” — no, the cap's plastic breaks easily.  
   *After the step:* The cap is plastic — no excess force.
7. Take the brushes out one at a time and assess their wear  
   *Tool:* Hands  
   *Order: free; must come after:* 6  
   *Value from the manual:* The left motor's brush is 4 mm, the end is chipped. Decision? — ✅ Less than 1/4" (≈6 mm) — replace brushes in both motors; ❌ 4 mm will still work — put them back; ❌ Replace just this one brush  
   *After the step:* Remember how the brush sat: the new one goes in the same way round.
8. Insert the new brushes the same way round as the old ones — in both motors  
   *Tool:* Hands  
   *Order: free; must come after:* 7  
   *After the step:* A brush put in the other way round takes a long time to bed in against the commutator.
9. Screw the brush holder caps back on with the screwdriver, no force  
   *Tool:* Screwdriver  
   *Order: free; must come after:* 8  
   *After the step:* A plastic cap strips easily — snug it down and stop.
10. Reconnect the left motor's 4-pin connector to the control module  
   *Tool:* Hands  
   *Order: free; must come after:* 9, 3  
   *After the step:* Push the connector in until it clicks; don't pull on the wires.
11. Disengage both motors' gearboxes: freewheel levers  
   *Tool:* Hands  
   *Order: free; must come after:* 9  
   **SAFETY step**  
   *After the step:* The wheels are no longer connected to the motors: the run-in won't move the wheelchair.
12. Turn the power on for the break-in  
   *Tool:* Hands  
   *Order: free; must come after:* 10  
   *After the step:* No blinking — the motor is detected again.
13. Break in the brushes for 20–30 min: joystick alternately forward and reverse  
   *Tool:* Hands  
   *Order: free; must come after:* 12, 11  
   *After the step:* New brushes are broken in first: that beds them in, and a later resistance reading is accurate.
14. Turn the power off after the break-in  
   *Tool:* Hands  
   *Order: free; must come after:* 13  
   *After the step:* Per the manual, after the work: power off first, then the gears go back into engagement.
15. Re-engage the gearboxes: levers to drive mode  
   *Tool:* Hands  
   *Order: free; must come after:* 14  
   *After the step:* Check: power off, push from behind — the wheelchair doesn't roll. That means the gears are engaged.

**Test:** Power on: the indicator glows steady, no blinking. The wheelchair goes straight, both motors pull equally. Brenna checks that the gearboxes are engaged. She nods.  
**What you learn:** The VR2 joystick reports faults by fast blinking of the indicator bars: 2 bars — the left motor isn't detected. First check the charge and connector, then a multimeter on the thick contacts. 0–1.5 Ω — the motor is OK, the controller is at fault. Open circuit — brushes: shorter than 1/4" they're replaced in both motors and broken in for 20–30 minutes.  
**Client says:** Brenna: “You didn't replace the controller ‘just in case’ — you're a technician already. The rest is experience.”  

---

### G5. Q-Logic: #203 — brake disconnected
- **Client:** Master Brenna  
- **Wheelchair:** Quantum Q6 Edge (mid-wheel drive, Q-Logic joystick)  
- **Symptom:** The Guild's exam wheelchair: on power-up the Q-Logic display shows “#203”, the wheelchair won't move. Follow the manufacturer's flowchart from start to finish, no improvising.

**Repair steps**

1. Find the display code in the Q-Logic table  
   *Tool:* Eyes  
   *Value from the manual:* Display: “#203”. What is it? — ✅ Brake 1 (left motor) isn't detected: connector, wiring, or the brake itself; ❌ Joystick out of range — calibrate; ❌ Battery empty — just charge it  
   *After the step:* Brake 1 is the brake of motor M1, the left one by default.
2. Check charge: multimeter on the joystick charging socket  
   *Tool:* Multimeter  
   *Order: free; must come after:* 1  
   *Mini-game:* meter  
   *After the step:* The flowchart assumes the batteries are charged. Check, don't take it on faith.
3. Put both freewheel levers into drive mode (up)  
   *Tool:* Hands  
   *Order: free; must come after:* 1  
   **SAFETY step**  
   *Hint:* Barty: “Yank the levers with your foot, it's faster!” — no: the manual forbids it — you'll bend the lever and the brake.  
   *After the step:* Drive mode — the motor brakes are engaged: the chair won't roll away.
4. Power-cycle the joystick  
   *Tool:* Hands  
   *Order: free; must come after:* 3  
   *After the step:* The code remains — so it's not the levers. We go further along the chart.
5. Turn off the joystick power  
   *Tool:* Hands  
   *Order: free; must come after:* 4  
   **SAFETY step**  
   *After the step:* The power module and motor connectors are only disconnected with the power off.
6. Remove the rear shroud: wing knob and clips  
   *Tool:* Hands  
   *Order: free; must come after:* 3  
   *After the step:* The shroud is held by a knob and clips — no tools needed.
7. Unscrew the power module screws on the rear frame  
   *Tool:* Screwdriver  
   *Order: free; must come after:* 5, 6  
   *After the step:* Don't pull on the wires: the module just swings out to give access to the connectors.
8. Unplug the left motor harness connector from the power module  
   *Tool:* Hands  
   *Order: free; must come after:* 7, 5  
   *After the step:* Pull on the connector body, not the wires.
9. Measure the brake resistance: pins 3–4 of the left motor connector  
   *Tool:* Multimeter  
   *Order: free; must come after:* 8  
   *Mini-game:* meter  
   *After the step:* Pins 3–4 are the brake coil. Pins 1–2 are the motor winding.
10. Follow the flowchart: replace the motor-and-brake assembly  
   *Tool:* Socket wrench  
   *Order: free; must come after:* 9  
   *Value from the manual:* Left brake — open circuit. What does the flowchart say? — ✅ Replace the left motor with its brake assembly and test the system; ❌ Replace the power module; ❌ Calibrate the joystick with the programmer  
   *After the step:* The motor and brake are one unit (motor/brake assembly): replaced as a whole.
11. Connect the new motor's connector to the power module  
   *Tool:* Hands  
   *Order: free; must come after:* 10  
   *After the step:* Don't pull on the wires: the connector should click in without strain on the harness.
12. Screw the power module back in place  
   *Tool:* Screwdriver  
   *Order: free; must come after:* 11  
   *After the step:* Screws all the way in, without stripping the threads.
13. Refit the rear shroud  
   *Tool:* Hands  
   *Order: free; must come after:* 12
14. Turn on the joystick power  
   *Tool:* Hands  
   *Order: free; must come after:* 13, 3  
   *After the step:* #203 is gone — the new brake is detected.
15. Brake test: level ground, low speed, joystick gently forward until the brake clicks, then back, left, right  
   *Tool:* Hands  
   *Order: free; must come after:* 14  
   *After the step:* In each direction the brake should click audibly after a couple of seconds.

**Test:** #203 is gone. The brake clicks in every direction; on a slope the wheelchair holds firm. Brenna marks it in the exam log.  
**What you learn:** Q-Logic displays the error number: #203/#204 — brake 1/2 not responding. Quantum flowchart: both freewheel levers to drive mode, disconnect the power module, pins 3–4 on the motor connector should read about 80 Ω. No 80 Ω — replace the motor with its brake assembly. The power module is replaced only if both brakes are fine.  
**Client says:** Brenna: “Didn't try to calibrate the joystick for a brake error — already smarter than half the fortune-tellers at the fair.”  

---
