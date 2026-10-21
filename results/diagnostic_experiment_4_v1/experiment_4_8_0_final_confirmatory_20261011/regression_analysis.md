# Experiment 4.8.0: Candidate G Regression and Error Analysis

**Document**: `regression_analysis.md`  
**Evaluation Date**: October 11, 2026  
**Scope**: In-depth analysis of Candidate G recoveries, regressions, and discordant pairs against Conditions D, E, and F.  

---

## 1. Executive Summary of Regressions & Recoveries

Candidate G implemented **Guarded Structural-Priority Context Packing (Intervention 1)** to resolve the hybrid SVOA fact contamination identified in Experiment 4.6. In single-document table-bearing queries, when relevant structural evidence is successfully packed, same-document SVOA facts are strictly suppressed.

### Net Progression Summary:
- **Condition D (Table Only)**: 99 / 200 EM (49.5%), 122 / 200 Cont (61.0%)
- **Condition E (In-Memory Prototype)**: 108 / 200 EM (54.0%), 137 / 200 Cont (68.5%)
- **Condition F (Persistent Production)**: 105 / 200 EM (52.5%), 131 / 200 Cont (65.5%)
- **Candidate G (Guarded Structural-Priority)**: **110 / 200 EM (55.0%)**, **137 / 200 Cont (68.5%)**

---

## 2. Recovery of Experiment 4.6 Regressions (F Missed, D Won)

In Experiment 4.6, 13 cases were diagnosed where Condition D succeeded but Condition F failed due to hybrid SVOA contamination, relevance filtering, or formatting degradation.

Under Candidate G, **10 of the 13 regressions (76.9%) were successfully recovered**:

| Case ID | Question | Gold Answer | Cond D | Cond F (Contaminated) | Candidate G | Recovery Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `93078684` | *wolf of wall street number of f words* | `569` | `569` (EM) | `...contains 8.35 f-words.` (Miss) | `569` | **RECOVERED** |
| `f89cf8b1` | *who wrote the declaration of man and citizen* | `General Lafayette , ( sometimes with Thomas Jefferson ) and Honoré Mirabeau` | `General Lafayette...` (EM) | `General Lafayette` (Miss) | `General Lafayette, sometimes with Thomas Jefferson, and Honoré Mirabeau` | **RECOVERED** |
| `8b41e651` | *who is the supreme justice of the supreme court* | `John Roberts` | `John Roberts` (EM) | `John Jay` (Miss) | `John Roberts` | **RECOVERED** |
| `5868443c` | *who is the supreme justice of the supreme court* | `John Roberts` | `John Roberts` (EM) | `John Jay` (Miss) | `John Roberts` | **RECOVERED** |
| `b786366c` | *who has the most ncaa basketball tournament appearances* | `Kentucky` | `Kentucky` (EM) | `Based on facts, Kansas...` (Miss) | `Kentucky` | **RECOVERED** |
| `44408e37` | *what is the 3rd largest state in usa* | `California` | `California` (EM) | `Based on the data... California` (Miss) | `California` | **RECOVERED** |
| `d84f0eaa` | *when did lionel messi play his first game for barcelona* | `2001` | `2001` (EM) | `2004` (Miss) | `2001` | **RECOVERED** |
| `0541c730` | *when did last podcast on the left start* | `2011` | `2011` (EM) | `2011 -- present` (Miss) | `2011` | **RECOVERED** |
| `1e07903c` | *who is known as the philippine queen of bossa nova* | `Sitti Navarro` | `Sitti Navarro` (EM) | `Sitti Katrina Baiddin Navarro` (Miss) | `Sitti Navarro` | **RECOVERED** |
| `42d98889` | *which is the only test playing nation that india has never beat in t20* | `Scotland` | `Scotland` (EM) | `Ireland` (Miss) | `Scotland` | **RECOVERED** |

### Root-Cause Recovery Mechanism:
- In cases `93078684`, `8b41e651`, `5868443c`, `b786366c`, `44408e37`, and `d84f0eaa`, suppressing scrambled same-document SVOA triples eliminated distractor entities (e.g., John Jay, Swearnet 8.35, Kansas 31 appearances) and conversational framing phrases (`Based on the facts provided...`), allowing the language model to extract the exact correct cell directly from the Markdown table.

---

## 3. Unresolved Experiment 4.6 Cases (Deferred Interventions)

Three of the 13 diagnosed cases remained unrecovered because their root cause belonged to deferred interventions:

1. **Case `cf2d77b0` (*Gurbachan Singh Randhawa* - First Arjun Award in Athletics)**:
   - **Diagnosis**: Vector similarity was 0.2296 (< 0.25 threshold) due to generic headers (`S.No. | Year | Name`) and missing title context in the vector chunk.
   - **Intervention Needed**: Intervention 2 (Document Title Grounding in Searchable Text).
   - **Candidate G Behavior**: Safely fell back to standard SVOA facts; predicted *"Insufficient information"*.

2. **Case `ef634417` (*Scorpions* - Rock You Like a Hurricane)**:
   - **Diagnosis**: The song infobox table contains both the performers (*Scorpions*) and songwriters (*Rudolf Schenker, Klaus Meine, Herman Rarebell*).
   - **Candidate G Behavior**: Predicted songwriters `Rudolf Schenker, Klaus Meine, Herman Rarebell`.

3. **Case `e44f257a` (*Chapter Fourteen* - Riverdale Season 2 Premiere)**:
   - **Diagnosis**: The HTML table had omitted episode numbers in the season column and missing "Season 2" section header context.
   - **Intervention Needed**: Intervention 3 (Table Structure Preservation & Header Repair).
   - **Candidate G Behavior**: Predicted *"Insufficient information"*.

---

## 4. Analysis of Candidate G Losses Against Condition F (10 Cases)

Candidate G gained **15 wins** over Condition F while incurring **10 losses** (Net: **+5 wins**, $+2.5$ pp).

Forensic review of the 10 cases where Condition F succeeded but Candidate G missed reveals two distinct mechanisms:

### Category 1: Evaluation Surface Variations (Containment Intact) ($N=2$)
In these cases, Candidate G extracted complete, accurate answers that passed containment, but differed from the exact short-string gold convention:
- **Case `4a55dbb5`**: *"who wrote the declaration of man and citizen"*
  - Gold: `General Lafayette`
  - F: `General Lafayette` (EM)
  - G: `General Lafayette, sometimes with Thomas Jefferson, and Honoré Mirabeau` (EM=False, Containment=True). G extracted the full bibliographic credit from the infobox.
- **Case `8f1f9bd9`**: *"what is the definition of the name thomas"*
  - Gold: `twin`
  - F: `twin` (EM)
  - G: `Aramaic: twin` (EM=False, Containment=True). Extracted the etymological label from the infobox table cell.

### Category 2: Disambiguation Through Corroborating Prose Triples ($N=8$)
In 8 cases, removing prose triples forced the model to rely solely on the structural table/list block. When that block contained multiple candidate entities (such as nominees, family members, or recurring cast), the model occasionally selected an alternative row:
- **Case `680012c3` & `a0ee91b8`**: *"who is the father of lucius in gladiator"*
  - Gold: `Lucius Verus`
  - F Context: Table + 28 SVOA facts including explicit parentage triples. F answered `Lucius Verus`.
  - G Context: Character list where Lucilla is Lucius's mother and Lucius Verus is his father. G predicted `Lucilla`.
- **Case `122e005c`**: *"who won the oscar for best actor in 1975"*
  - Gold: `Art Carney`
  - Table contains both winner (*Art Carney*) and nominees (*Dustin Hoffman*, *Al Pacino*, *Albert Finney*, *Jack Nicholson*). F used SVOA triples to isolate the winner; G selected `Dustin Hoffman`.
- **Case `b2c8d85e`**: *"when is the 5th round fa cup played"*
  - Gold: `16 February 2018`
  - Table contains Round 4 (`29 January 2018`) and Round 5 (`16 February 2018`). G selected `29 January 2018`.
- **Case `14164faf` & `9c756e62`**: *"who played the mad hatter in the batman tv show"*
  - Gold: `David Wayne`
  - Table lists recurring villains. G selected `Roddy McDowall` (Bookworm).
- **Case `5cccbf86`**: *"who has played in the most premier league derbies"*
  - Gold: `Neville Southall`
  - G extracted the club `Liverpool` rather than the individual player.
- **Case `fd55f4dc`**: *"who represents the arizona 9th district in the house"*
  - Gold: `Kyrsten Sinema`
  - G predicted `Insufficient information` due to congressional district table cell formatting.

---

## 5. Summary of Net Gains

Despite the 8 row-disambiguation losses, Candidate G achieved **15 decisive wins over Condition F** by completely eliminating SVOA distractor injection and conversational preambles. This shifted overall performance from **52.5% to 55.0% EM** (reaching prototype parity with Condition E's 54.0% EM and 68.5% Containment) while slashing context token consumption by **53.2%**.
