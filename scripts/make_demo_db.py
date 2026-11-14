#!/usr/bin/env python3
"""Tạo một DB demo cho Lyris (để chụp màn hình, thử giao diện, kiểm tra luồng) mà không gọi Ollama.

Cách chạy (luôn dùng Python của backend):

    backend/.venv/bin/python scripts/make_demo_db.py /tmp/lyris-demo/lyris.db /tmp/lyris-demo/avatars

Rồi chạy backend trỏ vào đó:

    LYRIS_DB_PATH=/tmp/lyris-demo/lyris.db LYRIS_AVATARS_DIR=/tmp/lyris-demo/avatars \
        backend/.venv/bin/uvicorn lyris.api.app:app --port 8023

Nội dung tạo ra:
- tài khoản chủ máy đã đặt profile (tên hiển thị, @handle, giới thiệu, avatar chữ cái; tên giả, không
  phải thông tin của ai), nên lời mời "Đặt tên cho tài khoản của bạn" không hiện. Thêm
  --fresh-account để giữ tài khoản mặc định ('Bạn', @ban, profile_completed = 0) như lần mở đầu tiên;
- một nhân vật do tài khoản tự tạo (Phạm Hoài An, riêng tư, có avatar chữ cái), để trang profile và
  Studio có "bởi @handle";
- cài 4 nhân vật mẫu qua chính API (`POST /api/templates/{slug}/install`, ảnh mẫu thành avatar);
  card seed Lạc Dương có sẵn được giữ (trang Khám phá nhận là đã cài);
- 2 persona mới (Ngọc Anh, Gia Huy), mỗi persona một avatar chữ cái màu phẳng (Pillow), đặt Ngọc Anh
  làm persona mặc định; persona seed Lâm Vãn giữ nguyên, không ảnh;
- 4 story (story seed bị xoá):
  * Hạ Vy và Ngọc Anh, Story Mode, câu chuyện dài (nhiều lượt, Thought inline, chỉ đạo ((...)),
    lượt cuối có 2 phiên bản, một lượt được thích);
  * Trần Minh Khang và Ngọc Anh: vài lượt Story rồi chuyển sang DM;
  * Morwenna Penrose và Gia Huy, tiếng Anh;
  * Tạ Vân Lan và Gia Huy, cũ hơn vài ngày.
- giờ của tin nhắn được lùi về quá khứ để danh sách hiện "hh:mm", "Hôm qua" và ngày cũ.
- state Phase 3 (docs/phase3.md) như thể worker đã trích xuất xong: thay đổi cảm xúc (tối đa 2 chỉ số mỗi
  lượt), cảnh, ký ức và fact, kể cả lời mở đầu (lượt 0: cảnh + ký ức), một tóm tắt tự động (Hạ Vy), nên
  "Xem sự kiện" có dòng thời gian. Mỗi lượt có job `extract` đã `done`. Gợi ý trả lời chỉ có ở story Hạ Vy,
  như thể người chơi vừa bấm "Nhận gợi ý" (Phase 3b: không còn gợi ý tự động).
  Riêng story Tạ Vân Lan để trống (như story có từ trước Phase 3), nên ngăn cảm xúc mời "Đọc lại story".

Phase 4b: chủ máy của DB demo chưa có mật khẩu. Backend chạy trên DB này in mã thiết lập ra Terminal (hoặc
`LYRIS_DB_PATH=... bash scripts/lyris-admin.sh setup-code`); nhập mã ở trang thiết lập rồi đặt mật khẩu.

App chạy với LLM giả (FakeLLM) và OLLAMA_URL trỏ vào cổng chết, nên không bao giờ gọi Ollama.
Từ chối ghi vào thư mục data/ của repo. DB đã có thì dừng, trừ khi thêm --force (xoá rồi tạo lại).
"""
from __future__ import annotations

import argparse
import asyncio
import io
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from lyris.api.app import create_app  # noqa: E402
from lyris.auth import clock as auth_clock  # noqa: E402
from lyris.auth import store as auth_store  # noqa: E402
from lyris.auth.net import SESSION_COOKIE  # noqa: E402
from lyris.auth.passwords import SCRYPT_N, SCRYPT_P, SCRYPT_R, PasswordHash  # noqa: E402
from lyris.config import Settings  # noqa: E402
from lyris.db.repo import ANY_ACCOUNT, Repo  # noqa: E402
from lyris.jobs.worker import extraction_rows  # noqa: E402
from lyris.llm.fake import FakeLLM  # noqa: E402
from lyris.llm.thought import split_thought  # noqa: E402
from lyris.models import (  # noqa: E402
    ExtractionResult,
    FactDraft,
    Message,
    Mode,
    RelationshipDelta,
    SceneState,
)
from lyris.prompt.directives import extract_directives  # noqa: E402
from lyris.state.extract import top_delta  # noqa: E402

DEAD_OLLAMA_URL = "http://127.0.0.1:9"  # cổng discard: mọi kết nối bị từ chối ngay
DEMO_MODEL = "gemma4:12b"

TEMPLATES = ("ha-vy", "tran-minh-khang", "morwenna-penrose", "ta-van-lan")

PERSONAS: list[dict[str, str]] = [
    {
        "name": "Ngọc Anh",
        "gender": "female",
        "description": (
            "24 tuổi, biên tập viên ở một nhà xuất bản nhỏ tại Sài Gòn. Lên Đà Lạt nghỉ phép một tháng "
            "sau đợt làm việc kiệt sức. Ít nói với người lạ nhưng hay để ý chi tiết nhỏ, mê sách cũ."
        ),
    },
    {
        "name": "Gia Huy",
        "gender": "male",
        "description": (
            "27 tuổi, kỹ sư phần mềm vừa nghỉ việc, đang đi bộ một mình qua những nơi xa lạ. "
            "Điềm tĩnh, hơi vụng về khi nói chuyện cảm xúc, thích hỏi chuyện người địa phương."
        ),
    },
]


# Tài khoản demo: tên giả, không phải người thật.
ACCOUNT: dict[str, str] = {
    "display_name": "Minh Thư",
    "handle": "minhthu.viet",
    "bio": (
        "Viết nhân vật vào những đêm mưa. Thích truyện chữa lành, tiệm sách cũ và những lá thư không bao giờ gửi."
    ),
}

# Màu nền phẳng của avatar chữ cái (tông ấm, chữ sáng đọc rõ).
AVATAR_COLORS: dict[str, str] = {
    "Minh Thư": "#7A4A5E",
    "Ngọc Anh": "#9A5A4A",
    "Gia Huy": "#4A5E6E",
    "Phạm Hoài An": "#5E5A3E",
}

OWN_CARD: dict[str, Any] = {
    "name": "Phạm Hoài An",
    "role": "Thợ sửa đồng hồ ở phố cổ Hội An",
    "gender": "male",
    "language": "vi",
    "description": (
        "29 tuổi, giữ tiệm sửa đồng hồ của ông nội trên đường Trần Phú, Hội An. {{user}} mang tới một chiếc "
        "đồng hồ quả quýt cũ đã đứng kim từ lâu."
    ),
    "personality": (
        "Chậm rãi, kiên nhẫn, nói ít nhưng nhớ lâu. Hay đùa khô khan để giấu chuyện mình để ý người khác. "
        "Ghét làm ẩu, thà trả máy lại còn hơn sửa cho có."
    ),
    "appearance": "Gầy, tóc hơi dài buộc gọn sau gáy, kính lúp kẹp trên trán, tay áo lúc nào cũng dính chút dầu máy.",
    "background": (
        "Học cơ khí ở Đà Nẵng rồi về phố cổ khi ông nội yếu đi. Tiệm nhỏ, ba mặt tường treo kín đồng hồ, "
        "tiếng tích tắc không bao giờ ngớt."
    ),
    "goals": "Giữ tiệm sống qua mùa vắng khách, và sửa cho xong chiếc đồng hồ ông nội bỏ dở.",
    "secrets": "Chiếc đồng hồ quả quýt {{user}} mang tới giống hệt chiếc ông nội từng sửa cho một người rồi không ai đến lấy.",
    "speech_style": "Câu ngắn, giọng Quảng nhẹ, hay hỏi lại một câu thay cho lời an ủi.",
    "style_profile": "viet_hien_dai",
    "address_terms": {"self_term": "anh", "player_term": "em", "nicknames": [], "others": ""},
    "greeting": (
        "Chuông gió ở cửa kêu leng keng khi {{user}} bước vào. Hoài An ngẩng lên khỏi chiếc kính lúp, tay vẫn "
        "còn cầm cây nhíp nhỏ.\n\n"
        "[Thought: Đồng hồ quả quýt, vỏ bạc, chắc phải hơn năm mươi năm. Ai lại mang thứ này đi sửa giữa mùa nước nổi.]\n\n"
        '"Đặt lên quầy giúp anh. Nhẹ tay thôi, máy cũ hay dỗi lắm."'
    ),
    "scenario": "Một chiều mưa tháng mười ở phố cổ Hội An, nước sông Hoài vừa lên tới bậc thềm.",
    "tags": ["chữa lành", "hiện đại", "Hội An"],
}


@dataclass(frozen=True)
class Turn:
    role: str  # "user" | "assistant"
    text: str
    mode: Mode = "story"
    minutes: float = 3.0  # phút sau lượt trước
    variants: tuple[str, ...] = ()  # các phiên bản khác của lượt AI (bản cuối là bản đang chọn)
    rating: str | None = None


# ---------------------------------------------------------------------------------------------
# Hạ Vy (Đà Lạt, tiệm sách) và Ngọc Anh: câu chuyện dài, Story Mode.

HA_VY: list[Turn] = [
    Turn(
        "user",
        '*Ngọc Anh đón lấy chiếc khăn, lau qua mái tóc còn đẫm nước rồi khẽ gật đầu cảm ơn.* '
        '"Cảm ơn Vy. Trà thơm quá." *Ngón tay chạm vào mép phong bì giấy dó kẹp giữa trang sách.* '
        '"Mà cái phong bì này của ai vậy? Hôm qua mình đọc tới đây đâu có thấy."',
    ),
    Turn(
        "assistant",
        "Hạ Vy khựng lại nửa nhịp, tay vẫn còn cầm quai ấm. Ánh đèn vàng trên quầy hắt xuống, làm nét mực tím "
        "trên phong bì như nhoè thêm một chút.\n\n"
        "[Thought: Biết ngay là sẽ bị hỏi mà. Lẽ ra mình nên cất nó vào ngăn kéo từ tối qua.]\n\n"
        '"À, cái đó..." Cô đặt ấm xuống, kéo chiếc ghế đẩu lại ngồi đối diện. "Thư cũ thôi. Người ta bán cả '
        'thùng sách cho tiệm, trong đó có mấy lá thư kẹp sẵn. Mình chưa nỡ bỏ đi."\n\n'
        "Cô vươn tay định rút phong bì lại, nhưng rồi dừng giữa chừng, chỉ khẽ vuốt cho thẳng một góc giấy bị quăn.\n\n"
        '"Cậu đọc tới chương nào rồi? Nếu thích cuốn này thì mình để dành cho cậu, khỏi phải ngày nào cũng '
        'đội mưa lên dốc giữ chỗ."',
        minutes=4,
    ),
    Turn(
        "user",
        '"Chương bảy, đoạn hai người hẹn nhau ở ga xe lửa." *Ngọc Anh ôm tách trà vào hai lòng bàn tay cho ấm.* '
        '"Mình không mua đâu. Đọc ở đây mới có mùi gỗ thông với tiếng mưa, mang về nhà trọ thì mất hết." '
        '((Vy hơi bối rối vì câu đó nghe như một lời khen dành cho chính cô))',
        minutes=6,
    ),
    Turn(
        "assistant",
        "Một tiếng cười rất khẽ bật ra trước khi Hạ Vy kịp giữ lại. Cô cúi xuống nhìn tách trà trong tay, "
        "vành tai đỏ lên dưới mấy sợi tóc mai.\n\n"
        '"Cậu nói vậy là chú Tư bên cạnh nghe được, mai chú lại đòi mình bán cả cái gác xép cho chú làm '
        'quán cà phê đó."\n\n'
        "[Thought: Mùi gỗ thông với tiếng mưa. Ba năm nay mình cứ nghĩ chỉ có mình là để ý mấy thứ đó.]\n\n"
        "Ngoài cửa sổ, mưa phùn dày thêm, dãy thông bên kia dốc chỉ còn là những vệt xám mờ. Con mèo mướp nằm "
        "trên chồng báo cũ vươn vai, nhảy xuống, đi một vòng quanh chân ghế của Ngọc Anh rồi nằm luôn lên mũi giày.\n\n"
        '"Bé Mướp chịu ai là nằm lên chân người đó." Vy chống cằm. "Vậy là cậu thành khách quen chính thức rồi. '
        'Khách quen thì được lên gác xép đọc sách. Muốn thử không?"',
        minutes=5,
        rating="up",
    ),
    Turn(
        "user",
        "*Ngọc Anh nhìn con mèo, rồi nhìn lên chiếc cầu thang gỗ hẹp dẫn lên gác.* "
        '"Thật hả? Mình tưởng trên đó là chỗ riêng của Vy."',
        minutes=4,
    ),
    Turn(
        "assistant",
        "Hạ Vy đứng dậy, phủi vạt tạp dề rồi với lấy cây đèn dầu nhỏ trên kệ. Cầu thang kêu cót két dưới bước chân cô, "
        "mỗi bậc một tiếng khác nhau, như ai đó đang gảy một cây đàn cũ.\n\n"
        '"Là chỗ riêng thật. Nhưng chỗ riêng mà không có ai ngồi thì buồn lắm."\n\n'
        "Gác xép thấp, mái dốc, ô cửa sổ tròn nhìn thẳng ra rặng thông. Sách chất thành từng chồng sát vách, giữa phòng "
        "là tấm nệm bông trải trên sàn gỗ và chiếc bàn gấp có lọ hoa dã quỳ đã héo một nửa.\n\n"
        "[Thought: Lần cuối có người lên đây cùng mình là mùa thu năm đó. Mình còn chưa kịp thay lọ hoa.]\n\n"
        "Vy đặt cây đèn xuống bàn, ngập ngừng một chút rồi rút lá thư từ cuốn sách trên tay Ngọc Anh, kẹp vào một cuốn "
        'khác trên kệ cao.\n\n"Cuốn đó cậu cứ đọc tiếp. Còn lá thư..." Cô quay lại, cười nhẹ. "Để hôm nào trời tạnh, '
        'mình kể cho nghe. Được không?"',
        minutes=7,
    ),
    Turn(
        "user",
        '"Được." *Ngọc Anh ngồi xuống tấm nệm, nhìn lọ dã quỳ héo.* "Vậy mai trời tạnh, mình mang hoa mới lên thay '
        'cho lọ này nhé. Coi như tiền thuê chỗ."',
        minutes=5,
    ),
    Turn(
        "assistant",
        "Vy đứng yên ở đầu cầu thang. Ánh đèn dầu chập chờn trên khuôn mặt cô, không rõ là đang cười hay đang cố "
        "không cười.\n\n"
        '"Dã quỳ thì phải hái ở dốc sau nhà thờ Con Gà, chỗ đó hoa vàng nhất."\n\n'
        "[Thought: Năm đó cũng có người nói y hệt câu này. Người ta hứa mang hoa lên, rồi đi luôn không về.]\n\n"
        "Cô xoay người đi xuống, đến bậc thứ ba thì dừng lại, nói vọng lên mà không quay đầu:\n\n"
        '"Mai mình mở cửa lúc tám giờ. Nhớ đến sớm, trước khi mấy ông bà khách quen giành mất chỗ ngồi gần cửa sổ."',
        minutes=6,
        variants=(
            "Vy bật cười, lần này không giấu nữa. Cô bước lại gần, cúi xuống nhặt một cánh dã quỳ rơi trên mặt bàn, "
            "xoay xoay giữa hai ngón tay.\n\n"
            '"Tiền thuê chỗ ở tiệm này đắt lắm đó. Một bó hoa chưa đủ đâu."\n\n'
            "[Thought: Sao người này nói câu nào cũng làm mình muốn giữ lại thêm một chút vậy.]\n\n"
            '"Thêm một buổi chiều ngồi đọc sách với mình nữa thì mới đủ." Cô đặt cánh hoa lên trang sách đang mở '
            'của Ngọc Anh. "Cậu chịu không?"',
        ),
    ),
]

# ---------------------------------------------------------------------------------------------
# Trần Minh Khang (Sài Gòn mùa mưa) và Ngọc Anh: vài lượt Story, rồi nhắn tin (DM) tối hôm đó.

KHANG: list[Turn] = [
    Turn(
        "user",
        '*Ngọc Anh cắm sạc vào điện thoại, ngước lên cười ngượng.* "Dạ, em cảm ơn anh. Em quên sạc từ trưa, '
        'lo sửa bản vẽ mặt đứng cho kịp chiều nay."',
    ),
    Turn(
        "assistant",
        "Khang gật đầu, không nói gì thêm. Một chiếc xe buýt chạy ngang, hất nước tràn lên vỉa hè, anh nghiêng người "
        "đứng chắn phía ngoài theo phản xạ.\n\n"
        "[Thought: Bản vẽ mặt đứng đó anh duyệt rồi, sửa thêm cũng không ai bắt. Nhóc này cầu toàn hơn anh tưởng.]\n\n"
        '"Mặt đứng ổn rồi, mai khỏi sửa nữa." Anh rút điện thoại ra, mở màn hình. "Đọc số đi, lát về tới nhà thì '
        'nhắn anh một tiếng. Đường Võ Văn Tần ngập là ngập tới đầu gối đó."',
        minutes=4,
    ),
    Turn("user", "Anh ơi, em về tới nhà rồi nha.\nCảm ơn anh vụ áo mưa với cục sạc, mai em gửi lại.", mode="dm", minutes=290),
    Turn(
        "assistant",
        "Ừ, tới là được.\nÁo mưa cứ giữ, anh còn cái khác.\n[Thought: Nhắn đúng giờ ghê. Lẽ ra nên hỏi thêm có bị ướt "
        "nhiều không.]",
        mode="dm",
        minutes=2,
    ),
    Turn("user", "Dạ. Mà anh về chưa? Lúc em đi mưa vẫn còn lớn lắm.", mode="dm", minutes=1.5),
    Turn(
        "assistant",
        "Về rồi. Kẹt xe ở Lý Chính Thắng gần tiếng.\nNgủ sớm đi, mai 8 giờ họp với bên chủ đầu tư.",
        mode="dm",
        minutes=3,
    ),
    Turn("user", "Dạ, em biết rồi. Anh cũng ngủ sớm nha.\nMai em mang bánh mì cho anh, coi như trả công.", mode="dm", minutes=2),
    Turn(
        "assistant",
        "Không cần đâu.\nMà nếu mang thì bánh mì chả cá đầu hẻm công ty, đừng mua chỗ khác.\n[Thought: Vừa nói không "
        "cần xong lại dặn tiệm. Mình bị gì vậy trời.]",
        mode="dm",
        minutes=4,
    ),
]

# ---------------------------------------------------------------------------------------------
# Morwenna Penrose (Cornwall) và Gia Huy: tiếng Anh.

MORWENNA: list[Turn] = [
    Turn(
        "user",
        '*Huy takes the towel and wipes the rain from his face, still catching his breath.* "Thanks. I wanted to see '
        'the waves before the storm peaked. Didn\'t think the path would vanish that fast."',
    ),
    Turn(
        "assistant",
        "Morwenna snorted and took the towel back before it could drip on her logbook. She jerked her chin at the "
        "iron stove in the corner, where a kettle was already rattling its lid.\n\n"
        '"Nobody thinks it will. That\'s how the harbour master ends up fishing tourists out of the cove every '
        'October."\n\n'
        "[Thought: He's shaking. Pretending he isn't, but he is. Three days of watching the sea like it owes him "
        "something.]\n\n"
        "She poured two mugs of tea strong enough to stand a spoon in and pushed one across the table.\n\n"
        '"Drink that. The lamp needs checking at seven, and you can carry the bulbs up since you\'re so keen on '
        'heights. Unless you\'d rather tell me what you\'re really doing out here?"',
        minutes=5,
    ),
    Turn(
        "user",
        '"I quit my job last month." *He wraps both hands around the mug.* "Thought walking the coast would help me '
        'figure out what comes next. So far it\'s mostly taught me I own the wrong boots."',
        minutes=6,
    ),
    Turn(
        "assistant",
        "That earned a short laugh, the first real one, gone almost before it arrived. Morwenna leaned back until "
        "her chair creaked and looked at him properly for the first time.\n\n"
        '"Wrong boots is a start. My gran said the sea never answers the question you bring it, only the one you '
        'were too scared to ask."\n\n'
        "[Thought: Listen to me, quoting Gran to a stranger. The storm must be getting into my head.]\n\n"
        "Above them, the great lens began its slow turn, and a sweep of white light passed over the rain-streaked "
        'window.\n\n"Right. Seven o\'clock. Bulbs are by the door, landlubber. Mind the fourth step, it bites."',
        minutes=5,
    ),
]

# ---------------------------------------------------------------------------------------------
# Tạ Vân Lan (cổ trang, Thanh Vân Tông) và Gia Huy: câu chuyện cũ hơn.

VAN_LAN: list[Turn] = [
    Turn(
        "user",
        '*Gia Huy thu kiếm, thở dốc, cúi đầu hành lễ.* "Đa tạ đại sư tỷ. Ta chỉ sợ ngày mai lên đài lại làm mất mặt '
        'Thanh Vân Tông."',
    ),
    Turn(
        "assistant",
        "Tạ Vân Lan không đáp ngay. Nàng bước tới, hai ngón tay đặt lên mạch cổ tay Gia Huy, chân khí lạnh như suối "
        "đầu nguồn theo đó chảy vào, lặng lẽ dẹp yên mấy luồng khí còn đang cuộn loạn.\n\n"
        '"Mất mặt tông môn là chuyện của chưởng môn. Còn mạng của ngươi là chuyện của ngươi."\n\n'
        "[Thought: Mạch tượng loạn thế này mà còn lo chuyện mặt mũi. Năm xưa ta cũng ngốc y như vậy.]\n\n"
        "Nàng thu tay, quay lưng bước về phía rừng trúc, tà áo trắng lướt qua mặt đá không một tiếng động.\n\n"
        '"Giờ Mão, tới Tàng Kinh Các. Ta chỉ ngươi thức thứ bảy thêm một lần. Lần cuối."',
        minutes=5,
    ),
]


# ---------------------------------------------------------------------------------------------
# State Phase 3: kết quả "trích xuất" viết tay cho từng lượt trả lời, cùng định dạng worker ghi thật.


@dataclass(frozen=True)
class DemoState:
    delta: dict[str, int]
    location: str | None = None
    time: str | None = None
    memory: str | None = None
    importance: int = 3
    facts: tuple[tuple[str, str], ...] = ()  # (subject, text)

    def result(self) -> ExtractionResult:
        # Như `validate` của trích xuất thật (Phase 3b): mỗi lượt chỉ giữ 2 thay đổi cảm xúc lớn nhất.
        return ExtractionResult(
            relationship_delta=RelationshipDelta(**top_delta(self.delta)),
            scene=SceneState(location=self.location, time=self.time),
            memory=self.memory,
            memory_importance=self.importance,
            facts=[FactDraft(subject=s, text=t) for s, t in self.facts],
        )


# Phase 3b: lời mở đầu (lượt 0) cũng được trích xuất, chỉ cảnh + ký ức (không thay đổi cảm xúc).
OPENINGS: dict[str, DemoState] = {
    "ha-vy": DemoState(
        {},
        location="Tiệm sách cũ trên dốc",
        time="Chiều mưa",
        memory="Hạ Vy mời Ngọc Anh tách trà gừng rồi hỏi cô đã đọc lá thư kẹp trong cuốn sách chưa.",
        importance=3,
    ),
    "tran-minh-khang": DemoState(
        {},
        location="Hiên tòa nhà văn phòng trên Võ Văn Tần",
        time="Chiều mưa",
        memory="Khang đưa Ngọc Anh cục sạc dự phòng và bộ áo mưa, rồi ngỏ ý chở cô về.",
        importance=3,
    ),
    "morwenna-penrose": DemoState(
        {},
        location="The lighthouse at Pendeen",
        time="Stormy dusk",
        memory="Morwenna called Huy in off the flooding cliff path and handed him a towel.",
        importance=3,
    ),
}

# Phase 3b: gợi ý chỉ có khi người chơi bấm "Nhận gợi ý". Story Hạ Vy giữ một bộ gợi ý như thể vừa được
# yêu cầu (để chụp màn hình trạng thái đó); các story khác không có gợi ý.
ON_DEMAND_SUGGESTIONS: dict[str, tuple[str, ...]] = {
    "ha-vy": (
        'Tôi gật đầu, cười. "Chịu. Mai mình mang cả hoa lẫn bánh lên."',
        'Tôi nhặt cánh hoa lên. "Vậy chiều đó Vy kể chuyện lá thư nhé?"',
        'Tôi giả vờ nghĩ ngợi. "Đắt vậy thì phải mặc cả đã."',
    ),
}


# slug -> vị trí lượt trong StoryPlan.turns -> state cho (bản đầu, *các phiên bản khác).
STATES: dict[str, dict[int, tuple[DemoState, ...]]] = {
    "ha-vy": {
        1: (
            DemoState(
                {"affection": 3, "trust": 2},
                memory="Ngọc Anh hỏi về phong bì thư tay kẹp trong cuốn sách; Hạ Vy lảng đi, nói đó là thư cũ đi kèm thùng sách mua lại.",
                importance=3,
                facts=(("Hạ Vy", "Hạ Vy giữ lại mấy lá thư cũ kẹp trong thùng sách người ta bán cho tiệm"),),
            ),
        ),
        3: (
            DemoState(
                {"affection": 4, "trust": 3, "attraction": 3},
                memory="Ngọc Anh nói đọc sách ở tiệm mới có mùi gỗ thông và tiếng mưa; Hạ Vy đỏ mặt rồi mời cô lên gác xép.",
                importance=4,
                facts=(
                    ("Ngọc Anh", "Ngọc Anh đang đọc tới chương bảy, đoạn hai nhân vật hẹn nhau ở ga xe lửa"),
                    ("Hạ Vy", "Con mèo mướp của tiệm tên là Bé Mướp"),
                ),
            ),
        ),
        5: (
            DemoState(
                {"affection": 2, "trust": 3, "attraction": 2, "obsession": 2},
                location="Gác xép tiệm sách",
                memory="Hạ Vy dẫn Ngọc Anh lên gác xép, cất lá thư lên kệ cao và hẹn hôm nào trời tạnh sẽ kể chuyện.",
                importance=5,
                facts=(("Hạ Vy", "Hạ Vy hứa sẽ kể chuyện lá thư cũ khi trời tạnh"),),
            ),
        ),
        7: (
            DemoState(
                {"affection": 2, "fear": 3, "obsession": 1},
                time="Chiều tối",
                memory="Ngọc Anh hứa mai mang dã quỳ lên thay lọ hoa; Hạ Vy chỉ dặn tám giờ tiệm mở cửa.",
                importance=4,
                facts=(("Ngọc Anh", "Ngọc Anh hứa mang hoa dã quỳ lên thay lọ hoa héo trên gác xép"),),
            ),
            DemoState(
                {"affection": 3, "attraction": 3, "obsession": 1},
                time="Chiều tối",
                memory="Ngọc Anh hứa mai mang dã quỳ lên thay lọ hoa; Hạ Vy đòi thêm một buổi chiều đọc sách cùng nhau.",
                importance=4,
                facts=(("Ngọc Anh", "Ngọc Anh hứa mang hoa dã quỳ lên thay lọ hoa héo trên gác xép"),),
            ),
        ),
    },
    "tran-minh-khang": {
        1: (
            DemoState(
                {"affection": 1, "trust": 3},
                location="Trạm xe buýt trước công ty",
                time="Chiều mưa",
                memory="Khang cho Ngọc Anh mượn áo mưa và cục sạc, dặn về tới nhà thì nhắn tin báo.",
                importance=4,
                facts=(("Ngọc Anh", "Ngọc Anh làm kiến trúc, vừa sửa xong bản vẽ mặt đứng mà Khang đã duyệt"),),
            ),
        ),
        3: (
            DemoState(
                {"affection": 2, "trust": 1},
                location="Nhà trọ của Ngọc Anh",
                time="Tối",
                memory="Ngọc Anh nhắn đã về tới nhà; Khang bảo cứ giữ áo mưa.",
                importance=2,
            ),
        ),
        5: (
            DemoState(
                {"trust": 1, "attraction": 1},
                memory="Khang kẹt xe ở Lý Chính Thắng gần một tiếng, nhắc Ngọc Anh ngủ sớm vì mai họp sớm.",
                importance=3,
                facts=(("Trần Minh Khang", "Mai 8 giờ cả nhóm họp với bên chủ đầu tư"),),
            ),
        ),
        7: (
            DemoState(
                {"affection": 3, "attraction": 2, "obsession": 1},
                time="Khuya",
                memory="Ngọc Anh hứa mai mang bánh mì cho Khang; anh nói không cần rồi dặn đúng tiệm chả cá đầu hẻm.",
                importance=4,
                facts=(("Trần Minh Khang", "Khang thích bánh mì chả cá ở đầu hẻm công ty"),),
            ),
        ),
    },
    "morwenna-penrose": {
        1: (
            DemoState(
                {"affection": 1, "trust": 1, "aversion": -2},
                location="The lighthouse cottage at Pendeen",
                time="Stormy evening",
                memory="Huy got caught on the cliff path in the storm and Morwenna took him in for strong tea.",
                importance=3,
                facts=(("Morwenna Penrose", "Morwenna checks the lighthouse lamp at seven every evening"),),
            ),
        ),
        3: (
            DemoState(
                {"affection": 2, "trust": 3, "attraction": 1, "aversion": -3},
                memory="Huy admitted he quit his job last month; Morwenna quoted her gran about the sea.",
                importance=4,
                facts=(("Gia Huy", "Huy quit his job last month and is walking the coast to figure out what comes next"),),
            ),
        ),
    },
}

# slug -> (vị trí lượt được tóm tắt tới, nội dung): tóm tắt tự động "những lượt cũ" cho ngăn cảm xúc.
SUMMARIES: dict[str, tuple[int, str]] = {
    "ha-vy": (
        1,
        "Một chiều mưa ở Đà Lạt, Ngọc Anh trú mưa trong tiệm sách cũ của Hạ Vy và đọc dở một cuốn tiểu thuyết. "
        "Cô thấy một phong bì thư tay kẹp giữa trang; Hạ Vy khựng lại, nói đó là thư cũ đi kèm thùng sách mua lại "
        "và chưa nỡ bỏ đi.",
    ),
}


def _apply_state(repo: Repo, message: Message, state: DemoState | None) -> None:
    """Ghi state của một lượt trả lời (message phải đang active) và đánh dấu job extract đã xong."""
    if state is None or message.id is None:
        return
    events, memories = extraction_rows(message, state.result(), [])
    saved = repo.replace_extraction(message.id, events, memories)
    assert saved is not None, "message phải active khi ghi state"
    job_id = repo.enqueue_job(message.story_id, "extract", message.id)  # job đang chờ (lời mở đầu) thì lấy lại nó
    repo.finish_job(job_id, "done", attempts=1, only_running=False)


def _apply_opening(repo: Repo, story_id: int, slug: str) -> None:
    """Lời mở đầu: POST /api/stories đã xếp job trích xuất; ghi kết quả như worker đã chạy xong. Story không
    có trong OPENINGS là story "có từ trước Phase 3": bỏ job đó, lời mở đầu chưa được ghi nhớ."""
    opening = repo.active_messages(story_id)[0]
    state = OPENINGS.get(slug)
    if state is None:
        repo.conn.execute("DELETE FROM jobs WHERE story_id = ?", (story_id,))
        repo.conn.commit()
        return
    _apply_state(repo, opening, state)


def _apply_suggestions(repo: Repo, story_id: int, slug: str) -> None:
    items = ON_DEMAND_SUGGESTIONS.get(slug)
    if not items:
        return
    last = repo.active_messages(story_id)[-1]
    assert last.id is not None and repo.replace_suggestions(last.id, list(items))


@dataclass(frozen=True)
class StoryPlan:
    template: str
    persona: str
    title: str
    turns: list[Turn]
    ago: timedelta  # thời điểm của lượt cuối, tính lùi từ lúc chạy script
    final_mode: Mode = "story"


STORIES: list[StoryPlan] = [
    # Thứ tự tạo; danh sách ở hub sắp theo hoạt động gần nhất.
    StoryPlan("ta-van-lan", "Gia Huy", "Đêm luyện kiếm ở hậu sơn", VAN_LAN, timedelta(days=4, hours=3)),
    StoryPlan("morwenna-penrose", "Gia Huy", "Storm at Pendeen", MORWENNA, timedelta(days=1, hours=2)),
    StoryPlan("tran-minh-khang", "Ngọc Anh", "Mưa đầu mùa", KHANG, timedelta(hours=5), final_mode="dm"),
    StoryPlan("ha-vy", "Ngọc Anh", "Gác xép mùi gỗ thông", HA_VY, timedelta(minutes=25)),
]


def initials_png(name: str, color: str, size: int = 512) -> bytes:
    """Avatar chữ cái: nền màu phẳng, chữ cái đầu của hai từ cuối (tên tiếng Việt) màu sáng, PNG."""
    words = name.split()
    letters = "".join(w[0] for w in words[-2:]).upper() if words else "?"
    img = Image.new("RGB", (size, size), color)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=int(size * (0.42 if len(letters) < 2 else 0.36)))
    draw.text((size / 2, size / 2), letters, fill="#FAF2EB", font=font, anchor="mm")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _message(story_id: int, turn_index: int, role: str, mode: Mode, text: str) -> Message:
    """Message giống hệt thứ ChatService ghi: tách Thought (AI) hoặc chỉ đạo ((...)) (người chơi)."""
    if role == "assistant":
        visible, thought = split_thought(text)
        return Message(
            story_id=story_id,
            turn_index=turn_index,
            role="assistant",
            mode=mode,
            raw_content=text,
            visible_content=visible,
            thought=thought,
            model_output=text,
            model_name=DEMO_MODEL,
        )
    visible, directive = extract_directives(text)
    return Message(
        story_id=story_id,
        turn_index=turn_index,
        role="user",
        mode=mode,
        raw_content=text.strip(),
        visible_content=visible,
        directive=directive,
    )


def _write_turns(repo: Repo, story_id: int, plan: StoryPlan, now: datetime) -> None:
    """Ghi các lượt sau lời mở đầu và lùi giờ của cả story về quá khứ."""
    total = sum(t.minutes for t in plan.turns) + sum(1.0 for t in plan.turns for _ in t.variants)
    start = now - plan.ago - timedelta(minutes=total + 2)  # lời mở đầu: 2 phút trước lượt đầu
    conn = repo.conn
    conn.execute(
        "UPDATE messages SET created_at = ? WHERE story_id = ? AND turn_index = 0",
        (_iso(start), story_id),
    )
    conn.execute(
        "UPDATE stories SET created_at = ?, updated_at = ? WHERE id = ?",
        (_iso(start), _iso(start), story_id),
    )
    clock = start + timedelta(minutes=2)
    turn_index = repo.next_turn_index(story_id)
    states = STATES.get(plan.template, {})
    summary = SUMMARIES.get(plan.template)
    for pos, turn in enumerate(plan.turns):
        clock += timedelta(minutes=turn.minutes)
        per_variant = states.get(pos, ())
        first = repo.insert_message(_message(story_id, turn_index, turn.role, turn.mode, turn.text))
        conn.execute("UPDATE messages SET created_at = ? WHERE id = ?", (_iso(clock), first.id))
        # State của từng phiên bản ghi lúc nó còn active (như worker trích xuất ngay sau mỗi lượt).
        _apply_state(repo, first, per_variant[0] if per_variant else None)
        last = first
        for n, alt in enumerate(turn.variants, start=1):
            clock += timedelta(minutes=1)
            last = repo.add_variant(_message(story_id, turn_index, "assistant", turn.mode, alt))
            conn.execute("UPDATE messages SET created_at = ? WHERE id = ?", (_iso(clock), last.id))
            _apply_state(repo, last, per_variant[n] if n < len(per_variant) else None)
        if summary is not None and summary[0] == pos:
            assert last.id is not None
            repo.add_summary(last.id, summary[1], turn_index)
        if turn.rating is not None:
            assert last.id is not None
            repo.set_feedback(last.id, turn.rating)  # type: ignore[arg-type]
        turn_index += 1
    conn.commit()


def _script_session(repo: Repo) -> str:
    """Phase 4b: mọi /api cần đăng nhập. Script cấp một phiên cho chủ máy ngay trong DB; chủ máy tạm có một
    hash ngẫu nhiên (không ứng với mật khẩu nào) để qua cổng "chưa thiết lập". `_end_script_session` gỡ cả hai,
    nên DB demo mở ra ở màn thiết lập chủ máy (backend in mã thiết lập khi khởi động)."""
    owner = repo.owner_account()
    assert owner.id is not None
    placeholder = PasswordHash(salt=os.urandom(16), digest=os.urandom(32), n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    with repo.transaction():
        auth_store.write_password(repo.conn, owner.id, placeholder, auth_clock.now(), temporary=False)
        token, _ = auth_store.insert_session(repo.conn, owner.id, now=auth_clock.now(), label="make_demo_db")
    return token


def _end_script_session(repo: Repo) -> None:
    owner = repo.owner_account()
    with repo.transaction():
        repo.conn.execute(
            "UPDATE accounts SET password_salt = NULL, password_hash = NULL, scrypt_n = NULL, scrypt_r = NULL,"
            " scrypt_p = NULL, password_changed_at = NULL, last_login_at = NULL WHERE id = ?",
            (owner.id,),
        )
        repo.conn.execute("DELETE FROM sessions")
        repo.conn.execute("DELETE FROM auth_attempts")
        auth_store.delete_setup(repo.conn)


async def _ok(resp: httpx.Response) -> Any:
    if resp.status_code >= 400:
        raise SystemExit(f"{resp.request.method} {resp.request.url.path} -> {resp.status_code}: {resp.text}")
    return resp.json()


async def build(db_path: Path, avatars_dir: Path, *, fresh_account: bool = False) -> dict[str, Any]:
    settings = Settings(
        db_path=db_path,
        ollama_url=DEAD_OLLAMA_URL,
        chat_model=DEMO_MODEL,
        num_ctx=8192,
        avatars_dir=avatars_dir,
        draft_model=DEMO_MODEL,
    )
    app = create_app(settings, FakeLLM())
    now = datetime.now(timezone.utc)
    async with app.router.lifespan_context(app):
        repo: Repo = app.state.repo
        seed_story_ids = [s.id for s in repo.list_stories(account_id=ANY_ACCOUNT)]
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo",
            cookies={SESSION_COOKIE: _script_session(repo)},
            headers={"X-Lyris": "1"},
        ) as client:
            png = {"content-type": "image/png"}
            if not fresh_account:
                await _ok(await client.put("/api/account", json=ACCOUNT))
                avatar = initials_png(ACCOUNT["display_name"], AVATAR_COLORS[ACCOUNT["display_name"]])
                await _ok(await client.put("/api/account/avatar", content=avatar, headers=png))

            own = await _ok(await client.post("/api/cards", json={"card": OWN_CARD}))
            own_id = int(own["id"])
            avatar = initials_png(OWN_CARD["name"], AVATAR_COLORS[OWN_CARD["name"]])
            await _ok(await client.put(f"/api/cards/{own_id}/avatar", content=avatar, headers=png))

            cards: dict[str, int] = {}
            for slug in TEMPLATES:
                card = await _ok(await client.post(f"/api/templates/{slug}/install"))
                cards[slug] = int(card["id"])

            personas: dict[str, int] = {}
            for body in PERSONAS:
                p = await _ok(await client.post("/api/personas", json=body))
                personas[body["name"]] = int(p["id"])
                avatar = initials_png(body["name"], AVATAR_COLORS[body["name"]])
                await _ok(await client.put(f"/api/personas/{p['id']}/avatar", content=avatar, headers=png))
            await _ok(await client.put("/api/settings", json={"default_persona_id": personas["Ngọc Anh"]}))

            created: list[dict[str, Any]] = []
            for plan in STORIES:
                story = await _ok(
                    await client.post(
                        "/api/stories",
                        json={"card_id": cards[plan.template], "persona_id": personas[plan.persona], "title": plan.title},
                    )
                )
                story_id = int(story["id"])
                _apply_opening(repo, story_id, plan.template)
                _write_turns(repo, story_id, plan, now)
                _apply_suggestions(repo, story_id, plan.template)
                if plan.final_mode != "story":
                    await _ok(await client.patch(f"/api/stories/{story_id}", json={"mode": plan.final_mode}))
                    # PATCH chạm updated_at của story: đặt lại cho đúng giờ của tin cuối.
                    last = repo.conn.execute(
                        "SELECT MAX(created_at) AS t FROM messages WHERE story_id = ?", (story_id,)
                    ).fetchone()["t"]
                    repo.conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (last, story_id))
                    repo.conn.commit()
                created.append({"id": story_id, "title": plan.title, "turns": len(plan.turns) + 1})

            for sid in seed_story_ids:
                assert sid is not None
                await _ok(await client.delete(f"/api/stories/{sid}"))

            listing = await _ok(await client.get("/api/stories"))
            account = await _ok(await client.get("/api/account"))
        _end_script_session(repo)
    return {
        "cards": cards,
        "own_card": own_id,
        "personas": personas,
        "stories": created,
        "listing": listing,
        "account": account,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tạo DB demo cho Lyris (không gọi Ollama).")
    parser.add_argument("db_path", type=Path, help="đường dẫn file SQLite sẽ tạo, ví dụ /tmp/lyris-demo/lyris.db")
    parser.add_argument("avatars_dir", type=Path, help="thư mục avatar, ví dụ /tmp/lyris-demo/avatars")
    parser.add_argument("--force", action="store_true", help="xoá DB đã có (cùng -wal, -shm) rồi tạo lại")
    parser.add_argument(
        "--fresh-account",
        action="store_true",
        help="giữ tài khoản mặc định chưa đặt tên (Bạn, @ban) để xem lời mời ở hub như lần mở đầu tiên",
    )
    args = parser.parse_args(argv)

    db_path: Path = args.db_path.expanduser().resolve()
    avatars_dir: Path = args.avatars_dir.expanduser().resolve()
    data_dir = (REPO_ROOT / "data").resolve()
    for target in (db_path, avatars_dir):
        if target == data_dir or data_dir in target.parents:
            print(f"Từ chối: {target} nằm trong {data_dir} (dữ liệu thật của bạn).", file=sys.stderr)
            return 2

    siblings = [db_path, db_path.with_name(db_path.name + "-wal"), db_path.with_name(db_path.name + "-shm")]
    if db_path.exists():
        if not args.force:
            print(f"{db_path} đã có. Thêm --force để xoá và tạo lại.", file=sys.stderr)
            return 1
        for f in siblings:
            f.unlink(missing_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    avatars_dir.mkdir(parents=True, exist_ok=True)

    result = asyncio.run(build(db_path, avatars_dir, fresh_account=args.fresh_account))
    account = result["account"]
    print(f"Đã tạo {db_path}")
    state = "đã đặt profile" if account["profile_completed"] else "chưa đặt tên"
    print(f"  Tài khoản: {account['display_name']} (@{account['handle']}), {state}")
    print(f"  Nhân vật tự tạo: {OWN_CARD['name']} (#{result['own_card']})")
    print("  Nhân vật mẫu: " + ", ".join(f"{slug} (#{cid})" for slug, cid in result["cards"].items()))
    print("  Persona: " + ", ".join(f"{name} (#{pid})" for name, pid in result["personas"].items()))
    for row in result["listing"]:
        mode = "DM" if row["mode"] == "dm" else "Story"
        print(f"  Story #{row['id']} [{mode}] {row['card_name']} và {row['persona_name']}: {row['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
