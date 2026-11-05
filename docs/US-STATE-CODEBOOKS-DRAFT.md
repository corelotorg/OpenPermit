# US state residential code books: adoption by state (DRAFT, verified 2026-10-03)

> Research reference only. Not legal advice. Confirm with the adopting agency. No code text is reproduced: only titles, editions, dates, section numbers and links.

Status: **DRAFT** research layer. Facts were checked against official pages fetched on 2026-10-03 and are not re-verified since; adoptions change, so confirm with the adopting agency. To finish: re-verify the category D states and the fields still marked UNVERIFIED (listed below), and refresh dates that have since passed.

## Summary

52 jurisdictions: 50 states, DC and Puerto Rico. Map categories:

- **A**: Statewide code; free state-published code book or amendment document: **24** (AL, CT, DC, GA, HI, ID, IN, KY, LA, ME, MD, MA, NJ, NM, OH, OK, OR, PA, RI, SC, UT, VA, WA, WI)
- **B**: Statewide code; state points to ICC Digital Codes / no-cost viewing (no free state download found): **4** (AR, CA, MN, NY)
- **C**: Local option / home rule (no mandatory statewide residential code): **16** (AK, AZ, CO, DE, IL, IA, KS, MS, MO, NE, NV, ND, SD, TX, VT, WV)
- **D**: Unverified (scope or book availability not confirmed): **8** (FL, MI, MT, NH, NC, PR, TN, WY)

How to read the categories:
- **Texas** is C. State law sets the IRC as the minimum municipal residential code (Tex. Loc. Gov't Code 214.212), but there is no state code agency or state book. Cities adopt and enforce.
- **Iowa, North Dakota, Nebraska, West Virginia and Mississippi** are C. Each has a state code, but it applies only where localities adopt it, or localities may opt out.
- **Tennessee** is statewide with local opt-out.
- **Category D** means a statewide adoption was confirmed but a free state book was not checked: Florida, Michigan, Montana, New Hampshire, North Carolina and Tennessee. Wyoming and Puerto Rico are D because their residential scope itself was not confirmed.

Notable findings (each is from a fetched official page; see `source_urls`):
- **Recent changes** (dates as recorded on 2026-10-03; the Montana, Oklahoma and Oregon dates have since passed):
  - Montana: 2024 IRC took effect Sept 26, 2026.
  - Oklahoma: 2024 IRC permanent rule took effect Sept 14, 2026.
  - Oregon: 2026 ORSC took effect Oct 1, 2026, with a six-month phase-in.
  - New Hampshire: 2024 IRC effective July 1, 2026, with concurrency through Dec 31, 2026.
  - Georgia: 2024 IRC amendments effective Jan 1, 2026.
  - Pennsylvania: 2021 IRC regulations effective Jan 1, 2026.
  - California: 2025 CRC effective Jan 1, 2026.
  - New York: 2025 RCNYS effective Dec 31, 2025.
  - Iowa: 2024 IRC effective Sept 10, 2025.
  - Upcoming: Washington (2024 codes) and South Carolina and Louisiana (next editions) are recorded as taking effect May 3, 2027, Jan 1, 2027 and Jan 1, 2027 respectively.
- **Michigan:** a July 7, 2025 court order kept the 2015-based residential rules in effect.
- **North Carolina:** the 2018 NC codes remain current while the 2024 code is delayed.
- **Kentucky:** the current code is the 2018 Kentucky Residential Code, still based on the 2015 IRC.
- **Full or near-full free state books:**
  - Ohio: Residential Code of Ohio rules, a 19.9 MB PDF.
  - Kentucky: 2018 KRC.
  - Wisconsin: Uniform Dwelling Code, a state-written code.
  - Hawaii, Connecticut, Massachusetts, West Virginia, Louisiana, New Mexico and Virginia: amendment documents.
- **States telling readers to use ICC's free viewer:** New York (DOS), Indiana (DHS) and Minnesota (DLI). California says the code can be read free through several channels, including depository libraries.
- **Copyright notices seen are mixed** (re-checked 2026-10-10; see `copyright_notice_seen`). ORI records what notice was seen and where; it makes no determination of copyright status.
  - Maryland's COMAR site states that the State of Maryland holds copyright in its version of the code text under CC BY-NC-SA 4.0, with a CC0 dedication 180 days after publication.
  - Georgia, Hawaii, Oklahoma, Pennsylvania and Rhode Island publications carry ICC copyright notices or references, for the incorporated model code or for referenced ICC material.
  - The NJ code PDF carries a copyright line from the NJ Office of Administrative Law.
  - Most other state pages show only a general copyright line in the site footer.

## Method

1. **Collection.** Official state agency, legislature and administrative-code pages were fetched with plain HTTP GET. Pages that returned 403 or rendered only through JavaScript (NY, NH, MI, FL, TN, MT, VT) were read with a web-fetch tool. Utah's server sends an incomplete TLS chain, so its statute PDF was fetched with certificate checks off. Fetched pages, hashes and the matched evidence are kept by the maintainer outside this repository; only the source URLs are published here.
2. **Evidence check.** Every fact carries a (URL, exact quote) pair. A build step looks for the quote in the fetched text and marks any field without a match `[UNVERIFIED]`. Fields with no evidence pair are also marked UNVERIFIED. The `evidence_checked` column counts the pairs that matched.
3. **ICC Digital Codes.** State page URLs (`https://codes.iccsafe.org/codes/united-states/<state>`) come from ICC's public US index page. **The state pages were not scraped**, under ORI's link-only policy for ICC pages. "Free read-only" is filled in only where the state's own page says the code can be viewed free. Everything else is "UNVERIFIED (ICC pages not scraped; link only)". ICC lists no territory pages, so PR has none.
4. **Copyright notice seen.** The `copyright_notice_seen` field records only what copyright notice was seen on the state sources listed for each row, and where. It was re-checked on 2026-10-10 by fetching each row's agency, code-book, citation and source URLs. Values:
   - `ICC notice on state publication`: the state's code or rule document carries an ICC copyright notice or reference (5 rows).
   - `notice on code publication`: the code publication itself carries a state copyright notice (2 rows).
   - `notice on web page footer`: only a general copyright line in the site footer was seen (22 rows).
   - `no notice seen`: every listed source was read and none showed a notice (15 rows).
   - `UNVERIFIED`: a listed source could not be read on 2026-10-10 (HTTP 403 or JavaScript-only rendering) or no official page is known (8 rows: AR, MA, MN, NH, NY, OH, PR, SD).
   `copyright_notice` is ORI's short description of the notice, not a quotation. **ORI makes no determination of copyright status.** State works are not assumed to be public domain, and a footer line is not treated as a statement about the code text.
5. **No code books in this repository.** State code documents are linked by URL only. No state or model code text, PDF or extract is committed.

Files: [`research/data/us-state-codebooks-DRAFT.csv`](../research/data/us-state-codebooks-DRAFT.csv) and [`.json`](../research/data/us-state-codebooks-DRAFT.json) (one row per state, 24 columns), and [`research/maps/us-state-codebooks-DRAFT.html`](../research/maps/us-state-codebooks-DRAFT.html), a self-contained offline map (click a state; no external requests).

Licences (see `LICENSE-SPEC.md`): the CSV and JSON data files are dedicated CC0 1.0; the map page is Apache-2.0, and the state records embedded in it are copied from the CSV and stay CC0 1.0; this document is CC BY-SA 4.0. The facts describe third-party adoptions and grant no right to any code text.

Map outlines: derived from the U.S. Census Bureau Cartographic Boundary File `cb_2024_us_state_500k.zip` (2024 vintage, 1:500,000; SHA-256 `3e81cbb6cf5f60d9b01ef3e730afa14d61ce5f784252a0b33a696135e71447bc`). That hash belongs to the copy the map was built from; it matched a fresh download from www2.census.gov on 2026-10-10, and the map's SVG paths match the output of the build script, which the maintainer keeps outside this repository. Each state was projected with an Albers equal-area conic projection: contiguous states with central meridian 96°W, origin latitude 37.5°N and standard parallels 29.5°N and 45.5°N; Alaska (clipped to 180°W-129°W, scaled 0.35), Hawaii and Puerto Rico as separately projected insets. Outlines were then simplified with topology-preserving Douglas-Peucker simplification (tolerance 0.0012 projected units) and written as SVG paths rounded to 0.1 px in a 960 px-wide view. The Census file's metadata asks for credit to the U.S. Census Bureau as the source and intends the file for small-scale display, not geographic analysis.

## Data

The per-state records are not repeated here. See [`research/data/us-state-codebooks-DRAFT.csv`](../research/data/us-state-codebooks-DRAFT.csv) or [`research/data/us-state-codebooks-DRAFT.json`](../research/data/us-state-codebooks-DRAFT.json): 52 rows (50 states, DC and Puerto Rico), 24 columns. The columns are `state`, `name`, `map_category`, `map_category_label`, `agency`, `agency_url`, `scope`, `scope_note`, `residential_code`, `residential_effective`, `building_code`, `state_book_url`, `state_book_desc`, `state_book_free`, `icc_state_page`, `icc_free_readonly`, `admin_citation`, `admin_url`, `copyright_notice`, `copyright_notice_source`, `copyright_notice_seen`, `date_verified`, `source_urls` and `evidence_checked`.

## Unverified items

- **Category D states:** FL, MI, MT, NH, NC, PR, TN, WY.
- **Count:** 177 of 1,248 cells (52 rows by 24 columns) contain UNVERIFIED. By field: `icc_free_readonly` 47, `building_code` 32, `admin_citation` 29, `residential_effective` 15, `state_book_free` 13, `residential_code` 12, `scope_note` 9, `copyright_notice` 8, `copyright_notice_seen` 8, `agency` 2, `scope` 2.
- **Free read-only status on ICC:** UNVERIFIED for every state except NY, IN, MN and CA, where the state's own page describes no-cost viewing.
- **Puerto Rico** has no official source page and no source URL; all of its substantive fields are UNVERIFIED.
- **Utah:** the statute version cited is marked superseded 7/1/2025 on the fetched PDF; its edition and effective date need re-checking against the current version.

## Attribution

ORI compiled these adoption facts from the public pages of the agencies below. Each agency is listed as a source only. No agency provided, reviewed or endorsed this research layer, and listing one implies no affiliation with ORI.

- Alabama: Alabama Home Builders Licensure Board (residential code adoption authority since Act 2024-443); Alabama Division of Construction Management (state-jurisdiction buildings). https://dcm.alabama.gov/bldg_code.aspx
- Alaska: Alaska Department of Public Safety, Division of Fire and Life Safety. https://dps.alaska.gov/fire/plan-review/
- Arizona: No statewide residential code agency (county/municipal adoption). https://www.azleg.gov/ars/11/00861.htm
- Arkansas: Arkansas State Fire Marshal (Arkansas Department of Public Safety / ADEM). https://dps.arkansas.gov/emergency-management/adem/state-fire-marshals-office/helpful-links/
- California: California Building Standards Commission (DGS). https://www.dgs.ca.gov/bsc/codes
- Colorado: Colorado Energy Office / Dept. of Local Affairs (no statewide residential code). https://energyoffice.colorado.gov/climate-energy/energy-policy/building-energy-codes
- Connecticut: Department of Administrative Services, Office of the State Building Inspector. https://portal.ct.gov/das
- Delaware: County governments (no statewide residential building code agency found). https://delcode.delaware.gov/title9/c025/
- District of Columbia: DC Department of Buildings (DOB) / Construction Codes Coordinating Board. https://dob.dc.gov/node/1615636
- Florida: Florida Building Commission (DBPR). https://www.floridabuilding.org/c/default.aspx
- Georgia: Georgia Department of Community Affairs (DCA). https://dca.georgia.gov/
- Hawaii: State Building Code Council (Dept. of Accounting and General Services). https://ags.hawaii.gov/
- Idaho: Idaho Division of Occupational and Professional Licenses (DOPL), Building Code Board. https://dopl.idaho.gov/
- Illinois: Capital Development Board (CDB). https://cdb.illinois.gov/business/codes.html
- Indiana: Indiana Fire Prevention and Building Safety Commission (Dept. of Homeland Security). https://www.in.gov/dhs/
- Iowa: Iowa Department of Inspections, Appeals, and Licensing - State Building Code Bureau. https://www.legis.iowa.gov/docs/iac/chapter/10-15-2025.661.301.pdf
- Kansas: No statewide residential code agency (local adoption). https://kslegislature.gov/b2023_24/laws/012_000_0000_chapter/012_033_0000_article/012_033_0001_section/012_033_0001_k/
- Kentucky: Kentucky Department of Housing, Buildings and Construction (DHBC). https://dhbc.ky.gov/
- Louisiana: Louisiana State Uniform Construction Code Council (LSUCCC). https://lsuccc.la/
- Maine: Maine Technical Building Codes and Standards Board (Dept. of Public Safety, Fire Marshal - MUBEC). https://www.maine.gov/dps/fmo/
- Maryland: Maryland Department of Labor - Building Codes Administration. https://labor.maryland.gov/labor/build/buildcodes.shtml
- Massachusetts: Board of Building Regulations and Standards (BBRS). https://www.mass.gov/
- Michigan: LARA Bureau of Construction Codes. https://www.michigan.gov/lara/bureau-list/bcc
- Minnesota: Minnesota Department of Labor and Industry (DLI). https://www.dli.mn.gov/
- Mississippi: Mississippi Building Codes Council (Mississippi Insurance Dept., State Fire Marshal). https://www.mid.ms.gov/sfmo/mississippi-uniform-building-codes/
- Missouri: No statewide residential code (local adoption; DNR lists local codes). https://dnr.mo.gov/energy/efficiency/codes-jurisdiction
- Montana: Montana Department of Labor & Industry, Building Codes Program. https://bsd.dli.mt.gov/building-codes-permits/current-codes
- Nebraska: Nebraska Legislature (state building code by statute); local adoption. https://nebraskalegislature.gov/laws/statutes.php?statute=71-6403
- Nevada: No statewide residential code (local adoption). https://www.leg.state.nv.us/nrs/NRS-278.html
- New Hampshire: NH State Building Code Review Board / State Fire Marshal. https://www.firemarshal.dos.nh.gov/laws-rules-regulatory/state-building-code
- New Jersey: NJ Department of Community Affairs, Division of Codes and Standards (Uniform Construction Code). https://www.nj.gov/dca/codes/codreg/current.shtml
- New Mexico: Regulation and Licensing Department, Construction Industries Division. https://www.rld.nm.gov/construction-industries/
- New York: NY Department of State, Division of Building Standards and Codes. https://dos.ny.gov/notice-adoption
- North Carolina: NC Office of State Fire Marshal / Building Code Council / Residential Code Council. https://www.ncosfm.gov/codes/codes-current-and-past
- North Dakota: ND Department of Commerce, Division of Community Services. https://www.commerce.nd.gov/community-services/building-codes
- Ohio: Ohio Board of Building Standards (Dept. of Commerce). https://codes.ohio.gov/ohio-administrative-code/4101:8
- Oklahoma: Oklahoma Uniform Building Code Commission (OUBCC). https://oklahoma.gov/oubcc/codes-and-rules.html
- Oregon: Oregon Building Codes Division (BCD). https://www.oregon.gov/bcd/codes-stand/Pages/residential-structures.aspx
- Pennsylvania: PA Department of Labor & Industry, Uniform Construction Code. https://www.pa.gov/agencies/dli/programs-services/labor-management-relations/bureau-of-occupational-and-industrial-safety/uniform-construction-code.html
- Puerto Rico: UNVERIFIED (no official page confirmed).
- Rhode Island: RI Building Code Standards Committee (State Building Code Office). https://rules.sos.ri.gov/Regulations/Part/510-00-00-2
- South Carolina: SC Building Codes Council (LLR). https://www.llr.sc.gov/bcc/
- South Dakota: No statewide residential code (municipal ordinances; SDCL ch. 11-10). https://sdlegislature.gov/Statutes/11-10
- Tennessee: Tennessee State Fire Marshal's Office (Dept. of Commerce & Insurance). https://www.tn.gov/commerce/fire/codes-enforcement/history.html
- Texas: No state code agency for residential; municipalities enforce (state statute sets minimum). https://guides.sll.texas.gov/texas-law/building-codes
- Utah: Utah Legislature (State Construction Code by statute). https://le.utah.gov/xcode/Title15A/Chapter2/C15A-2-S103_2024070120240501.pdf
- Vermont: Vermont Division of Fire Safety (no state residential building code listed); Dept. of Public Service (RBES energy standards). https://firesafety.vermont.gov/buildingcode/codes
- Virginia: Virginia DHCD / Board of Housing and Community Development. https://www.dhcd.virginia.gov/codes
- Washington: Washington State Building Code Council (SBCC). https://sbcc.wa.gov/
- West Virginia: West Virginia State Fire Commission / State Fire Marshal. https://firemarshal.wv.gov/
- Wisconsin: Wisconsin Department of Safety and Professional Services (DSPS). https://dsps.wi.gov/a-z-programs-list/udc/
- Wyoming: Wyoming State Fire Marshal (state-adopted codes; residential scope UNVERIFIED). https://wsfm.wyo.gov/

- **International Code Council (ICC):** publisher of the International Residential Code®, International Building Code® and related I-Codes, and host of ICC Digital Codes (https://codes.iccsafe.org/). State pages are linked, not reproduced. IRC, IBC and I-Codes are ICC marks, used here only to name the codes.
- **Map boundaries:** derived from the U.S. Census Bureau Cartographic Boundary File cb_2024_us_state_500k (public domain; source: U.S. Census Bureau).
- **Status lookups:** U.S. DOE Building Energy Codes Program state pages (energycodes.gov), used for "None Statewide" (AZ, KS, MO, CO).

ORI is not affiliated with, sponsored by or endorsed by ICC, any state agency or the U.S. Census Bureau.
