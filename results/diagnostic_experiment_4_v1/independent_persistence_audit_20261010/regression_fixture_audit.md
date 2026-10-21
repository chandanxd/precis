# Evidence-Level Regression Safeguards Audit

**Experiment 4.5.3 Independent Audit**  
**Date**: 2026-10-10  
**Status**: VERIFIED (Pass on All Three Historical Failure Modes)

---

## 1. Case `3f5983b2`: Namibian Minister of Youth / Erastus Utoni

- **Query**: `"who is the minister of youth in namibia"`
- **Gold Answer**: Erastus Utoni
- **Historical Failure Mode**:
  SVOA extraction extracted `Agnes Tjongarero` (the deputy) and lost or misattributed `Erastus Utoni` due to copular ambiguity in complex ministry rosters.

### Source Evidence
```html
<p>Cabinet of Namibia</p>
<ul>
  <li>Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni
    <ul>
      <li>Deputy : Agnes Tjongarero</li>
    </ul>
  </li>
</ul>
```

### Extracted & Persisted Structural Record
- **ID**: `case_3f5983b2_html_struct_list_1_a5b991ef140c`
- **Structure Type**: `list`
- **Content**:
  ```markdown
  ### Structured List:
  * Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni
  * [Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni] Deputy : Agnes Tjongarero
  ```
- **Searchable Text**: Preserves full entity names, ministry title, and parent prefixes.

### Query-Time Assembled Context
```
### Structured List:
* Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni
* [Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni] Deputy : Agnes Tjongarero
```

### Audit Assessment
- **Evidence Presence**: Both Erastus Utoni and Agnes Tjongarero are present.
- **Role Hierarchy**: The subordinate prefix `[Minister of Sport ...]` explicitly links the Deputy role to the parent item, preventing the model from conflating the deputy with the minister.
- **Verdict**: Failure mode is **prevented at the context evidence level**.

---

## 2. Case `ef634417`: Scorpions Song & Performer Attribution

- **Query**: `"who sings the song rock you like a hurricane"`
- **Gold Answer**: Scorpions
- **Historical Failure Mode**:
  A standalone list of songwriters (`Rudolf Schenker`, `Klaus Meine`, `Herman Rarebell`) overwhelmed the prompt context, causing the LLM to hallucinate a songwriter as the singer instead of the band `Scorpions`.

### Source Evidence
```html
<table>
  <tr><th>Rock You Like a Hurricane</th><th>Col_2</th></tr>
  <tr><td>Single by Scorpions</td><td></td></tr>
  <tr><td>Songwriter ( s )</td><td>Rudolf Schenker Klaus Meine Herman Rarebell</td></tr>
</table>
<ul>
  <li>Rudolf Schenker</li>
  <li>Klaus Meine</li>
  <li>Herman Rarebell</li>
</ul>
```

### Ingestion & Query Execution
- **Deduplication**: In `extract_structural_evidence_from_document()`, the standalone list matched > 80% of the table cells and was suppressed.
- **Assembled Context**:
  ```markdown
  | Rock You Like a Hurricane | Col_2 |
  | --- | --- |
  | Single by Scorpions |  |
  | Songwriter ( s ) | Rudolf Schenker Klaus Meine Herman Rarebell |
  ```
- **Distractor Elimination**: The standalone `### Structured List:` block was completely excluded from the assembled prompt.

### Audit Assessment
- **Evidence Presence**: `Single by Scorpions` is preserved prominently.
- **Distractor Suppression**: Verified that redundant songwriter list blocks are absent from context.
- **Verdict**: Failure mode is **prevented at the context evidence level**.

---

## 3. Case `8f1f9bd9`: Thomas Definition Surface-Form Mismatch

- **Query**: `"what is the definition of the name thomas"`
- **Gold Answer**: twin
- **Historical Failure Mode**:
  SVOA fact extraction was unable to establish a relational triple for the lexical definition `twin` from the Aramaic name table.

### Source Evidence
```html
<table>
  <tr><th>Thomas</th><th>Col_2</th></tr>
  <tr><td>Word / name</td><td>Aramaic</td></tr>
  <tr><td>Meaning</td><td>twin</td></tr>
</table>
```

### Extracted & Persisted Record
- **ID**: `case_8f1f9bd9_html_struct_tbl_1_0_6a3e2189d20c`
- **Structure Type**: `table`
- **Content**:
  ```markdown
  | Thomas | Col_2 |
  | --- | --- |
  | Word / name | Aramaic |
  | Meaning | twin |
  ```

### Query-Time Assembled Context
- Exact GFM table preserved and packed into Stage 4 context.
- Both `"twin"` and `"Aramaic"` are explicitly present.

### Audit Assessment
- **Evidence Presence**: Complete table preserved with exact key-value mapping `Meaning -> twin`.
- **Verdict**: Failure mode is **prevented at the context evidence level**.
