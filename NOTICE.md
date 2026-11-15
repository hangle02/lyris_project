# NOTICE

Third-party material used by Lyris, and the terms it comes with. The detailed, per-file list (in Vietnamese) is
[wiki/design/credits.md](wiki/design/credits.md); in the app the same credits are under Tài khoản →
"Giới thiệu & bản quyền ảnh".

## Lyris code and content

- **No open-source licence is granted** for the Lyris code, prompts, wiki or documentation in this repository.
  Publishing it on GitHub for review does not grant any right to copy, modify or redistribute it.
- Ownership follows the course brief ("Ownership and publishing"): products that pass Apero's gating process are
  published under Apero's name, and the copyright belongs to Apero. The third-party material below keeps its own
  licence in every case.

## AI model

- Lyris does **not** include any model weights. The operator installs the model separately through Ollama
  (default `gemma4:12b`, set by `LYRIS_CHAT_MODEL`).
- Gemma models are provided by Google under Google's own terms for the Gemma family (Gemma Terms of Use and the
  Gemma Prohibited Use Policy, published at <https://ai.google.dev/gemma/terms>). The operator must check and follow
  the licence that applies to the exact model version deployed, and Lyris must not be used for anything that
  licence prohibits.
- [Ollama](https://github.com/ollama/ollama) is a separate program, installed by the operator, under the MIT
  licence. Lyris talks to it over HTTP and does not redistribute it.

## Fonts

Self-hosted from the `@fontsource` packages (version 5.3.0, licence `OFL-1.1` in each package's `package.json`),
all under the **SIL Open Font License 1.1** (<https://openfontlicense.org>):

| Font | Copyright |
|---|---|
| Cormorant Garamond | Copyright 2015 The Cormorant Project Authors (github.com/CatharsisFonts/Cormorant) |
| Plus Jakarta Sans | Copyright 2020 The Plus Jakarta Sans Project Authors (https://github.com/tokotype/PlusJakartaSans) |
| Be Vietnam Pro | Copyright 2021 The Be Vietnam Pro Project Authors (https://github.com/bettergui/BeVietnamPro) |

The full licence text ships in each package (`frontend/node_modules/@fontsource/*/LICENSE`).

## Images of the sample characters

From Wikimedia Commons, cropped to a 3:4 portrait frame (files in `backend/lyris/seed/templates/`):

| Character | File | Original | Author | Licence | Changes |
|---|---|---|---|---|---|
| Hạ Vy | `ha-vy.jpg` | [Da Lat - Viet Nam](https://commons.wikimedia.org/wiki/File:Da_Lat_-_Viet_Nam.jpg) | Tuong Lam Photos | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | Cropped and resized; the edited file is shared under the same CC BY-SA 4.0 licence |
| Trần Minh Khang | `tran-minh-khang.jpg` | [2024-11-16 Ho Chi Minh City at night 3](https://commons.wikimedia.org/wiki/File:2024-11-16_Ho_Chi_Minh_City_at_night_3.jpg) | Alexey Komarov (Alexkom000) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0) | Cropped and resized |
| Tạ Vân Lan | `ta-van-lan.jpg` | Landscape in the Style of Juran and Yan Wengui, 1713 ([Wikimedia Commons](https://commons.wikimedia.org/wiki/File:%E6%B8%85_%E7%8E%8B%E7%BF%AC_%E5%80%A3%E5%B7%A8%E7%84%B6%E7%87%95%E6%96%87%E8%B2%B4%E5%B1%B1%E6%B0%B4%E5%9C%96_%E5%8D%B7-Landscape_in_the_Style_of_Juran_and_Yan_Wengui_MET_DP204418.jpg)) | Wang Hui | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) | A section of the scroll (The Metropolitan Museum of Art) cropped to 3:4 |
| Morwenna Penrose | `morwenna-penrose.jpg` | [Pendeen Watch lighthouse Cornwall](https://commons.wikimedia.org/wiki/File:Pendeen_Watch_lighthouse_Cornwall.jpg) | Tom Corser (www.tomcorser.com) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) | Cropped and resized; the edited file is shared under the same CC BY-SA 3.0 licence |

The screenshots in `docs/assets/screenshots/` show some of these images inside the app; the same attribution and
licences apply to those parts of the screenshots.

Characters that a user or operator adds through the app (and their pictures) live in the operator's database, not
in this repository; whoever uploads them is responsible for their rights. Pictures of the characters in `worlds/`
are not in this repository (see [credits.md §4](wiki/design/credits.md)).

## Icons

The icons in `frontend/src/components/icons.tsx` are drawn after the outlines of [Lucide](https://lucide.dev)
(ISC licence); the Lucide package itself is not installed. The Lyris logo, wordmark, four-point star, favicon and
home-screen icon are Lyris's own drawings.

## Software libraries

The backend and frontend use open-source libraries, each under its own licence, pinned in `backend/uv.lock` and
`frontend/package-lock.json`. The production frontend build (`frontend/dist/`) bundles some of these npm packages;
their licence notices stay with the packages.
