# IMD Weather Event Context (Example Domain Signal)

**Purpose:** This file is background context only — to understand what real-world signal an SOP like "active low-pressure/cyclonic system → treat all outdoor activity as high severity" is reacting to. Nothing here should be hardcoded into the bot; it is example-only context for the assignment brief, not live data the app should special-case.

## 1. Low-pressure system over northeast Madhya Pradesh (early September 2026)

Per IMD (India Meteorological Department) bulletins found via search:
- A **Well Marked Low-Pressure Area** was situated over northeast Madhya Pradesh and its neighbourhood in early September 2026.
- Under its influence, **isolated heavy to very heavy rainfall** was forecast over Madhya Pradesh during **September 3–5, 2026**, with **isolated extremely heavy rainfall** additionally likely over East Madhya Pradesh specifically on **September 3, 2026**.
- A separate associated/adjacent system was noted over the **North Bay of Bengal off the West Bengal–Bangladesh coasts**.
- Wider rain impact was expected to extend to **Chhattisgarh, Bihar, Jharkhand**, and parts of **Jammu and Kashmir, Ladakh, and Himachal Pradesh**, with rain beginning around September 2.

Source: [IMD Rainfall Information](https://mausam.imd.gov.in/responsive/rainfallinformation.php), [IMD Cyclone Information](https://mausam.imd.gov.in/responsive/cycloneinformation.php), [IMD New Delhi forecast bulletin, 4 Sept 2026](https://mausam.imd.gov.in/newdelhi/mcdata/delhi_forecast.pdf), [IMD Monsoon Information](https://mausam.imd.gov.in/responsive/monsooninformation.php)

## 2. Squally winds off south Tamil Nadu coast

Per IMD fishermen-warning bulletins found via search:
- **Squally wind conditions of 45–55 km/h gusting to 65 km/h** were forecast to prevail **along and off the South Tamil Nadu coast**, over parts of the **southwest Bay of Bengal adjoining the south Sri Lanka coast**, and parts of the **Comorin area**.
- IMD's standard advisory in these bulletins: **fishermen are advised not to venture into the affected sea areas** during the warning period.
- This class of warning (squally wind fishermen advisories) is issued routinely by IMD's regional centers (e.g., Chennai, Thiruvananthapuram) whenever wind speeds in coastal/offshore waters cross defined thresholds — it is a recurring bulletin type, not a one-off event.

Source: [IMD Chennai Fishermen Warning](https://mausam.imd.gov.in/chennai/mcdata/fishermen.pdf), [RSMC New Delhi Fishermen Warning, 24 Jul 2026](https://rsmcnewdelhi.imd.gov.in/uploads/archive/45/45_521cc8_FW240600.pdf), [IMD Thiruvananthapuram wind warning](https://mausam.imd.gov.in/thiruvananthapuram/mcdata/dwr1.pdf), [IMD internal bulletin, 2 Sept 2026](https://internal.imd.gov.in/section/nhac/dynamic/allindianew.pdf)

## 3. Why this matters for SOP design (framing only)

Both examples illustrate a category of signal that is **qualitative/systemic** rather than a single numeric threshold on one field: "there is an active named weather system (low-pressure area / cyclonic circulation) affecting this region" is a different kind of fact than "wind speed > 40 km/h." IMD communicates this as a *named system with a defined area of influence and validity window*, not just a point-forecast number.

This is relevant background for why the brief calls for at least one **fuzzy/non-numeric SOP**: a rule like "if there's an active severe-weather system affecting the area, treat all outdoor activity as high severity regardless of the specific numbers" cannot be expressed as a single `if x > y` check against one Open-Meteo field — it requires either (a) a qualitative judgment call by the LLM based on the pattern of returned values (e.g., sustained high wind + high precipitation probability + certain weather codes together), or (b) a genuinely separate signal (IMD-style systemic advisory) that Open-Meteo's per-point forecast API does not directly expose as a single field. Open-Meteo does expose `weather_code` (WMO codes, which include categories like thunderstorm) and `cape` (convective energy, a storm-risk proxy) that could serve as partial numeric proxies, but neither is literally "is there a named low-pressure system," reinforcing that this class of SOP is inherently judgment-based rather than threshold-based.

Note again: this file exists purely so the person building the bot understands the *kind* of real-world event the brief is alluding to — no specific date, region, or number from this file should be hardcoded into the running application.
