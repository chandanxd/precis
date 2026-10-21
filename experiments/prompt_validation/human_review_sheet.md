# Précis Confirmatory Experiment: Blinded Error Analysis Review Sheet

**Review Sample:** 30 questions randomly sampled (Seed: 42) from confirmatory cohort.
**Task:** Evaluate `Output A` and `Output B` without knowledge of prompt condition.

### Coding Taxonomy Guide:
- **Primary Categories:**
  1. `Conversational Mismatch`: Full gold entity present in text, but conversational preamble caused exact match failure.
  2. `Incomplete Entity`: Partial entity returned (omitted date, unit, or qualifier).
  3. `Hallucination`: Asserted facts absent from or contradicting evidence context.
  4. `Evidence Insufficiency`: Evidence context lacked the necessary facts to answer question.
  5. `Other`: Unclassified or refusal.

---

## REV_01 (Sample `cdcb817f`)
**Question:** leader of carthage in the first punic war

**Gold Answer:** `Xanthippus`

<details><summary>Click to view Evidence Context (206 words)</summary>

```
Fact 1: Regulus was forcing next victorious at the Battle of Adys (context: forcing Carthage to sue for peace)
Fact 2: The negotiations returned  (context: to reorganise Carthage's army) (location: to Carthage) (recipient: Carthage)
Fact 3: The negotiations failed the Carthaginians , Xanthippus , a Spartan mercenary (cause: for the Carthaginians , Xanthippus , a Spartan mercenary) (manner: fortunately)
Fact 4: the terms NOT suggested were so heavy that Carthage decided Carthage would be better off not under Roman rule (context: According to Polybius) [attributed to the terms]
Fact 5: the Roman army , commanded by Marcus Atilius Regulus landed a result of the battle (cause: As a result of the battle) (location: in Africa)
Fact 6: Xanthippus captured Regulus (time: at the Battle of Tunis)
Fact 7: Xanthippus defeated the Roman army
Fact 8: the Roman army , commanded by Marcus Atilius Regulus ravaging the Carthaginian countryside
Fact 9: The Siege of Aspis ( or Clupea ) was the first fighting on African land during the war
Fact 10: the Roman army , commanded by Marcus Atilius Regulus began 
Fact 11: Marcus Atilius Regulus commanded the Roman army
Fact 12: Xanthippus is a Spartan mercenary
Fact 13: the terms NOT were  [attributed to the terms]
```
</details>

- **Output A:** `Insufficient information`
- **Output B:** `The provided facts do not contain enough information to answer the question. The document mentions Xanthippus as a Spartan mercenary and discusses negotiations with Carthage, but it does not identify the leader of Carthage during the First Punic War.`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_02 (Sample `27035f71`)
**Question:** bacterial cell walls are made rigid by the presence of

**Gold Answer:** `Peptidoglycan`

<details><summary>Click to view Evidence Context (245 words)</summary>

```
Fact 1: Peptidoglycan serves a structural role in the bacterial cell wall (context: giving structural strength , as well as counteracting the osmotic pressure of the cytoplasm)
Fact 2: a polymer consisting of sugars and amino acids that forms a mesh - like layer outside the plasma membrane of most bacteria forms a mesh - like layer outside the plasma membrane of most bacteria
Fact 3: Peptidoglycan , also known as murein is forming a polymer consisting of sugars and amino acids that forms a mesh - like layer outside the plasma membrane of most bacteria (context: forming the cell wall)
Fact 4: Peptidoglycan is involved binary fission (manner: also) (time: in binary fission) (time: during bacterial cell reproduction)
Fact 5: the MreB protein that facilitates cell shape facilitates cell shape
Fact 6: it is the MreB protein that facilitates cell shape (context: whereas peptidoglycan helps maintain the structural strength of the cell) (manner: however) (manner: actually)
Fact 7: another strand forming the 3D mesh - like layer
Fact 8: a polymer consisting  (context: of sugars and amino acids)
Fact 9: The peptide chain can be - linked cross
Fact 10: The sugar component linked 
Fact 11: Peptidoglycan known  (cause: as murein) (manner: also)
Fact 12: N - acetylmuramic acid is ( NAM
Fact 13: The sugar component consists  (context: of alternating residues of β - ( 1 , 4 ))
Fact 14: N - acetylglucosamine ( is NAG
Fact 15: A common misconception is 
```
</details>

- **Output A:** `Peptidoglycan serves a structural role in the bacterial cell wall, providing structural strength and counteracting the osmotic pressure of the cytoplasm.`
- **Output B:** `peptidoglycan`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_03 (Sample `131ef65b`)
**Question:** who plays yoda in revenge of the sith

**Gold Answer:** `Frank Oz`

<details><summary>Click to view Evidence Context (198 words)</summary>

```
Fact 1: Yoda was heard the Star Wars Rebels (manner: episode) (time: in the Star Wars Rebels)
Fact 2: episode reprising the role for the first time since Revenge of the Sith
Fact 3: Yoda appears for the first time (cause: for the first time) (manner: physically) (time: in the season)
Fact 4: 2 episode `` Shroud of Darkness '' , in which Yoda tells Ezra Yoda should find Malachor and reunites with Ahsoka after nearly 20 years tells Ezra Yoda (time: in which)
Fact 5: Yoda communicates Padawan Ezra Bridger and Padawan Ezra Bridger's master Kanan Jarrus (context: with Padawan Ezra Bridger and Padawan Ezra Bridger's master Kanan Jarrus) (location: during Padawan Ezra Bridger and his master Kanan Jarrus' experience in an ancient temple on Lothal)
Fact 6: Yoda helps 
Fact 7: episode `` is Path of the Jedi '' with Frank Oz
Fact 8: the pair do searching some soul - searching (context: to analyze Padawan Ezra Bridger and his master Kanan Jarrus' true motivations)
Fact 9: his master is Kanan Jarrus'
Fact 10: 2 episode `` is Shroud of Darkness ''
Fact 11: his master Kanan Jarrus' is experience in an ancient temple on Lothal
```
</details>

- **Output A:** `The provided facts do not contain enough information to answer the question. Fact 2 mentions that Yoda reprised his role for the first time since *Revenge of the Sith*, but it does not state who played the character in *Revenge of the Sith*.`
- **Output B:** `Insufficient information`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_04 (Sample `f0e748aa`)
**Question:** when will the 2018 oscar nominations be announced

**Gold Answer:** `Tuesday , January 23 , 2018`

<details><summary>Click to view Evidence Context (87 words)</summary>

```
Fact 1: Nominations announced Monday , February 5 , 2018 [attributed to Nominations]
Fact 2: Nominations announced Nominees Luncheon         Saturday , February 10 , 2018     Scientific and Technical Achievement Awards presentation         Tuesday , February 20 , 2018 [attributed to Nominations]
Fact 3: Final polls close 90th Annual Academy Awards presentation (time: Sunday) (time: March)
Fact 4: Nominations polls close  (time: Tuesday)
Fact 5: Final voting begins  (time: Tuesday) [attributed to Nominations]
Fact 6: Tuesday is January 23 , 2018
Fact 7: Tuesday is February 27 , 2018
```
</details>

- **Output A:** `Monday, February 5, 2018.`
- **Output B:** `Monday, February 5, 2018`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_05 (Sample `521f3ea7`)
**Question:** what is the order of the netflix marvel shows

**Gold Answer:** `Marvel 's Daredevil`

<details><summary>Click to view Evidence Context (224 words)</summary>

```
Fact 1: Series     Season     Episodes released Showrunner ( s )     Status         Marvel 's Daredevil             13     April 10 , 2015 ( 2015 - 04 - 10 ) (manner: Originally)
Fact 2: Preparing for release         Marvel 's Iron Fist             13     March 17 , 2017 ( 2017 - 03 - 17 )     Scott Buck Released TBA     2018 ( 2018 ) (manner: TBA) (recipient: Released         Marvel 's The Punisher) (time: November)
Fact 3: Preparing for release         Marvel 's Iron Fist             13     March 17 , 2017 ( 2017 - 03 - 17 )     Scott Buck Released Filming         Marvel 's The Defenders             8     August 18 , 2017 ( 2017 - 08 - 18 )     Marco Ramirez (manner: TBA) (time: November)
Fact 4: Preparing for release         Marvel 's Iron Fist             13     March 17 , 2017 ( 2017 - 03 - 17 )     Scott Buck Released Raven Metzner (manner: TBA) (time: November)
Fact 5: Erik Oleson is Filming         Marvel 's Jessica Jones             13     November 20 , 2015 ( 2015 - 11 - 20 )
Fact 6: Filming         Marvel 's Jessica Jones is 13     November 20 , 2015 ( 2015 - 11 - 20
Fact 7: Filming         Marvel 's The Defenders             8     August 18 , 2017 ( 2017 - 08 - 18 ) is Marco Ramirez
Fact 8: 13     November 17 , 2017 ( 2017 - 11 - 17 ) is Steve Lightfoot
```
</details>

- **Output A:** `Based on the provided facts, the order of the Netflix Marvel shows by release date is:

1.  **Marvel's Daredevil**: April 10, 2015
2.  **Marvel's Jessica Jones**: November 20, 2015
3.  **Marvel's Iron Fist**: March 17, 2017
4.  **Marvel's The Defenders**: August 18, 2017
5.  **Marvel's The Punisher**: November 2018 (TBA)`
- **Output B:** `Marvel 's Daredevil, Marvel 's Jessica Jones, Marvel 's Iron Fist, Marvel 's The Defenders, Marvel 's The Punisher`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_06 (Sample `4da9ee44`)
**Question:** where is wind power used most in the united states

**Gold Answer:** `Iowa`

<details><summary>Click to view Evidence Context (130 words)</summary>

```
Fact 1: Texas had the most installed wind power capacity of any U.S. state (context: with over 20,000 MW of capacity) (time: at the end of 2016)
Fact 2: The Alta Wind Energy Center in California is the largest wind farm in the United States with a capacity of 1548 MW
Fact 3: Nebraska to have installed over 1,000 MW of wind power capacity
Fact 4: The state generating the highest percentage of energy from wind power generating is Iowa
Fact 5: North Dakota has the most per capita wind generation
Fact 6: GE Energy is the largest domestic wind turbine manufacturer
Fact 7: Texas had installed more under construction (context: than any other state currently has installed) (manner: also)
Fact 8: Nebraska became the eighteenth state (time: In 2016)
```
</details>

- **Output A:** `Texas`
- **Output B:** `Based on the provided facts, wind power is used most in terms of total installed capacity in **Texas**, which had over 20,000 MW of capacity at the end of 2016. The Alta Wind Energy Center in California is noted as the largest single wind farm with a capacity of 1548 MW.`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_07 (Sample `43ee2c93`)
**Question:** who plays the beast on the new beauty and the beast

**Gold Answer:** `Dan Stevens`

<details><summary>Click to view Evidence Context (185 words)</summary>

```
Fact 1: who Stevens Beast , a cold - hearted prince who is transformed into a beast and forced to earn back the prince's humanity by learning to truly love and be loved in return (cause: as Beast , a cold - hearted prince who is transformed into a beast and forced to earn back the prince's humanity by learning to truly love and be loved in return)
Fact 2: Dan Stevens plays Beast , a cold - hearted prince who is transformed into a beast and forced to earn back the prince's humanity by learning to truly love and be loved in return
Fact 3: a cold - hearted prince who is transformed into a beast and forced to earn back the prince's humanity by learning to truly love and be loved in return is transformed  (location: into a beast)
Fact 4: Adam Mitchell portrays the younger version of the prince
Fact 5: Beast is a cold - hearted prince who is transformed into a beast and forced to earn back the prince's humanity by learning to truly love and be loved in return
```
</details>

- **Output A:** `Dan Stevens plays the Beast.`
- **Output B:** `Dan Stevens`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_08 (Sample `27e1f5a5`)
**Question:** what time is it in alaska time zone

**Gold Answer:** `UTC − 09 : 00`

<details><summary>Click to view Evidence Context (78 words)</summary>

```
Fact 1: The Alaska Time Zone observes standard time (context: − 09)
Fact 2: The clock time in this zone is based solar time (location: at the 135th meridian west of the Greenwich Observatory) (time: on mean solar time)
Fact 3: The Alaska Time Zone's time offset is eight hours ( UTC − 08 : 00 ) (time: During daylight saving time)
Fact 4: The Alaska Time Zone's time offset 
Fact 5: Coordinated Universal Time ( is UTC
```
</details>

- **Output A:** `The provided facts do not contain enough information to answer the question. They state the time offsets for standard time and daylight saving time but do not specify which offset applies at the current moment or provide a specific clock time.`
- **Output B:** `UTC − 08 : 00`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_09 (Sample `244f7dbd`)
**Question:** what is the netflix show the ranch about

**Gold Answer:** `a dysfunctional family consisting of two brothers , their rancher father , and his divorced wife and local bar owner`

<details><summary>Click to view Evidence Context (272 words)</summary>

```
Fact 1: The Ranch is filmed a sound stage (context: While the opening sequence shows scenes from Norwood and Ouray , Colorado and surrounding Ouray and San Miguel Counties) (location: in front of a live audience in Burbank , California) (time: on a sound stage)
Fact 2: The show takes place (context: detailing the life of the Bennetts , a dysfunctional family consisting of two brothers , two brothers' rancher father , and their rancher father's divorced wife and local bar owner) (location: in the fictitious small town of Garrison , Colorado) (time: on the fictional Iron River Ranch)
Fact 3: The Ranch is an American comedy web television series starring Ashton Kutcher , Danny Masterson , Debra Winger , Elisha Cuthbert , and Sam Elliott that debuted in 2016 on Netflix
Fact 4: a dysfunctional family consisting  (context: of two brothers , two brothers' rancher father)
Fact 5: two brothers is two brothers' rancher father
Fact 6: an American comedy web television series starring Ashton Kutcher , Danny Masterson , Debra Winger , Elisha Cuthbert , and Sam Elliott that debuted in 2016 on Netflix debuted  (time: in 2016) (time: on Netflix)
Fact 7: an American comedy web television series starring Ashton Kutcher , Danny Masterson , Debra Winger , Elisha Cuthbert , and Sam Elliott
Fact 8: Each season consists 20 episodes broken up into two parts (context: of 20 episodes broken up into two parts) (context: each containing 10 episodes)
Fact 9: scenes surrounding Ouray and San Miguel Counties
Fact 10: 20 episodes broken up  (location: into two parts)
Fact 11: Garrison is Colorado
Fact 12: Burbank is California
```
</details>

- **Output A:** `The Ranch is an American comedy web television series that details the life of a dysfunctional family consisting of two brothers, their rancher father, and their rancher father's divorced wife. The story takes place on the fictional Iron River Ranch in the fictitious small town of Garrison, Colorado.`
- **Output B:** `The life of the Bennetts, a dysfunctional family consisting of two brothers, two brothers' rancher father, and their rancher father's divorced wife and local bar owner.`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_10 (Sample `d6ca6717`)
**Question:** which president of the united states was a boy scout

**Gold Answer:** `Gerald Ford`

<details><summary>Click to view Evidence Context (290 words)</summary>

```
Fact 1: Requirements include earning at least 21 merit badges and demonstrating Scout Spirit through the Boy Scout Oath and Law , service , and leadership all before or by age 18
Fact 2: the Eagle Scout rank has been earned more than two million young men (time: Since Eagle Scout's introduction in 1911)
Fact 3: a badge that visibly recognizes the accomplishments of the Scout recognizes the accomplishments of the Scout (manner: visibly)
Fact 4: Eagle Scouts are presented a medal and a badge that visibly recognizes the accomplishments of the Scout (context: with a medal and a badge that visibly recognizes the accomplishments of the Scout)
Fact 5: just a small sample of Eagle Scouts are just a small sample of Eagle Scouts
Fact 6: A Scout who attains this rank is called 
Fact 7: This includes an extensive service project that the Scout plans , organizes , leads , and manages
Fact 8: Eagle Scout is the highest rank one can receive in BSA
Fact 9: A Scout who attains this rank attains this rank
Fact 10: Eagle Scouts : is astronaut Neil Armstrong , film director Michael Moore , TV host Mike Rowe , Steven Spielberg , Mayor Michael Bloomberg , Secretary of Defense Robert Gates , and President Gerald Ford
Fact 11: Additional recognition can be earned Eagle Palms (context: awarded for completing additional tenure , leadership , and merit badge requirements) (location: through Eagle Palms)
Fact 12: Requirements earning at least 21 merit badges
Fact 13: an extensive service project that the Scout plans , organizes , leads , and manages plans that
Fact 14: Many famous Americans are 
Fact 15: the highest rank one can receive in BSA can receive  (time: in BSA)
```
</details>

- **Output A:** `President Gerald Ford.`
- **Output B:** `Gerald Ford`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_11 (Sample `b15c9393`)
**Question:** what is the name of son of lord krishna

**Gold Answer:** `Pradyumna`

<details><summary>Click to view Evidence Context (200 words)</summary>

```
Fact 1: A character in the Srimad Bhagavatam was the son of Lord Krishna and Rukmini
Fact 2: the Hindu god is Vishnu
Fact 3: Pradyumna is referred a name of the Hindu god Vishnu (context: being referred to as Vishnu Ankar Gupta) (manner: also)
Fact 4: A character in the Srimad Bhagavatam is one in 24 Keshava Namas ( names ) (context: praised in all pujas)
Fact 5: Pradyumna is considered one of the four vyuha avatars of Vishnu (cause: as one of the four vyuha avatars of Vishnu)
Fact 6: Pradyumna ( Sanskrit : प्रद्युम्न ) is the name of a character in the Srimad Bhagavatam
Fact 7: Pradyumna According was an incarnation of Kamadeva , the god of love (context: According to some accounts)
Fact 8: ( Sanskrit : is प्रद्युम्न
Fact 9: all the 3 letters joint referred  (cause: as जोडाक्षर)
Fact 10: Kamadeva is the god of love
Fact 11: Pradyumna is the only name in Sanskrit with all the 3 letters joint ( referred as जोडाक्षर ) (manner: also)
Fact 12: Pradyumna is ( Sanskrit : प्रद्युम्न )
Fact 13: 24 Keshava Namas ( is names
Fact 14: Affliation is = Avatara of Kamadeva
```
</details>

- **Output A:** `Rukmini's son is Pradyumna.`
- **Output B:** `Pradyumna`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_12 (Sample `222f14e3`)
**Question:** who did the broncos beat in the super bowl

**Gold Answer:** `Green Bay Packers`

<details><summary>Click to view Evidence Context (66 words)</summary>

```
Fact 1: 4         Total Super Bowl championships won 
Fact 2: Mike Shanahan     XXXII     San Diego is CA     Green Bay Packers     31 -- 24     12 -- 4         1998
Fact 3: Mike Shanahan     XXXIII     Miami is FL     Atlanta Falcons     34 -- 19     14 -- 2         2015     Gary Kubiak     50     Santa Clara , CA     Carolina Panthers     24 -- 10     12 --
Fact 4: Gary Kubiak is 50     Santa Clara
```
</details>

- **Output A:** `The provided facts do not contain enough information to answer the question. Fact 1 mentions "Total Super Bowl championships won" but does not specify which team or list the opponents defeated. Facts 2 and 3 mention Mike Shanahan, Gary Kubiak, and specific game scores (e.g., Green Bay Packers 31-24), but do not explicitly state that these teams were the Denver Broncos nor do they identify the opponent for a Super Bowl victory by the Broncos.`
- **Output B:** `Miami Dolphins`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_13 (Sample `ba31eb56`)
**Question:** who is the actress who plays baker on blue bloods

**Gold Answer:** `Abigail Hawk`

<details><summary>Click to view Evidence Context (142 words)</summary>

```
Fact 1: Detective Abigail Baker in Blue Bloods , Riley Thomas in the 2016 holiday TV movie is A Christmas in Vermont , and Ellie in Domenica Cameron - Scorsese 's 2017 directorial debut , Almost Paris
Fact 2: Abigail Hawk born Abigail Diane Gustafson
Fact 3: Abigail Hawk ( born Abigail Diane Gustafson ) is an American actress known for playing Samantha Bonner in the 1995 TV series Reality Check
Fact 4: Hawk won the `` Best Actress '' award (context: For Abigail Hawk ( born Abigail Diane Gustafson )'s performance in Almost Paris) (time: at the 2017 Golden Door Film Festival)
Fact 5: an American actress known  (cause: for playing Samantha Bonner in the 1995 TV series Reality Check)
Fact 6: the 1995 TV series is Reality Check
Fact 7: Cameron - Scorsese 's 2017 directorial debut is Almost Paris
```
</details>

- **Output A:** `Abigail Baker in Blue Bloods is played by Detective Abigail Baker, whose full name is Abigail Diane Gustafson. She is also known as Abigail Hawk.`
- **Output B:** `Abigail Baker`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_14 (Sample `83cbb1e2`)
**Question:** who was the girl in the video brenda got a baby

**Gold Answer:** `Ethel `` Edy '' Proctor`

<details><summary>Click to view Evidence Context (74 words)</summary>

```
Fact 1: The first part Brenda 
Fact 2: Ethel `` Edy '' Proctor portrays Brenda
Fact 3: The video of the song to visualize 
Fact 4: The video of the song is in black - and - white (time: in black - and - white)
Fact 5: The video of the song was made to visualize what Shakur narrates
Fact 6: The first part shows Shakur
Fact 7: the actual story starts  (manner: then)
```
</details>

- **Output A:** `The provided facts do not contain enough information to answer the question. While Fact 2 states that Ethel "Edy" Proctor portrays Brenda, and Facts 5 and 6 mention Shakur in the first part of the video, there is no fact linking Brenda to having a baby or identifying a specific girl associated with that event.`
- **Output B:** `Ethel `` Edy '' Proctor`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_15 (Sample `16422eaa`)
**Question:** who played cosette in les miserables on broadway

**Gold Answer:** `Judy Kuhn`

<details><summary>Click to view Evidence Context (1011 words)</summary>

```
Fact 1: Character     Original French Stage Cast 1980     Original London Cast 1985     Original Broadway Cast     First Broadway Revival 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani     Ramin Karimloo         Javert     Jean Vallée     Roger Allam     Terrence Mann     Norm Lewis     Will Swenson         Fantine     Rose Laurens     Patti LuPone     Randy Graff     Daphne Rubin - Vega     Caissie Levy         Cosette     Fabienne Guyon     Rebecca Caine     Judy Kuhn     Ali Ewoldt     Samantha Hill         Marius     Gilles Buhlmann     Michael Ball     David Bryant     Adam Jacobs     Andy Mientus         Enjolras     Christian Ratellin     David Burt     Michael Maguire     Aaron Lazar     Kyle Scatliffe         Éponine     Marianne Mille     Frances Ruffelle     Celia Keenan - Bolger     Nikki M. James         Thénardier     Yvan Dautin     Alun Armstrong     Leo Burmester     Gary Beach     Cliff Saunders         Madame Thénardier     Marie - France Roussel     Susan Jane Tanner     Jennifer Butt     Jenny Galloway     Keala Matarazzo 
Fact 2: Character     Original French Stage Cast 1980     Original London Cast 1985     Original Broadway Cast     First Broadway Revival is 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani     Ramin Karimloo         Javert     Jean Vallée     Roger Allam     Terrence Mann     Norm Lewis     Will Swenson         Fantine     Rose Laurens     Patti LuPone     Randy Graff
Fact 3: 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani is Ramin Karimloo         Javert     Jean Vallée
Fact 4: Character     Original French Stage Cast 1980     Original London Cast 1985     Original Broadway Cast     First Broadway Revival 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani     Ramin Karimloo         Javert     Jean Vallée     Roger Allam     Terrence Mann     Norm Lewis     Will Swenson         Fantine     Rose Laurens     Patti LuPone     Randy Graff     Daphne Rubin - Vega     Caissie Levy         Cosette     Fabienne Guyon     Rebecca Caine     Judy Kuhn     Ali Ewoldt     Samantha Hill         Marius     Gilles Buhlmann     Michael Ball     David Bryant     Adam Jacobs is Andy Mientus         Enjolras     Christian Ratellin     David Burt
Fact 5: Character     Original French Stage Cast 1980     Original London Cast 1985     Original Broadway Cast     First Broadway Revival 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani     Ramin Karimloo         Javert     Jean Vallée     Roger Allam     Terrence Mann     Norm Lewis     Will Swenson         Fantine     Rose Laurens     Patti LuPone     Randy Graff     Daphne Rubin - Vega     Caissie Levy         Cosette     Fabienne Guyon     Rebecca Caine     Judy Kuhn     Ali Ewoldt     Samantha Hill         Marius     Gilles Buhlmann     Michael Ball     David Bryant     Adam Jacobs     Andy Mientus         Enjolras     Christian Ratellin     David Burt     Michael Maguire     Aaron Lazar     Kyle Scatliffe         Éponine     Marianne Mille     Frances Ruffelle     Celia Keenan - Bolger     Nikki M. James         Thénardier     Yvan Dautin     Alun Armstrong     Leo Burmester     Gary Beach     Cliff Saunders         Madame Thénardier is Marie - France Roussel
Fact 6: Character     Original French Stage Cast 1980     Original London Cast 1985     Original Broadway Cast     First Broadway Revival 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani     Ramin Karimloo         Javert     Jean Vallée     Roger Allam     Terrence Mann     Norm Lewis     Will Swenson         Fantine     Rose Laurens     Patti LuPone     Randy Graff     Daphne Rubin - Vega     Caissie Levy         Cosette     Fabienne Guyon     Rebecca Caine     Judy Kuhn     Ali Ewoldt     Samantha Hill         Marius     Gilles Buhlmann     Michael Ball     David Bryant     Adam Jacobs     Andy Mientus         Enjolras     Christian Ratellin     David Burt     Michael Maguire     Aaron Lazar     Kyle Scatliffe         Éponine     Marianne Mille     Frances Ruffelle     Celia Keenan - Bolger     Nikki M. James         Thénardier     Yvan Dautin     Alun Armstrong     Leo Burmester     Gary Beach     Cliff Saunders         Madame Thénardier     Marie - France Roussel     Susan is Jane Tanner     Jennifer Butt
Fact 7: Character     Original French Stage Cast 1980     Original London Cast 1985     Original Broadway Cast     First Broadway Revival 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani     Ramin Karimloo         Javert     Jean Vallée     Roger Allam     Terrence Mann     Norm Lewis     Will Swenson         Fantine     Rose Laurens     Patti LuPone     Randy Graff     Daphne Rubin - Vega     Caissie Levy         Cosette     Fabienne Guyon     Rebecca Caine     Judy Kuhn     Ali Ewoldt     Samantha Hill         Marius     Gilles Buhlmann     Michael Ball     David Bryant     Adam Jacobs     Andy Mientus         Enjolras     Christian Ratellin     David Burt is Michael Maguire
Fact 8: 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani     Ramin Karimloo         Javert     Jean Vallée is Roger Allam     Terrence Mann     Norm
Fact 9: Character     Original French Stage Cast 1980     Original London Cast 1985     Original Broadway Cast     First Broadway Revival 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani     Ramin Karimloo         Javert     Jean Vallée     Roger Allam     Terrence Mann     Norm Lewis     Will Swenson         Fantine     Rose Laurens     Patti LuPone     Randy Graff     Daphne Rubin - Vega     Caissie Levy         Cosette     Fabienne Guyon     Rebecca Caine     Judy Kuhn     Ali Ewoldt     Samantha Hill         Marius     Gilles Buhlmann     Michael Ball     David Bryant     Adam Jacobs     Andy Mientus         Enjolras     Christian Ratellin     David Burt     Michael Maguire     Aaron Lazar     Kyle Scatliffe         Éponine     Marianne Mille     Frances Ruffelle     Celia Keenan - Bolger     Nikki M. James         Thénardier     Yvan Dautin     Alun Armstrong     Leo Burmester     Gary Beach     Cliff Saunders is Madame Thénardier
Fact 10: Character     Original French Stage Cast 1980     Original London Cast 1985     Original Broadway Cast     First Broadway Revival 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani     Ramin Karimloo         Javert     Jean Vallée     Roger Allam     Terrence Mann     Norm Lewis     Will Swenson         Fantine     Rose Laurens     Patti LuPone     Randy Graff     Daphne Rubin - Vega     Caissie Levy         Cosette     Fabienne Guyon     Rebecca Caine     Judy Kuhn     Ali Ewoldt     Samantha Hill         Marius     Gilles Buhlmann     Michael Ball     David Bryant     Adam Jacobs     Andy Mientus         Enjolras     Christian Ratellin     David Burt     Michael Maguire is Aaron Lazar     Kyle Scatliffe         Éponine
Fact 11: Character     Original French Stage Cast 1980     Original London Cast 1985     Original Broadway Cast     First Broadway Revival 2006     Second Broadway Revival 2014         Jean Valjean     Maurice Barrier     Colm Wilkinson     Alexander Gemignani     Ramin Karimloo         Javert     Jean Vallée     Roger Allam     Terrence Mann     Norm Lewis     Will Swenson         Fantine     Rose Laurens     Patti LuPone     Randy Graff     Daphne Rubin - Vega     Caissie Levy         Cosette     Fabienne Guyon     Rebecca Caine     Judy Kuhn     Ali Ewoldt     Samantha Hill         Marius     Gilles Buhlmann     Michael Ball     David Bryant     Adam Jacobs     Andy Mientus         Enjolras     Christian Ratellin     David Burt     Michael Maguire     Aaron Lazar     Kyle Scatliffe         Éponine     Marianne Mille     Frances Ruffelle     Celia Keenan - Bolger     Nikki M. James         Thénardier     Yvan Dautin     Alun Armstrong     Leo Burmester     Gary Beach     Cliff Saunders         Madame Thénardier     Marie - France Roussel     Susan Jane Tanner     Jennifer Butt     Jenny Galloway     Keala Settle         Gavroche     Florence Davis Cyrille Dupont Fabrice Ploquin     Ian Tucker Oliver Spencer is Liza Hayden
Fact 12: Leo Burmester is Gary Beach
Fact 13: Andy Mientus         Enjolras     Christian Ratellin is David Burt
```
</details>

- **Output A:** `Rebecca Caine, Judy Kuhn, Ali Ewoldt, Samantha Hill`
- **Output B:** `Based on the provided facts, the following actors played Cosette in Les Misérables on Broadway:

*   **Original Broadway Cast:** Judy Kuhn
*   **First Broadway Revival (2006):** Ali Ewoldt
*   **Second Broadway Revival (2014):** Samantha Hill`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_16 (Sample `fba18e97`)
**Question:** when did clifford the big red dog first air on tv

**Gold Answer:** `September 4 , 2000`

<details><summary>Click to view Evidence Context (183 words)</summary>

```
Fact 1: Clifford the Big Red Dog aired PBS Kids (context: Produced by Scholastic Productions) (manner: originally) (time: on PBS Kids) (time: from September 4 , 2000 to February 25 , 2003)
Fact 2: The UK version ( where Clifford the Big Red Dog was dubbed with British voice actors replacing the original American soundtrack ) originally aired on BBC 2 on April 1 , 2002 . was dubbed  (context: with British voice actors replacing the original American soundtrack) (manner: where)
Fact 3: Clifford is the Big Red Dog
Fact 4: Clifford the Big Red Dog version 
Fact 5: Clifford the Big Red Dog is an American - British educational animated children 's television series , based upon Norman Bridwell 's children 's book series of the same name
Fact 6: The UK version aired  (manner: originally) (time: on BBC 2) (time: on April 1 , 2002)
Fact 7: an American - British educational animated children 's television series based  (location: upon Norman Bridwell 's children 's book series of the same name)
Fact 8: British voice actors replacing the original American soundtrack
```
</details>

- **Output A:** `Clifford the Big Red Dog first aired on TV on September 4, 2000.`
- **Output B:** `September 4 , 2000`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_17 (Sample `dd1d2b8f`)
**Question:** what is the strongest earthquake in the united states

**Gold Answer:** `1964 Alaska earthquake and tsunami`

<details><summary>Click to view Evidence Context (1584 words)</summary>

```
Fact 1: Santa Barbara is earthquake
Fact 2: 3,000 +     1906 San Francisco earthquake             000000001909 - 09 - 27 - 0000 is September 27 , 1909
Fact 3: Date     State ( s )     Magnitude     Fatalities     Article     Further information         000000001700 - 01 - 26 - 0000 January 26 , 1700     Washington , Oregon , California     8.7 -- 9.2     Unknown     1700 Cascadia earthquake             000000001755 - 11 - 18 - 0000 November 18 , 1755     Massachusetts     5.9     Unknown     1755 Cape Ann earthquake             000000001811 - 12 - 16 - 0000 December 16 , 1811     Missouri     7.2 -- 8.1     Unknown     1811 -- 1812 New Madrid earthquakes             000000001812 - 12 - 08 - 0000 December 8 , 1812     California     6.9 -- 7.5     7001400000000000000 ♠ 40 +     1812 San Juan Capistrano earthquake             000000001857 - 01 - 09 - 0000 January 9 , 1857     California     7.9     7000200000000000000 ♠ 2     1857 Fort Tejon earthquake             000000001867 - 04 - 24 - 0000 April 24 , 1867     Kansas     5.1     5000000000000000000 ♠ 0     1867 Manhattan , Kansas earthquake             000000001868 - 04 - 02 - 0000 April 2 , 1868     Hawaii     7.9     7001770000000000000 ♠ 77     1868 Hawaii earthquake and tsunami             000000001868 - 10 - 21 - 0000 October 21 , 1868     California     6.3 -- 6.7     7001300000000000000 ♠ 30     1868 Hayward earthquake             000000001872 - 12 - 14 - 0000 December 14 , 1872     Washington     6.5 -- 7.0     5000000000000000000 ♠ 0     1872 North Cascades earthquake             000000001872 - 03 - 26 - 0000 March 26 , 1872     California     7.4 -- 7.9     7001270000000000000 ♠ 27     1872 Lone Pine earthquake             000000001886 - 08 - 31 - 0000 August 31 , 1886     South Carolina     6.9 -- 7.3     7001600000000000000 ♠ 60     1886 Charleston earthquake             000000001906 - 04 - 18 - 0000 April 18 , 1906     California     7.9     7003300000000000000 ♠ is 3,000 +     1906 San Francisco earthquake             000000001909 - 09 - 27 - 0000 September 27 , 1909     Indiana     5.1     5000000000000000000 ♠ 0     1909 Wabash River earthquake             000000001915 - 10 - 03 - 0000 October 3 , 1915     Nevada     7.1     5000000000000000000
Fact 4: Date     State ( s )     Magnitude     Fatalities     Article     Further information         000000001700 - 01 - 26 - 0000 January 26 , 1700     Washington , Oregon , California     8.7 -- 9.2 is Unknown     1700 Cascadia earthquake             000000001755 - 11 - 18 - 0000 November 18 , 1755     Massachusetts     5.9     Unknown     1755 Cape Ann earthquake             000000001811 - 12 - 16 - 0000
Fact 5: 77     1868 Hawaii earthquake and tsunami             000000001868 - 10 - 21 - 0000 is October 21
Fact 6: Date     State ( s )     Magnitude     Fatalities     Article     Further information         000000001700 - 01 - 26 - 0000 January 26 , 1700     Washington , Oregon , California     8.7 -- 9.2     Unknown     1700 Cascadia earthquake             000000001755 - 11 - 18 - 0000 November 18 , 1755     Massachusetts     5.9     Unknown     1755 Cape Ann earthquake             000000001811 - 12 - 16 - 0000 December 16 , 1811     Missouri     7.2 -- 8.1     Unknown     1811 -- 1812 New Madrid earthquakes             000000001812 - 12 - 08 - 0000 December 8 , 1812     California     6.9 -- 7.5     7001400000000000000 ♠ 40 +     1812 San Juan Capistrano earthquake             000000001857 - 01 - 09 - 0000 January 9 , 1857     California     7.9     7000200000000000000 ♠ 2     1857 Fort Tejon earthquake             000000001867 - 04 - 24 - 0000 April 24 , 1867     Kansas     5.1     5000000000000000000 ♠ 0     1867 Manhattan , Kansas earthquake             000000001868 - 04 - 02 - 0000 April 2 , 1868     Hawaii     7.9     7001770000000000000 ♠ 77     1868 Hawaii earthquake and tsunami             000000001868 - 10 - 21 - 0000 October 21 , 1868     California     6.3 -- 6.7     7001300000000000000 ♠ 30     1868 Hayward earthquake             000000001872 - 12 - 14 - 0000 December 14 , 1872     Washington     6.5 -- 7.0     5000000000000000000 ♠ 0     1872 North Cascades earthquake             000000001872 - 03 - 26 - 0000 March 26 , 1872     California     7.4 -- 7.9     7001270000000000000 ♠ 27     1872 Lone Pine earthquake             000000001886 - 08 - 31 - 0000 August 31 , 1886     South Carolina     6.9 -- 7.3     7001600000000000000 ♠ 60     1886 Charleston earthquake             000000001906 - 04 - 18 - 0000 April 18 , 1906     California     7.9     7003300000000000000 ♠ 3,000 +     1906 San Francisco earthquake             000000001909 - 09 - 27 - 0000 September 27 , 1909     Indiana     5.1     5000000000000000000 ♠ 0     1909 Wabash River earthquake             000000001915 - 10 - 03 - 0000 October 3 , 1915     Nevada     7.1     5000000000000000000 ♠ 0     1915 Pleasant Valley earthquake             000000001925 - 06 - 29 - 0000 June 29 , 1925     California     6.8     7001130000000000000 ♠ 13     1925 Santa Barbara earthquake             000000001931 - 08 - 16 - 0000 August 16 , 1931     Texas     5.8     5000000000000000000 ♠ 0     1931 Valentine earthquake             000000001933 - 03 - 10 - 0000 March 10 , 1933     California     6.4     7002120000000000000 ♠ is 120     1933 Long Beach earthquake             000000001936 - 07 - 15 - 0000 July 15 , 1936     Oregon , Washington     5.8     5000000000000000000
Fact 7: Date     State ( s )     Magnitude     Fatalities     Article     Further information         000000001700 - 01 - 26 - 0000 January 26 , 1700     Washington , Oregon , California     8.7 -- 9.2     Unknown     1700 Cascadia earthquake             000000001755 - 11 - 18 - 0000 November 18 , 1755     Massachusetts     5.9     Unknown     1755 Cape Ann earthquake             000000001811 - 12 - 16 - 0000 December 16 , 1811     Missouri     7.2 -- 8.1     Unknown     1811 -- 1812 New Madrid earthquakes             000000001812 - 12 - 08 - 0000 December 8 , 1812     California     6.9 -- 7.5     7001400000000000000 ♠ 40 +     1812 San Juan Capistrano earthquake             000000001857 - 01 - 09 - 0000 January 9 , 1857     California     7.9     7000200000000000000 ♠ 2     1857 Fort Tejon earthquake             000000001867 - 04 - 24 - 0000 April 24 , 1867     Kansas     5.1     5000000000000000000 ♠ 0     1867 Manhattan , Kansas earthquake             000000001868 - 04 - 02 - 0000 April 2 , 1868     Hawaii     7.9     7001770000000000000 ♠ 77     1868 Hawaii earthquake and tsunami             000000001868 - 10 - 21 - 0000 October 21 , 1868     California     6.3 -- 6.7     7001300000000000000 ♠ 30     1868 Hayward earthquake             000000001872 - 12 - 14 - 0000 December 14 , 1872     Washington     6.5 -- 7.0     5000000000000000000 ♠ 0     1872 North Cascades earthquake             000000001872 - 03 - 26 - 0000 March 26 , 1872     California     7.4 -- 7.9     7001270000000000000 ♠ 27     1872 Lone Pine earthquake             000000001886 - 08 - 31 - 0000 August 31 , 1886     South Carolina     6.9 -- 7.3     7001600000000000000 ♠ 60     1886 Charleston earthquake             000000001906 - 04 - 18 - 0000 April 18 , 1906     California     7.9     7003300000000000000 ♠ 3,000 +     1906 San Francisco earthquake             000000001909 - 09 - 27 - 0000 September 27 , 1909     Indiana     5.1     5000000000000000000 ♠ 0     1909 Wabash River earthquake             000000001915 - 10 - 03 - 0000 October 3 , 1915     Nevada     7.1     5000000000000000000 ♠ 0     1915 Pleasant Valley earthquake             000000001925 - 06 - 29 - 0000 June 29 , 1925     California     6.8     7001130000000000000 ♠ 13     1925 is Santa Barbara earthquake             000000001931 - 08 - 16 - 0000 August 16 , 1931     Texas
Fact 8: Date     State ( s )     Magnitude     Fatalities     Article is Further information         000000001700 - 01 - 26 - 0000 January 26 , 1700     Washington , Oregon , California     8.7 -- 9.2
Fact 9: Date     State ( s )     Magnitude     Fatalities     Article     Further information         000000001700 - 01 - 26 - 0000 January 26 , 1700     Washington , Oregon , California     8.7 -- 9.2     Unknown     1700 Cascadia earthquake             000000001755 - 11 - 18 - 0000 November 18 , 1755     Massachusetts     5.9     Unknown     1755 Cape Ann earthquake             000000001811 - 12 - 16 - 0000 December 16 , 1811     Missouri     7.2 -- 8.1     Unknown     1811 -- 1812 New Madrid earthquakes             000000001812 - 12 - 08 - 0000 December 8 , 1812     California     6.9 -- 7.5     7001400000000000000 ♠ 40 +     1812 is San Juan Capistrano earthquake
Fact 10: Unknown     1700 Cascadia earthquake             000000001755 - 11 - 18 - 0000 November 18 is 1755     Massachusetts     5.9     Unknown     1755 Cape Ann earthquake             000000001811 - 12 - 16 - 0000
Fact 11: Date     State ( s )     Magnitude     Fatalities     Article     Further information         000000001700 - 01 - 26 - 0000 January 26 , 1700     Washington , Oregon , California     8.7 -- 9.2     Unknown     1700 Cascadia earthquake             000000001755 - 11 - 18 - 0000 November 18 , 1755     Massachusetts     5.9     Unknown     1755 Cape Ann earthquake             000000001811 - 12 - 16 - 0000 December 16 , 1811     Missouri     7.2 -- 8.1     Unknown     1811 -- 1812 New Madrid earthquakes             000000001812 - 12 - 08 - 0000 December 8 , 1812     California     6.9 -- 7.5     7001400000000000000 ♠ 40 +     1812 San Juan Capistrano earthquake             000000001857 - 01 - 09 - 0000 January 9 , 1857     California     7.9     7000200000000000000 ♠ 2     1857 Fort Tejon earthquake             000000001867 - 04 - 24 - 0000 April 24 , 1867     Kansas     5.1     5000000000000000000 ♠ 0     1867 Manhattan , Kansas earthquake             000000001868 - 04 - 02 - 0000 April 2 , 1868     Hawaii     7.9     7001770000000000000 ♠ 77     1868 Hawaii earthquake and tsunami             000000001868 - 10 - 21 - 0000 October 21 , 1868     California     6.3 -- 6.7     7001300000000000000 ♠ 30     1868 Hayward earthquake             000000001872 - 12 - 14 - 0000 December 14 , 1872     Washington     6.5 -- 7.0     5000000000000000000 ♠ 0     1872 is North Cascades earthquake             000000001872 - 03 - 26 - 0000
Fact 12: 3,000 +     1906 San Francisco earthquake             000000001909 - 09 - 27 - 0000 September 27 , 1909     Indiana     5.1     5000000000000000000 ♠ 0 is 1909 Wabash River earthquake             000000001915 - 10 - 03 - 0000
Fact 13: May 18 , 1940     California     6.9     7000900000000000000 ♠ 9     1940 El Centro earthquake             000000001940 - 12 - 20 - 0000 December 20 , 1940     New Hampshire     5.3     5000000000000000000 ♠ 0 is 1940 New Hampshire earthquakes
```
</details>

- **Output A:** `Based on the provided facts, the strongest earthquake recorded in the United States was the **1700 Cascadia earthquake**.

According to Fact 8 and Fact 9, this event occurred on January 26, 1700, along the coast of Washington, Oregon, and California. It had an estimated magnitude of **8.7 to 9.2**, which is higher than any other earthquake listed in the text (the next highest being the 1906 San Francisco earthquake at 7.9).`
- **Output B:** `Based on the provided facts, the strongest earthquake recorded in the United States was the **1700 Cascadia earthquake**.

According to Fact 8 and Fact 9, this event occurred on January 26, 1700, along the coast of Washington, Oregon, and California. It had an estimated magnitude of **8.7 to 9.2**, which is higher than any other earthquake listed in the text (the next highest being the 1906 San Francisco earthquake at 7.9).`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_18 (Sample `3fa881ba`)
**Question:** when does the eclipse end in the us

**Gold Answer:** `6 : 44 p.m. UTC ( 2 : 44 p.m. EDT )`

<details><summary>Click to view Evidence Context (273 words)</summary>

```
Fact 1: the total eclipse 's land coverage ended  (location: along the South Carolina coast) (manner: 2) (time: at about 6 : 44 p.m. UTC)
Fact 2: The event 's shadow began to cover land on the Oregon coast as a partial eclipse at 4 (time: p.m.) (time: with the total eclipse beginning there at 5 : 16 p.m. UTC ( 10 : 16 a.m. PDT ))
Fact 3: the total eclipse beginning  (manner: there) (time: at 5 : 16 p.m.)
Fact 4: no solar eclipse NOT had been visible (context: not since the February 1979 eclipse had a total eclipse been visible from anywhere in the mainland United States) (location: across the entire contiguous United States) (manner: Prior) (time: since June 8 , 1918)
Fact 5: the rest of the U.S. had a partial eclipse
Fact 6: The event 's shadow to cover land (cause: as a partial eclipse at 4) (location: on the Oregon coast)
Fact 7: the total eclipse beginning there at 5 : 16 p.m. is UTC
Fact 8: Hawaii began sunrise (context: with sunrise) (manner: Visibility) (time: at 4 : 20 p.m.)
Fact 9: Hawaii ended 5 : 25 p.m. (time: UTC)
Fact 10: UTC ( is 6 : 20 a.m. HST
Fact 11: : 44 p.m. is EDT
Fact 12: The path of totality touched 14 states
Fact 13: UTC ( is 7 : 25 a.m. HST
Fact 14: The area of the path of totality NOT was about 16 percent of the area of the United States (context: with most of this area over the ocean , not land)
Fact 15: the ocean is not land
```
</details>

- **Output A:** `at about 6 : 44 p.m. UTC`
- **Output B:** `The total eclipse's land coverage ended at about 6:44 p.m. UTC along the South Carolina coast.`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_19 (Sample `46b13e70`)
**Question:** when did the steel mills closed in youngstown ohio

**Gold Answer:** `September 19 , 1977`

<details><summary>Click to view Evidence Context (178 words)</summary>

```
Fact 1: Youngstown 's economy has been impacted a loss of the steel industry jobs which started on September 19 , 1977 (time: on what became known to locals as `` Black Monday)
Fact 2: the city 's population was halved the Mahoning Valley region , where Youngstown is located (context: while non-industrial businesses were forced to close or relocate due to cascading effects resulting from Youngstown 's deindustrialization) (location: In the Mahoning Valley region , where Youngstown is located)
Fact 3: Youngstown 's economic struggles have been documented  (context: While the loss of steel industry jobs in the region coincided with the general deindustrialization of Rust Belt cities such as Youngstown as well as the United States as a whole) (manner: well)
Fact 4: the steel industry jobs which started on September 19 , 1977 started  (time: on September 19 , 1977)
Fact 5: Youngstown 's economy continued  (time: into the mid-1980s)
Fact 6: the Mahoning Valley region , where Youngstown is located is located  (manner: where)
Fact 7: cascading effects resulting  (time: from Youngstown 's deindustrialization)
```
</details>

- **Output A:** `September 19, 1977`
- **Output B:** `The provided facts do not contain enough information to answer the question. Fact 1 states that a loss of steel industry jobs started on September 19, 1977, but it does not specify when the steel mills closed.`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_20 (Sample `97147d1f`)
**Question:** who want to be a millionaire calls his dad

**Gold Answer:** `Carpenter`

<details><summary>Click to view Evidence Context (147 words)</summary>

```
Fact 1: Carpenter NOT to call Carpenter's father (cause: not for help , but rather to tell his father Carpenter was going to win the game)
Fact 2: episode of Millionaire , Carpenter proceeded to advance to the million - dollar question without using any lifelines (time: On the November 19 , 1999)
Fact 3: Carpenter's win led  (recipient: multiple talk show appearances , as well as reappearances on Millionaire Millionaire) (time: to multiple talk show appearances , as well as reappearances on Millionaire Millionaire)
Fact 4: the show 's first millionaire became 
Fact 5: episode of Millionaire , Carpenter to advance  (context: without using any lifelines) (time: to the million - dollar question)
Fact 6: Carpenter's win gave Carpenter national recognition
Fact 7: Carpenter answered the question (manner: correctly)
Fact 8: Carpenter proceeded  (time: On the November 19 , 1999)
Fact 9: Carpenter NOT was used
```
</details>

- **Output A:** `The provided facts do not contain enough information to answer the question. Fact 1 states that "Carpenter NOT to call Carpenter's father," but it does not specify who else wants to be a millionaire or if they call their dad.`
- **Output B:** `Carpenter`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_21 (Sample `bd229593`)
**Question:** where does the last name cintron come from

**Gold Answer:** `Portuguese and Spanish - French origins`

<details><summary>Click to view Evidence Context (59 words)</summary>

```
Fact 1: Cintrón or Cintron is a surname of Portuguese and Spanish - French origins
Fact 2: the surname is Cintron
Fact 3: Cintron is 
Fact 4: The name migrated a consequence of the conquest and settlement of the New World (cause: as a consequence of the conquest and settlement of the New World) (location: particularly in Puerto Rico)
```
</details>

- **Output A:** `The surname Cintrón or Cintron is of Portuguese and Spanish-French origins.`
- **Output B:** `Portuguese and Spanish - French origins`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_22 (Sample `d4d35bf0`)
**Question:** when did audio video and the film industry begin

**Gold Answer:** `in the mid - to late 1920s`

<details><summary>Click to view Evidence Context (271 words)</summary>

```
Fact 1: The earliest feature - length movies with recorded sound included only music and effects
Fact 2: The primary steps in the commercialization of sound cinema were taken the mid - (recipient: late 1920s) (time: in the mid -) (time: to late 1920s)
Fact 3: The first feature film presented  (cause: as a talkie) (manner: originally)
Fact 4: the sound films which included synchronized dialogue , known as `` talking pictures '' , or `` talkies '' included synchronized dialogue , known as `` talking pictures '' , or `` talkies ''
Fact 5: the sound films which included synchronized dialogue , known as `` talking pictures '' , or `` talkies '' were exclusively shorts (time: At first)
Fact 6: The earliest feature - length movies with recorded sound included effects
Fact 7: Vitaphone , which was at the time the leading brand of sound - on - disc technology was the leading brand of sound - on - disc technology (time: at the time)
Fact 8: A major hit was made Vitaphone , which was at the time the leading brand of sound - on - disc technology (context: with Vitaphone , which was at the time the leading brand of sound - on - disc technology)
Fact 9: The first feature film presented  (cause: as a talkie) (manner: originally)
Fact 10: The first feature film originally presented as a talkie was The Jazz Singer , released in October 1927
Fact 11: The Jazz Singer released  (time: in October 1927)
Fact 12: which included `` talkies ''
Fact 13: synchronized dialogue known  (cause: as `` talking pictures '')
```
</details>

- **Output A:** `The provided facts do not contain enough information to answer when the audio video and the film industry began. The facts only state that the earliest feature-length movies with recorded sound included music, effects, and later synchronized dialogue (talkies), and that the primary steps in the commercialization of sound cinema were taken in the mid- to late 1920s. They do not specify when audio video or the film industry as a whole began.`
- **Output B:** `mid - late 1920s`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_23 (Sample `b41e1f3f`)
**Question:** why 26 january is celebrated as republic day in hindi

**Gold Answer:** `the Constitution of India came into effect on 26 January 1950`

<details><summary>Click to view Evidence Context (84 words)</summary>

```
Fact 1: Republic Day honours the date on which the Constitution of India came into effect on 26 January 1950 replacing the Government of India Act ( 1935 ) (location: as the governing document of India)
Fact 2: the date on which the Constitution of India came into effect on 26 January 1950 replacing the Government of India Act ( 1935 ) came  (context: replacing the Government of India Act ( 1935 )) (location: into effect) (time: on which) (time: on 26 January 1950)
```
</details>

- **Output A:** `Constitution of India came into effect on 26 January 1950 replacing the Government of India Act (1935)`
- **Output B:** `Republic Day honours the date on which the Constitution of India came into effect on 26 January 1950 replacing the Government of India Act (1935).`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_24 (Sample `3dc288ae`)
**Question:** the meaning of the song piece by piece

**Gold Answer:** `restoring someone 's faith in love and family relationships`

<details><summary>Click to view Evidence Context (235 words)</summary>

```
Fact 1: A midtempo pop song about restoring someone 's faith in love and family relationships promulgated Piece by Piece '' (cause: as a sequel to the song) (cause: Because of You '' ( 2004 ) but with a `` happy ending '')
Fact 2: American singer Kelly Clarkson co wrote the track (context: with `` Piece by Piece '''s producer Greg Kurstin)
Fact 3: Piece by Piece is a song by American singer Kelly Clarkson taken from American singer Kelly Clarkson's seventh studio album of the same name
Fact 4: American singer Kelly Clarkson NOT wrote the song (context: whose neglect of her husband 's' family was used as a juxtaposition to her husband 's unconditional love for her and their daughter , whom they both promised to never abandon) (time: in a first - person narrative to American singer Kelly Clarkson's father ,)
Fact 5: a song by American singer Kelly Clarkson taken from American singer Kelly Clarkson's seventh studio album of the same name taken  (time: from American singer Kelly Clarkson's seventh studio album of the same name)
Fact 6: American singer Kelly Clarkson NOT co - (manner: introspectively) (time: After a discussion with American singer Kelly Clarkson's sister about their family life)
Fact 7: her husband 's unconditional love for her and their daughter , whom they both promised to never abandon NOT promised whom they both promised to never abandon
```
</details>

- **Output A:** `restoring someone's faith in love and family relationships`
- **Output B:** `The provided facts do not contain enough information to answer the question about the meaning of the song "Piece by Piece." While Fact 1 mentions the song is "about restoring someone's faith in love and family relationships," it does not provide a comprehensive or explicit definition of the song's overall meaning beyond this specific theme.`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_25 (Sample `de892fce`)
**Question:** who won in the brown vs board of education case

**Gold Answer:** `defendants`

<details><summary>Click to view Evidence Context (462 words)</summary>

```
Fact 1: Brown v. Board of Education         Supreme Court of the United States Argued  (context: Reargued December 8 , 1953) (time: December) [attributed to Brown v. Board of Education         Supreme Court of the United States]
Fact 2: Brown v. Board of Education         Supreme Court of the United States Decided May 17 , 1954
Fact 3: 2d 1212 ( D. Kan . 1999 )         Holding         Segregation of students in public schools violates the Equal Protection Clause of the Fourteenth Amendment (context: because separate facilities are inherently unequal)
Fact 4: judgment reinstated judgment for defendants , 56 F. Supp (manner: 2d)
Fact 5: Full case name     Oliver Brown is et al
Fact 6: This case overturned a previous ruling or rulings         Plessy v. Ferguson ( 1896 )
Fact 7: 468 ( D. Kan . 1955 ) ; motion to intervene granted , 84 F.R.D. 383 ( D. Kan . 1979 ) ; judgment for defendants , 671 F. Supp. 1290 ( D. Kan . 1987 ) ; reversed  (manner: Cir)
Fact 8: District Court of Kansas reversed 
Fact 9: Subsequent history     Judgment on relief is 349 U.S. 294 ( 1955 ) ( Brown II )
Fact 10: Court membership             Chief Justice     Earl Warren     Associate Justices     Hugo Black Stanley F. Reed Felix Frankfurter William O. Douglas Robert H. Jackson Harold H. Burton Tom C. Clark Sherman Minton             Case opinions         Majority     Warren , joined by unanimous         Laws applied U.S. Const
Fact 11: 468 ( D. Kan . 1955 ) ; motion to intervene granted , 84 F.R.D. 383 ( D. Kan . 1979 ) ; judgment for defendants , 671 F. Supp. 1290 ( D. Kan . 1987 ) ; vacated  (manner: U.S.)
Fact 12: unanimous         Laws joined Court membership             Chief Justice     Earl Warren     Associate Justices     Hugo Black Stanley F. Reed Felix Frankfurter William O. Douglas Robert H. Jackson Harold H. Burton Tom C. Clark Sherman Minton             Case opinions
Fact 13: judgment for defendants , 671 F. Supp. 1290 ( D. Kan . reversed  (manner: Cir)
Fact 14: Prior history     Judgment for defendants is 98 F. Supp
Fact 15: defendants is 56 F. Supp
Fact 16: Court membership             Chief Justice     Earl Warren is Associate Justices
Fact 17: motion to intervene granted , 84 F.R.D. 383 ( D. Kan . 1979 ) reversed  (manner: Cir)
Fact 18: 1954 U.S. LEXIS 2094 ; is 53 Ohio Op
Fact 19: judgment for defendants , 671 F. Supp. 1290 is ( D. Kan
Fact 20: motion intervene granted 
Fact 21: motion to intervene granted , 84 F.R.D. 383 is ( D. Kan
Fact 22: Citations is 347 U.S. 483
Fact 23: Citations     347 U.S. 483 ( more ) 74 S. Ct. 686 ; is 98 L. Ed
Fact 24: Citations     347 U.S. 483 is ( more ) 74 S. Ct.
```
</details>

- **Output A:** `defendants`
- **Output B:** `The defendants won in the Brown v. Board of Education case.`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_26 (Sample `83c34a0a`)
**Question:** what is the normal range for plasma glucose concentration

**Gold Answer:** `3.9 and 5.5 mmol / L ( 70 to 100 mg / dL )`

<details><summary>Click to view Evidence Context (270 words)</summary>

```
Fact 1: The blood glucose target range for diabetics according should be 5.0 -- 7.2 mmol / l ( 90 (context: according to the American Diabetes Association) (time: before meals , and less than 10 mmol / L ( 180 mg / dL )) (time: after meals ( as measured by a blood glucose monitor ))
Fact 2: this level fluctuates The mean normal blood glucose level in humans is about 5.5 mmol / L ( 100 mg / dL ) (manner: however) (time: throughout the day)
Fact 3: The normal blood glucose level ( tested while fasting ) for non-diabetics should be between 3.9 and 5.5 mmol / L ( 70 to 100 mg / dL ) (time: between 3.9 and 5.5 mmol / L ( 70 to 100 mg / dL ))
Fact 4: The normal blood glucose level tested  (cause: for non-diabetics) (context: while fasting)
Fact 5: a blood glucose monitor measured meals
Fact 6: Blood sugar levels for those without diabetes and who are not fasting NOT should be below 6.9 mmol / L ( 125 mg / dL ) (location: below 6.9 mmol / L ( 125 mg / dL ))
Fact 7: The mean normal blood glucose level in humans is 
Fact 8: less than 10 mmol / L ( is 180 mg / dL
Fact 9: 3.9 and 5.5 mmol / L ( is 70 to 100 mg / dL
Fact 10: who are not fasting NOT should be  (location: below 6.9 mmol / L ( 125 mg / dL ))
Fact 11: 6.9 mmol / L is ( 125 mg / dL
```
</details>

- **Output A:** `3.9 and 5.5 mmol / L ( 70 to 100 mg / dL )`
- **Output B:** `The provided facts do not contain enough information to answer the question explicitly, as they define ranges for specific conditions (diabetics, non-diabetics fasting) and mean levels but do not state a single "normal range for plasma glucose concentration" without qualification.`

**Transition Status:** `Prompt-Correction`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_27 (Sample `e6b46a70`)
**Question:** what is the difference between an opiate agonist and antagonist

**Gold Answer:** `a substance that fully activates the receptor that it binds to`

<details><summary>Click to view Evidence Context (218 words)</summary>

```
Fact 1: which NOT is used to refer to a drug which under some conditions behaves as an agonist ( a substance that fully activates the receptor that it binds to (context: while under other conditions , behaves as an antagonist ( a substance that binds to a receptor but does not activate and can block the activity of other agonists )) (time: In pharmacology the term agonist - antagonist or mixed agonist / antagonist)
Fact 2: a drug which under some conditions behaves as an agonist ( a substance that fully activates the receptor that it binds to behaves  (cause: as an agonist ( a substance that fully activates the receptor that it binds to) (time: under some conditions)
Fact 3: a substance that fully activates the receptor that it binds to activates the receptor that it binds to (manner: fully)
Fact 4: an agonist ( is a substance that fully activates the receptor that it binds to
Fact 5: which NOT to refer  (time: to a drug which under some conditions behaves as an agonist ( a substance that fully activates the receptor that it binds to)
Fact 6: the receptor that it binds to binds  (time: that it binds to)
Fact 7: a substance that binds to a receptor but binds  (time: to a receptor)
```
</details>

- **Output A:** `Insufficient information`
- **Output B:** `Based on the provided facts, the document does not contain information about "opiate" agonists or antagonists. The available facts only define general terms for **agonists** (substances that fully activate the receptor they bind to) and **antagonists** (substances that bind to a receptor but do not activate it), without specifying their relationship to opiates.`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_28 (Sample `8b961e2f`)
**Question:** when did the subway open in new york

**Gold Answer:** `1904`

<details><summary>Click to view Evidence Context (196 words)</summary>

```
Fact 1: the New York City Subway Opened is one of the world 's oldest public transit systems , one of the world 's most used metro systems , and the metro system with the most stations (context: Opened in 1904)
Fact 2: The New York City Subway is leased a rapid transit system owned by the City of New York
Fact 3: The New York City Subway offers service (time: on every day of the year)
Fact 4: The New York City Subway leased  (recipient: the New York City Transit Authority , a subsidiary agency of the state - run Metropolitan Transportation Authority ( MTA )) (time: to the New York City Transit Authority , a subsidiary agency of the state - run Metropolitan Transportation Authority ( MTA ))
Fact 5: The New York City Subway offers 24 hours per day (time: on every day of the year)
Fact 6: the New York City Transit Authority is a subsidiary agency of the state - run Metropolitan Transportation Authority ( MTA )
Fact 7: the City of New York owned a rapid transit system
Fact 8: the state - run Metropolitan Transportation Authority ( is MTA
```
</details>

- **Output A:** `1904`
- **Output B:** `1904`

**Transition Status:** `Persistent-Success`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_29 (Sample `f68f4a35`)
**Question:** who has won the most games in nfl 2017

**Gold Answer:** `Dallas Cowboys`

<details><summary>Click to view Evidence Context (54 words)</summary>

```
Fact 1: 1,202     NFC East is 17     Carolina Panthers
Fact 2: First NFL Season     Total Games     Division is Dallas Cowboys     502
Fact 3: NFC North is 7     Baltimore Ravens
Fact 4: 1,135     NFC West is 20     Cleveland Browns     462     482
Fact 5: 558     1960     884     AFC East is 6     Minnesota Vikings     470     390     10
```
</details>

- **Output A:** `Based on the provided facts, it is not possible to determine who has won the most games in NFL 2017. The facts list teams and numbers but do not specify which year corresponds to those statistics, nor do they explicitly state win counts for any team in 2017.`
- **Output B:** `Insufficient information`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

## REV_30 (Sample `0162fe58`)
**Question:** what movie is count on me by bruno mars in

**Gold Answer:** `A Turtle 's Tale : Sammy 's Adventures`

<details><summary>Click to view Evidence Context (366 words)</summary>

```
Fact 1: The 2016 Hyundai Genesis and Mars ' song is featured in the film , Diary of a Wimpy Kid : is featured the film , Diary of a Wimpy Kid (time: in the film , Diary of a Wimpy Kid)
Fact 2: that featured the 2016 Hyundai Genesis and Mars ' song (context: and was used for a Hyundai ' s commercial , during the Super Bowl XLVIII 's fourth quarter , entitled `` Dad 's Sixth Sense '')
Fact 3: The 2016 Hyundai Genesis and Mars ' song was chosen reasons separate and coincidental from Mars ' previously announced Half Time gig '' (location: for reasons separate and coincidental from Mars ' previously announced Half Time gig '')
Fact 4: The recording has been featured two different commercials for the Blue Cross Blue Shield Association (time: on two different commercials for the Blue Cross Blue Shield Association)
Fact 5: the film is Diary of a Wimpy Kid
Fact 6: The recording is part of the Belgian / American animated film A Turtle 's Tale
Fact 7: The 2016 Hyundai Genesis and Mars ' song is featured in the film , Diary of a Wimpy Kid : is The Long Haul
Fact 8: the Belgian / American animated film is A Turtle 's Tale
Fact 9: The track was included the Songs for the Philippines relief album , which was compiled to help the victims of Typhoon Haiyan since `` all proceeds '' were donated to the Philippine Red Cross (location: on the Songs for the Philippines relief album , which was compiled to help the victims of Typhoon Haiyan since `` all proceeds '' were donated to the Philippine Red Cross)
Fact 10: Sammy 's Adventures and the TV show is Suburgatory
Fact 11: both took place
Fact 12: reasons announced Half Time gig (manner: previously)
Fact 13: both took one in Illinois
Fact 14: the Philippines relief album , which was compiled to help the victims of Typhoon Haiyan since `` all proceeds '' were donated to the Philippine Red Cross was compiled to help the victims of Typhoon Haiyan since `` all proceeds '' were donated to the Philippine Red Cross
```
</details>

- **Output A:** `Diary of a Wimpy Kid`
- **Output B:** `The provided facts do not contain information about the song "Count On Me" by Bruno Mars. The document only mentions a "2016 Hyundai Genesis and Mars ' song" featured in *Diary of a Wimpy Kid*.`

**Transition Status:** `Persistent-Error`

**Human Auditor Coding:**
- Output A Error Mode: `[                      ]`
- Output B Error Mode: `[                      ]`
- Secondary Tags: `[                      ]`

---

