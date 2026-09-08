# FarmTact — research register and evidence interpretation

Research cut-off: 2026-09-08. This is a targeted literature and source review, not a systematic review or a claim to have read every paper. Full-text availability and the portions reviewed are explicitly recorded. No numerical commercial production recipe is approved by this handoff.

## Development use policy — version 1.2

Section 0 of `FarmTact_Build_Specification.md` governs this phase. Coding agents perform source, taxonomy, licence, units and applicability review, with independent agent checks for critical extractions. No human approval, manual research sign-off or farmer-supplied recipe is required to build and test the system.

Accept supported evidence and mappings through recorded technical checks. Quarantine ambiguous aliases, missing context and unverifiable numerical claims, then continue with unaffected records. Unknown or incompatible licences block the affected reuse; they do not require development to stop. Never convert uncertainty into a validated fact to clear a gate.

Create explicitly synthetic, internally consistent crop recipes where real farm parameters are missing. Mark their parameters and derived models `demo_only`, preserve their fixture provenance and keep them outside scientific evidence claims. Automatic acceptance permits simulation only; it does not approve a commercial production recipe. The default demonstration uses complete fixtures and recorded policy decisions so it runs without human input.

The publication access statuses below describe the original research handoff and are not new verification performed for this rewrite. Referenced machine-readable registries are development deliverables absent from the current checkout; construct them from these records and retain every access limitation.

## Selection and research protocol

The ten-crop portfolio is anchored to NParks cultivation guidance and checked against SFA examples and a local farm catalogue [C01–C04]. It is not a verified national sales or tonnage ranking. Search synonyms and scientific names, prioritize Singapore experiments, then comparable tropical/protected systems, then other environments. Exclude microgreens, seedlings, tubers, forage, medicinal extraction and unrelated species when the endpoint is mature saleable leaves. Keep them only as explicitly scoped background.

For each candidate: verify DOI and version; distinguish original study/review/extension; inspect methods, units, experimental unit, controls and replication; check corrections/retractions; locate lawful data supplements; record gaps. A full text being accessible is not the same as every table having been numerically extracted. Access-blocked papers remain useful bibliography entries but cannot silently authorize a growth parameter.

## Reviewed publication records

### P01 — Light-Time-Biomass Response Model for Predicting the Growth of Choy Sum (Brassica rapa var. parachinensis) in Soil-Based LED-Constructed Indoor Plant Factory for Efficient Seedling Production

Year: 2021. DOI: `10.3389/fpls.2021.623682`. Scope: Singapore-affiliated study; experiment details require extraction; soil-based indoor LED.

Read status: **publisher full text accessed; model scope reviewed**.

Research note: Models light, time and seedling biomass.

FarmTact design implication: Use for a nursery-stage growth-model candidate.

Limit: Seedling biomass is not mature marketable yield; extract stage and fresh/dry-weight definitions before parameterization.

Source: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2021.623682/full

### P02 — Widely-targeted metabolomics and transcriptomics identify metabolites associated with flowering regulation of Choy Sum

Year: 2024. DOI: `10.1038/s41598-024-60801-4`. Scope: China; verify precise experimental site; experimental flowering study.

Read status: **publisher full text accessed; abstract and scope reviewed**.

Research note: Investigates flowering-related physiology and molecular signals.

FarmTact design implication: Motivates a flowering-stage/quality field, not an operational prediction coefficient.

Limit: Omics associations are not a validated days-to-harvest model.

Source: https://www.nature.com/articles/s41598-024-60801-4

### P03 — Optimal Plant Density, Nutrient Concentration and Rootzone Temperature for Higher Growth and Yield of Brassica rapa L. Curly Dwarf Pak Choy in Raft Hydroponic System Under Tropical Climate

Year: 2020. DOI: `not verified`. Scope: Sabah, Malaysia; raft hydroponics.

Read status: **publisher abstract reviewed**.

Research note: Tests density, solution conductivity and root-zone temperature jointly.

FarmTact design implication: Require cultivar and system-specific density/temperature interaction fields.

Limit: Reported best treatment is not a universal recipe; DOI not established in this review.

Source: https://tost.unise.org/pdfs/vol7/no3-2/7x3-2x178-188xOA.html

### P04 — Extended photoperiod improves growth and nutritional quality of pak choi under constant daily light integral

Year: 2025. DOI: `10.3389/fpls.2025.1621513`. Scope: Netherlands; SFA co-author and funding; controlled-environment hydroponics.

Read status: **publisher methods, results and data-availability statement reviewed**.

Research note: Three cultivars were compared across photoperiod/light-intensity treatments; final harvest was 32 days after sowing in that experiment.

FarmTact design implication: Separate PPFD, photoperiod, DLI, cultivar and energy cost in candidate recipes.

Limit: Constant DLI does not imply identical growth. The linked Zenodo deposit is described as LC-MS data, not necessarily a complete yield time series.

Source: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1621513/full

### P05 — Microclimate control to increase productivity and nutritional quality of leafy vegetables in a cost-effective manner

Year: 2022. DOI: `10.25165/j.ijabe.20221503.7367`. Scope: Singapore; aeroponics and tropical greenhouse.

Read status: **publisher abstract and references reviewed**.

Research note: Discusses root-zone management and supplementary lighting in tropical production.

FarmTact design implication: Represent protected systems, root-zone conditions and energy/water trade-offs.

Limit: Research overview; do not count cited experiments again as independent observations.

Source: https://ijabe.org/index.php/ijabe/article/view/7367

### P06 — Nitrate accumulation, productivity and photosynthesis of Brassica alboglabra grown under low light with supplemental LED lighting in the tropical greenhouse

Year: 2019. DOI: `10.1080/01904167.2019.1643367`. Scope: Singapore; tropical greenhouse with supplementary LEDs.

Read status: **publisher abstract/indexed institutional record reviewed; repository download blocked**.

Research note: Examines light, productivity and nitrate accumulation.

FarmTact design implication: Track marketable quality as well as biomass for kailan.

Limit: No universal nitrogen, nitrate-limit or LED prescription is inferred.

Source: https://www.tandfonline.com/doi/full/10.1080/01904167.2019.1643367

### P07 — Reduced nitrogen availability in hydroponically grown Chinese broccoli does not affect photosynthetic performance and yield while enhancing nitrogen use efficiency and nutritional quality

Year: 2026. DOI: `10.3389/fpls.2025.1745794`. Scope: Singapore-affiliated; precise site to extract; hydroponics.

Read status: **publisher full text accessed; abstract reviewed**.

Research note: Studies reduced nitrogen within a defined experimental treatment range.

FarmTact design implication: Candidate nutrient-efficiency evidence; retain baseline and treatment context.

Limit: The publication year is 2026 despite a 2025 DOI suffix; not permission for autonomous fertilizer changes.

Source: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1745794/full

### P08 — Controlling root zone temperature improves plant growth and pigments in hydroponic lettuce

Year: 2023. DOI: `10.1093/aob/mcad127`. Scope: Japan; hydroponics.

Read status: **publisher article accessed; abstract and study design reviewed**.

Research note: Root-zone temperature affects biomass and pigments under tested conditions.

FarmTact design implication: Separate root temperature from air temperature in yield features.

Limit: Treatment performance must remain conditional on cultivar, ambient conditions and experimental scale.

Source: https://academic.oup.com/aob/article/132/3/455/7265388

### P09 — Raising root zone temperature improves plant productivity and metabolites in hydroponic lettuce production

Year: 2024. DOI: `10.3389/fpls.2024.1352331`. Scope: Japan; hydroponics.

Read status: **publisher abstract reviewed**.

Research note: Root warming can help in its tested environmental context.

FarmTact design implication: Add a contradiction/context check when retrieving root-cooling literature.

Limit: Cooling and warming studies are not contradictory when baseline conditions differ; no one fixed optimum.

Source: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2024.1352331/full

### P10 — A short-term cooling of root-zone temperature increases bioactive compounds in baby leaf Amaranthus tricolor L.

Year: 2022. DOI: `10.3389/fpls.2022.944716`. Scope: Chiba, Japan; indoor hydroponic baby leaf.

Read status: **publisher methods and discussion reviewed**.

Research note: Examines short cooling treatments and quality/growth trade-offs.

FarmTact design implication: Keep baby-leaf stage and quality target distinct from full-size bayam.

Limit: One experiment, non-Singapore conditions; do not optimize biomass with a quality-stress coefficient.

Source: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2022.944716/full

### P11 — Changes in Growth and Anthocyanin Content of Brassica juncea L. affected by Light Intensity and Photoperiod in Plant Factory with Artificial Lighting

Year: 2022. DOI: `10.7235/HORT.20220053`. Scope: Korea; indoor plant factory.

Read status: **publisher XML accessed; abstract and methods sections reviewed**.

Research note: Red mustard responds to lighting conditions in growth and pigmentation.

FarmTact design implication: Use cultivar-specific light/quality features.

Limit: Red mustard results cannot automatically be assigned to all Chinese mustard cultivars.

Source: https://www.hst-j.org/articles/xml/LDxK/

### P12 — Effect of Light Quality on Physiological Disorder, Growth, and Secondary Metabolite Content of Water Spinach (Ipomoea aquatica Forsk) Cultivated in a Closed-type Plant Production System

Year: 2019. DOI: `10.12972/kjhst.20190020`. Scope: Japan; closed hydroponic production.

Read status: **publisher XML methods and results reviewed**.

Research note: Light spectrum affects biomass allocation and intumescence injury.

FarmTact design implication: Include marketable defect/packout endpoints, not just total biomass.

Limit: Full-text page states a non-commercial Creative Commons licence; do not assume commercial corpus redistribution rights.

Source: https://www.hst-j.org/articles/xml/Mz2A/

### P13 — Growth and photosynthetic characteristics of sweet potato (Ipomoea batatas) leaves grown under natural sunlight with supplemental LED lighting in a tropical greenhouse

Year: 2020. DOI: `10.1016/j.jplph.2020.153239`. Scope: Singapore; tropical greenhouse.

Read status: **PubMed/publisher abstract reviewed; institutional full-text download blocked**.

Research note: Studies sweet-potato leaves rather than simply tuber production.

FarmTact design implication: Build a leaf/shoot product model separate from tuber recipes.

Limit: Leaf biomass and regrowth scheduling require leaf-specific data.

Source: https://pubmed.ncbi.nlm.nih.gov/32763651/

### P14 — Plant Growth and Nutritional Quality Attributes of Basella alba Applied with Variable Rates of Nitrogen Fertilizer at Different Planting Dates under Canadian Maritime Climatic Conditions

Year: 2021. DOI: `10.1155/2021/5577696`. Scope: Nova Scotia, Canada; outdoor field.

Read status: **original article PDF examined via repository mirror; first page visually checked**.

Research note: Examines planting time and nitrogen under a maritime climate.

FarmTact design implication: Capture season, trial location, plant part and fertilizer context for Basella.

Limit: Do not transfer Canadian planting dates or rates directly to Singapore; assess study quality before numeric extraction.

Source: https://onlinelibrary.wiley.com/doi/10.1155/2021/5577696

### P15 — Effects of Temperature, Relative Humidity, and Carbon Dioxide Concentration on Growth and Glucosinolate Content of Kale Grown in a Plant Factory

Year: 2021. DOI: `10.3390/foods10071524`. Scope: Korea; plant factory.

Read status: **publisher/PMC abstract indexed; full-text access blocked during review**.

Research note: Evaluates environment and kale growth/quality responses.

FarmTact design implication: Prioritize environment-by-cultivar feature collection.

Limit: Precise taxon/cultivar must be confirmed from full methods before activating numeric priors; do not conflate Chinese kale and curly kale.

Source: https://www.mdpi.com/2304-8158/10/7/1524

### P16 — Using Machine Learning Models to Predict Hydroponically Grown Lettuce Yield

Year: 2022. DOI: `10.3389/fpls.2022.706042`. Scope: Egypt; greenhouse hydroponic/aeroponic systems.

Read status: **publisher methods and model inputs reviewed**.

Research note: Compares several ML methods using plant measurements recorded at harvest.

FarmTact design implication: Use as a model-candidate reference and a forecast-leakage test case.

Limit: Harvest-time dry weight and other contemporaneous measurements cannot be used in an earlier planting-date forecast.

Source: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2022.706042/full

### P17 — Lettuce Production in Intelligent Greenhouses—3D Imaging and Computer Vision for Plant Spacing Decisions

Year: 2023. DOI: `10.3390/s23062929`. Scope: Bleiswijk, Netherlands; greenhouse.

Read status: **university publication record and abstract reviewed**.

Research note: Links crop imaging to spacing decisions; companion experimental data exists.

FarmTact design implication: Optional image-derived canopy/spacing features after baseline models work.

Limit: External greenhouse data is not a representative Singapore farm-demand dataset.

Source: https://research.wur.nl/en/publications/lettuce-production-in-intelligent-greenhouses3d-imaging-and-compu/

### P18 — Effect of harvesting interval and defoliation on yield and chemical composition of leaves, stems and tubers of sweet potato (Ipomoea batatas L. (Lam.)) plant parts

Year: 2003. DOI: `10.1016/S0378-4290(03)00018-2`. Scope: Vietnam; field; multiple harvest regimes.

Read status: **publisher abstract/indexed record reviewed**.

Research note: Distinguishes leaf, stem and tuber responses to harvesting.

FarmTact design implication: Motivates multi-cut regrowth and plant-part accounting.

Limit: Feed/biomass objectives and dry-matter results are not fresh-market saleable leaf yield.

Source: https://www.sciencedirect.com/science/article/abs/pii/S0378429003000182

### P19 — Limitations to photosynthesis of lettuce grown under tropical conditions: alleviation by root-zone cooling

Year: 2001. DOI: `10.1093/jexbot/52.359.1323`. Scope: Singapore; tropical cultivation with root-zone treatments.

Read status: **publisher abstract reviewed**.

Research note: Contrasts cooled roots with fluctuating warm root-zone conditions.

FarmTact design implication: Provide locally relevant physiological context for protected lettuce.

Limit: Older physiological experiment; not an energy-price or commercial yield forecast.

Source: https://academic.oup.com/jxb/article-abstract/52/359/1323/510957

### P20 — Enhancing Productivity and Improving Nutritional Quality of Subtropical and Temperate Leafy Vegetables in Tropical Greenhouses and Indoor Farming Systems

Year: 2024. DOI: `10.3390/horticulturae10030306`. Scope: Singapore-focused research synthesis; protected/indoor systems.

Read status: **publisher indexed abstract reviewed; full-text request blocked**.

Research note: Synthesizes tropical controlled-environment research.

FarmTact design implication: Seed backward/forward citation discovery and contextual comparisons.

Limit: A review is not another independent experimental dataset.

Source: https://www.mdpi.com/2311-7524/10/3/306

## Research gaps that must remain visible

Crop-specific local demand, harvest costs, buyer packout, shelf life, multi-cut regrowth, cultivar-specific energy requirements and commercial per-cycle yields are not supplied by these papers. Bayam, Malabar spinach, mustard and kangkong have less directly transferable commercial Singapore evidence in this reviewed set than lettuce/pak choi. Kale taxonomy and cultivar must be confirmed in P15 before parameter use. Literature-derived uncertainty should not be given falsely precise probabilities.

The SFA-associated pak choi study P04 explicitly describes its Zenodo data as LC-MS data. It is a scientific-quality supplement, not automatically a ready-made crop-yield dataset. WUR D20 is a stronger candidate for climate/image modeling, but its experimental domain is the Netherlands. File licences and actual downloadable schemas must be checked by the ingest agent.

## Source register

**[C01] NParks: Know 10 Leafy Vegetables** — government_extension. https://isomer-user-content.by.gov.sg/316/b7cac2ae-6e25-41b0-a284-0b6028080584/know%2010%20leafy%20vegetables.pdf

**[C02] NParks: Growing Five Leafy Vegetables** — government_extension. https://www.nparks.gov.sg/publications-resources/articles/growing-five-leafy-vegetables

**[C03] SFA: Tasty treats from local farms** — government_local_produce. https://www.sfa.gov.sg/fromSGtoSG/tasty-treats-from-local-farms

**[C04] Kok Fah Technology Farm product catalogue** — farm_primary_catalogue. https://kokfahfarm.com.sg/

**[P01] Light-Time-Biomass Response Model for Predicting the Growth of Choy Sum (Brassica rapa var. parachinensis) in Soil-Based LED-Constructed Indoor Plant Factory for Efficient Seedling Production** — journal_research. https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2021.623682/full

**[P02] Widely-targeted metabolomics and transcriptomics identify metabolites associated with flowering regulation of Choy Sum** — journal_research. https://www.nature.com/articles/s41598-024-60801-4

**[P03] Optimal Plant Density, Nutrient Concentration and Rootzone Temperature for Higher Growth and Yield of Brassica rapa L. Curly Dwarf Pak Choy in Raft Hydroponic System Under Tropical Climate** — journal_research. https://tost.unise.org/pdfs/vol7/no3-2/7x3-2x178-188xOA.html

**[P04] Extended photoperiod improves growth and nutritional quality of pak choi under constant daily light integral** — journal_research. https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1621513/full

**[P05] Microclimate control to increase productivity and nutritional quality of leafy vegetables in a cost-effective manner** — journal_research_overview. https://ijabe.org/index.php/ijabe/article/view/7367

**[P06] Nitrate accumulation, productivity and photosynthesis of Brassica alboglabra grown under low light with supplemental LED lighting in the tropical greenhouse** — journal_research. https://www.tandfonline.com/doi/full/10.1080/01904167.2019.1643367

**[P07] Reduced nitrogen availability in hydroponically grown Chinese broccoli does not affect photosynthetic performance and yield while enhancing nitrogen use efficiency and nutritional quality** — journal_research. https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1745794/full

**[P08] Controlling root zone temperature improves plant growth and pigments in hydroponic lettuce** — journal_research. https://academic.oup.com/aob/article/132/3/455/7265388

**[P09] Raising root zone temperature improves plant productivity and metabolites in hydroponic lettuce production** — journal_research. https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2024.1352331/full

**[P10] A short-term cooling of root-zone temperature increases bioactive compounds in baby leaf Amaranthus tricolor L.** — journal_research. https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2022.944716/full

**[P11] Changes in Growth and Anthocyanin Content of Brassica juncea L. affected by Light Intensity and Photoperiod in Plant Factory with Artificial Lighting** — journal_research. https://www.hst-j.org/articles/xml/LDxK/

**[P12] Effect of Light Quality on Physiological Disorder, Growth, and Secondary Metabolite Content of Water Spinach (Ipomoea aquatica Forsk) Cultivated in a Closed-type Plant Production System** — journal_research. https://www.hst-j.org/articles/xml/Mz2A/

**[P13] Growth and photosynthetic characteristics of sweet potato (Ipomoea batatas) leaves grown under natural sunlight with supplemental LED lighting in a tropical greenhouse** — journal_research. https://pubmed.ncbi.nlm.nih.gov/32763651/

**[P14] Plant Growth and Nutritional Quality Attributes of Basella alba Applied with Variable Rates of Nitrogen Fertilizer at Different Planting Dates under Canadian Maritime Climatic Conditions** — journal_research. https://onlinelibrary.wiley.com/doi/10.1155/2021/5577696

**[P15] Effects of Temperature, Relative Humidity, and Carbon Dioxide Concentration on Growth and Glucosinolate Content of Kale Grown in a Plant Factory** — journal_research. https://www.mdpi.com/2304-8158/10/7/1524

**[P16] Using Machine Learning Models to Predict Hydroponically Grown Lettuce Yield** — journal_research. https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2022.706042/full

**[P17] Lettuce Production in Intelligent Greenhouses—3D Imaging and Computer Vision for Plant Spacing Decisions** — journal_research. https://research.wur.nl/en/publications/lettuce-production-in-intelligent-greenhouses3d-imaging-and-compu/

**[P18] Effect of harvesting interval and defoliation on yield and chemical composition of leaves, stems and tubers of sweet potato (Ipomoea batatas L. (Lam.)) plant parts** — journal_research. https://www.sciencedirect.com/science/article/abs/pii/S0378429003000182

**[P19] Limitations to photosynthesis of lettuce grown under tropical conditions: alleviation by root-zone cooling** — journal_research. https://academic.oup.com/jxb/article-abstract/52/359/1323/510957

**[P20] Enhancing Productivity and Improving Nutritional Quality of Subtropical and Temperate Leafy Vegetables in Tropical Greenhouses and Indoor Farming Systems** — journal_review. https://www.mdpi.com/2311-7524/10/3/306

**[D01] NEA station rainfall** — dataset_or_api. https://data.gov.sg/datasets/d_6580738cdd7db79374ed3152159fbd69/view

**[D02] NEA air temperature** — dataset_or_api. https://data.gov.sg/datasets/d_66b77726bbae1b33f218db60ff5861f0/view

**[D03] NEA relative humidity** — dataset_or_api. https://data.gov.sg/datasets/d_2d3b0c4da128a9a59efca806441e1429/view

**[D04] NEA 24-hour weather forecast** — dataset_or_api. https://data.gov.sg/datasets/d_ce2eb1e307bda31993c533285834ef2b/view

**[D05] NEA four-day weather forecast** — dataset_or_api. https://data.gov.sg/datasets/d_f131f6e343bf8168e4057a04c4326a0a/view

**[D06] SingStat T010002 merchandise trade volume** — dataset_or_api. https://tablebuilder.singstat.gov.sg/table/TR/T010002

**[D07] SingStat T010001 merchandise trade value** — dataset_or_api. https://tablebuilder.singstat.gov.sg/table/TR/T010001

**[D08] Singapore monthly CPI components** — dataset_or_api. https://data.gov.sg/datasets/d_bdaff844e3ef89d39fceb962ff8f0791/view

**[D09] Singapore annual local production** — dataset_or_api. https://data.gov.sg/datasets/d_c02f75e7dd48f2e24f61e007033c28ca/view

**[D10] SFA Singapore Food Statistics 2025** — dataset_or_api. https://www.sfa.gov.sg/news-publications/newsroom/singapore-food-statistics-2025

**[D11] NASA POWER daily/hourly meteorology** — dataset_or_api. https://power.larc.nasa.gov/docs/services/api/temporal/daily/

**[D12] ERA5-Land hourly time-series** — dataset_or_api. https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries

**[D13] NOAA Global Forecast System** — dataset_or_api. https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast

**[D14] NASA GPM IMERG** — dataset_or_api. https://gpm.nasa.gov/data/imerg

**[D15] Copernicus Sentinel-2 L2A** — dataset_or_api. https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2

**[D16] Copernicus Sentinel-1** — dataset_or_api. https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1

**[D17] FAOSTAT production, area, yield and trade** — dataset_or_api. https://www.fao.org/faostat/en/

**[D18] UN Comtrade** — dataset_or_api. https://comtrade.un.org/

**[D19] Open-Meteo hosted weather API** — dataset_or_api. https://open-meteo.com/en/pricing

**[D20] WUR Autonomous Greenhouse Challenge lettuce climate and annotated images** — dataset_or_api. https://research.wur.nl/en/datasets/3rd-autonomous-greenhouse-challenge-time-series-data-on-realized-/

**[D21] Pak choi photoperiod study LC-MS deposit** — dataset_or_api. https://doi.org/10.5281/zenodo.16271244

**[D22] Crossref scholarly metadata API** — dataset_or_api. https://www.crossref.org/documentation/retrieve-metadata/rest-api/

**[D23] NEA weather radar images (beta)** — dataset_or_api. https://data.gov.sg/datasets/d_418e9ac3414fd927b7405631e0a7bc82/view

**[T01] Codex subagent configuration** — official_technical_documentation. https://learn.chatgpt.com/docs/agent-configuration/subagents

**[T02] GPT-6 Astra model** — official_technical_documentation. https://developers.openai.com/api/docs/models/gpt-6-astra

**[T03] GPT-5.6 Sol model** — official_technical_documentation. https://developers.openai.com/api/docs/models/gpt-5.6-sol

**[T04] OpenAI structured outputs** — official_technical_documentation. https://developers.openai.com/api/docs/guides/structured-outputs

**[T05] OR-Tools CP-SAT solver** — official_technical_documentation. https://developers.google.com/optimization/cp/cp_solver

**[T06] Copernicus Data Space STAC API** — official_technical_documentation. https://documentation.dataspace.copernicus.eu/APIs/STAC.html

**[T07] FAO statistical database terms** — official_technical_documentation. https://www.fao.org/contact-us/terms/db-terms-of-use/en/

**[T08] SingStat developer API** — official_technical_documentation. https://tablebuilder.singstat.gov.sg/view-api/for-developers

**[T09] Codex configuration reference** — official_technical_documentation. https://learn.chatgpt.com/docs/config-file/config-reference
