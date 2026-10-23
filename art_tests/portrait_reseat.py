"""Портрет клиента в новой коляске (Qwen Image 2.1 edit в локальном ComfyUI): <image1> — рендер новой коляски
(art_tests/portrait_chair.py), <image2> — нынешний портрет (персонаж, поза, стиль).
python art_tests/portrait_reseat.py <ключ> [seeds…]   -> scratchpad/poses/local/reseat_<ключ>_s<seed>…png"""
import os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SP = r"C:\Users\wario\AppData\Local\Temp\claude\D--wheels-and-bones\d845888a-7a45-42b9-a337-635687a142cf\scratchpad"
sys.path.insert(0, SP)
from comfy_client import upload, queue, wait, download

JOBS = {   # ключ: (рендер коляски, портрет, описание коляски, руки)
    "sorceress": ("portrait_chair_m3/portrait_chair_m3_00_white.png", "client_sorceress.png",
                  "a Permobil M3 Corpus mid-wheel-drive power wheelchair: black contoured seat and high backrest with a "
                  "headrest, black armrests, a joystick controller with a red knob on the armrest, six wheels (big drive "
                  "wheels with purple three-spoke hubs in the middle, small casters front and back), glossy purple body "
                  "panels, black footplates",
                  "Her right hand rests on the joystick."),
    "goblin": ("portrait_chair_edge4/portrait_chair_edge4_00_white.png", "client_goblin.png",
               "a Quantum Edge 4 power wheelchair with the seat raised high on a black scissor lift: black seat and "
               "backrest with a headrest, black armrests, a joystick controller on the right armrest, a low black power "
               "base with red accents, six small black wheels, a black footplate",
               "His hand rests on the joystick."),
    "badger": ("portrait_chair_f5/portrait_chair_f5_00_white.png", "client_f5.png",
               "a Permobil F5 Corpus front-wheel-drive power wheelchair: black contoured seat and high backrest with a "
               "headrest, black armrests with a joystick controller on the armrest, big black front drive wheels with "
               "three-spoke hubs, small black casters at the back, a dark graphite power base with small yellow "
               "accents, two black footplates raised high right in front of the seat (adjusted for short legs), a "
               "small anti-tip wheel low under them",
               "One paw rests on the joystick, the other holds her little honey pot. Her short legs hang down from the "
               "front edge of the seat cushion and her feet stand flat directly ON the two raised footplates: the "
               "footplates are the only thing under her feet - no step, ledge or box under her feet and no second, "
               "lower pair of footplates. Both big drive wheels are complete and round."),
    "golem": ("portrait_chair_trident/portrait_chair_trident_00_white.png", "client_golem.png",
              "a Drive Trident HD heavy-duty power wheelchair: big black padded captain's seat with a headrest, black "
              "padded armrests, a joystick controller on the right armrest, big front drive wheels with silver rims, "
              "black rear casters, yellow suspension springs, a black frame and a black footplate",
              "One stone hand rests on the joystick."),
    "lizard": ("portrait_chair_whillc2/portrait_chair_whillc2_00_white.png", "client_whillc2.png",
               "a WHILL Model C2 power wheelchair: black seat and backrest, black curved armrests with a round joystick "
               "controller at the front of the right armrest, big black front omni-wheels with many small rollers, "
               "black solid rear wheels, a matte black base and a black footplate",
               "She holds her open map book on her lap, one hand near the joystick."),
    "leshy": ("portrait_chair_leshy/portrait_chair_leshy_00_white.png", "client_leshy.png",
              "a Magic Mobility Extreme X8 off-road power wheelchair: four big knobby off-road tyres, a glossy red body "
              "shell, a black seat with a high contoured backrest and headrest, black armrests with a joystick controller "
              "on the right one, a long black footplate",
              "One hand rests on the joystick, the other on the armrest."),
    "gorynych": ("portrait_chair_gorynych/portrait_chair_gorynych_00_white.png", "client_gorynych.png",
                 "a Pride Jazzy 614 mid-wheel-drive power wheelchair: a big black padded captain's seat with a headrest, "
                 "black armrests with a joystick on the right one, two big black drive wheels with cross-shaped hubs in "
                 "the middle, small black casters front and back, a black base, a black footplate",
                 "One clawed hand rests on the joystick. He has EXACTLY THREE heads, as in <image2>."),
    "owl_grandson": ("portrait_chair_focuscr/portrait_chair_focuscr_00_white.png", "client_focuscr_grandson.png",
                     "a Ki Mobility Focus CR tilt-in-space manual wheelchair, TILTED BACK: the seat and backrest are "
                     "reclined back together, a headrest, dark navy blue frame, big black rear wheels with black "
                     "push rims, small black front casters, raised black footplates, push handles at the back",
                     "The tall grandson owl stands behind the wheelchair holding both push handles, exactly as in "
                     "<image2>; the grandmother owl sits in the tilted seat holding her spyglass."),
    "owl": ("portrait_chair_focuscr/portrait_chair_focuscr_01_white.png", "client_focuscr.png",
            "a Ki Mobility Focus CR tilt-in-space manual wheelchair, TILTED BACK: the seat and backrest are reclined back "
            "together, a headrest, dark navy blue frame, big black rear wheels with black push rims, small black front "
            "casters, raised black footplates",
            "She sits comfortably reclined in the tilted seat, holding her spyglass."),
    # Матильда заново (поза — не со старого портрета: там ноги на «ступеньке», Qwen дорисовывал вторые подножки)
    "badger_new": ("portrait_chair_f5/portrait_chair_f5_00_white.png", "client_f5.png",
                   "a Permobil F5 Corpus front-wheel-drive power wheelchair: black contoured seat and high backrest with "
                   "a headrest, black armrests; on the front end of the left armrest ONE joystick controller box with "
                   "ONE small straight upright black joystick knob, exactly as in <image1>; big black front drive wheels "
                   "with three-spoke hubs, small black casters at the back, a dark graphite power base with small yellow "
                   "accents, EXACTLY TWO black footplates side by side, raised high just below the front edge of the "
                   "seat (adjusted for her short legs); no small wheels at the front",
                   "Her left paw rests on the armrest just behind the joystick controller, not covering it; the other paw "
                   "holds her little honey pot on her lap. Her short legs bend at the front edge of the seat and her two "
                   "feet stand flat on the two footplates, one foot on each. Only these two footplates, nothing else "
                   "under her feet. Both big drive wheels are complete and round."),
    # фольклорные клиенты в моделях Meshy (вместо колясок Tripo), 2026-10-23
    "yaga": ("portrait_chair_yaga/portrait_chair_yaga_01_white.png", "client_yaga.png",
             "a Vermeiren D100 folding steel wheelchair: brushed silver steel frame with an X cross brace under the seat, "
             "black sling backrest and seat, black padded armrests on silver side frames, push handles with black grips, "
             "swing-away footrests with black footplates, large spoked rear wheels with grey tyres and silver pushrims, "
             "grey solid front casters on silver forks",
             "She holds a BIG, long witch's twig broom (a besom) in both hands across her lap: a long wooden handle and a "
             "large bushy bundle of twigs, clearly much bigger than the little broom in <image2>. Her feet in felt boots "
             "rest on the footplates."),
    "rusalka": ("portrait_chair_rusalka/portrait_chair_rusalka_01_white.png", "client_rusalka.png",
                "a Panthera X3 ultralight rigid wheelchair: matte black carbon-fibre frame, low black backrest, black seat "
                "cushion, no push handles, black spoked rear wheels with silver-grey pushrims, small black front casters, "
                "a light grey tubular loop footplate",
                "Her hands rest on her lap; her mermaid tail lies on the footplate, as in <image2>."),
    "mummy": ("portrait_chair_ra/portrait_chair_ra_01_white.png", "client_mummy.png",
              "a Quickie Nitrum rigid active wheelchair: glossy red tubular frame, black padded backrest and black seat "
              "cushion, black spoked rear wheels with black pushrims and large dark grey round power-assist motor hubs "
              "(Alber e-motion) with light grey caps in the wheel centres, small black front casters, a black footplate",
              "The mummy's bandaged hands rest on the knees, as in <image2>."),
    # Мартин и Бомм в Invacare 9000 Meshy (было — синее сиденье, серебристая рама), 2026-10-23
    "martin": ("portrait_chair_basic/portrait_chair_basic_00_white.png", "martin.png",
               "an Invacare 9000 standard manual wheelchair: black steel frame, black nylon sling seat and backrest with a small blue Invacare badge on the side, black padded armrests, swing-away footrests with black footplates, big black mag rear wheels with straight composite spokes and thin silver pushrims, small black front casters",
               "His hands rest on his lap, as in <image2>; his feet rest on the footplates."),
    # Мартин заново: поза по рендеру (подножки подняты под его голень), культя левой ноги — хорошо видна, не сливается
    "martin_new": ("portrait_chair_basic/portrait_chair_basic_00_white.png", "martin.png",
                   "an Invacare 9000 standard manual wheelchair: black steel frame, black nylon sling seat and backrest "
                   "with a small blue Invacare badge on the side, black padded armrests, swing-away footrests with black "
                   "footplates, big black mag rear wheels with straight composite spokes and thin silver pushrims, small "
                   "black front casters",
                   "Martin is a friendly teenage zombie boy. His hands rest on his thighs. His LEFT leg ends just below the "
                   "knee: the left blue jeans leg is neatly folded up and pinned over a short stump wrapped in a clean "
                   "light beige bandage, resting on the front edge of the black seat, clearly visible and separate from "
                   "the wheelchair. His RIGHT leg is whole: his right bare green foot hangs freely in the air in front "
                   "of the seat, above the footplates, NOT touching anything — nothing at all under the foot (no step, "
                   "no extra footrest, no box). The wheelchair's two footplates stay lower down, empty, exactly as in "
                   "<image1>. Exactly one foot in the picture."),
    # Тилли — нарисована Codex (art_tests/codex_tilly), здесь только для portrait_install
    "fairy": ("portrait_chair_fairy/portrait_chair_fairy_00_white.png", "client_fairy.png", "", ""),
    "yuki": ("portrait_chair_aeroz/portrait_chair_aeroz_00_white.png", "client_aeroz.png", "", ""),   # Codex (codex_yuki)
    "troll": ("portrait_chair_troll/portrait_chair_troll_00_white.png", "client_troll.png",
              "an Invacare 9000 standard manual wheelchair: black steel frame, black nylon sling seat and backrest with a small blue Invacare badge on the side, black padded armrests, swing-away footrests with black footplates, big black mag rear wheels with straight composite spokes and thin silver pushrims, small black front casters",
              "His big hands rest on his round belly, as in <image2>; his big feet rest on the footplates."),
}
FREE_POSE = {"badger_new", "martin_new"}   # от старого портрета — только облик персонажа, поза и коляска — по рендеру


def white(path, name):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    tmp = os.path.join(SP, "poses", "local", name)
    bg.convert("RGB").save(tmp)
    return tmp


def node(cls, **inputs):
    return dict(class_type=cls, inputs=inputs)


key = sys.argv[1]
seeds = [int(s) for s in sys.argv[2:]] or [11, 22, 33]
chair, portrait, desc, hands = JOBS[key]
i1 = upload(os.path.join(ROOT, "tools", "render_out", chair), f"wnb_reseat_chair_{key}.png")
orig = os.path.join(HERE, "retired", portrait)                    # персонаж — с исходного портрета (до новых колясок)
i2 = upload(white(orig if os.path.exists(orig) else os.path.join(ROOT, "assets", portrait), f"in_portrait_{key}.png"),
            f"wnb_reseat_char_{key}.png")
prompt = ("Redraw the character from <image2> sitting in the wheelchair from <image1>. Keep the character EXACTLY as in "
          "<image2>: the same face, hair, clothes, colours, proportions, expression and sitting pose, and the same clean "
          "cartoon art style with soft cel shading and dark outlines. Replace only the wheelchair: it must be exactly "
          "the wheelchair from <image1> — the same model, design, viewing angle and every part — drawn in the same "
          "cartoon style as <image2>. It is " + desc + ". " + hands + " The character sits naturally on the seat, back "
          "against the backrest, feet on the footplate. Whole character and wheelchair fully visible, uncropped. "
          "Plain pure white background, no shadow, no text.")
if key in FREE_POSE:
    prompt = ("Draw the character from <image2> sitting in the wheelchair from <image1>. Keep the character's look EXACTLY "
              "as in <image2>: the same face, hair, clothes, colours, body proportions and expression, nothing added "
              "(no new glasses, hats or accessories), and "
              "the same clean cartoon art style with soft cel shading and dark outlines. The wheelchair must be exactly "
              "the wheelchair from <image1> — the same model, design, viewing angle and every part, nothing added or "
              "doubled — drawn in the same cartoon style. It is " + desc + ". " + hands + " The character sits naturally on the "
              "seat, back against the backrest. Whole character and wheelchair fully visible, uncropped. Plain pure "
              "white background, no shadow, no text.")
ids = []
for seed in seeds:
    g = {"1": node("UNETLoader", unet_name="qwen2.1\\qwen_image_2.1_int8_convrot.safetensors", weight_dtype="default"),
         "2": node("QwenImage21Cache", model=["1", 0], device="auto", dtype="default"),
         "3": node("CLIPLoader", clip_name="Qwen text_encoder\\qwen3vl_8b_int8_convrot.safetensors", type="qwen_image",
                   device="default"),
         "4": node("VAELoader", vae_name="qwen_image_2.1_vae_bf16.safetensors"),
         "L0": node("LoadImage", image=i1), "L1": node("LoadImage", image=i2),
         "6": node("TextEncodeQwenImage21", clip=["3", 0], prompt=prompt, negative_prompt="", resolution=0,
                   vae=["4", 0], **{"images.image_1": ["L0", 0], "images.image_2": ["L1", 0]}),
         "7": node("KSampler", model=["2", 0], seed=seed, steps=25, cfg=1.0, sampler_name="euler", scheduler="simple",
                   denoise=1.0, positive=["6", 0], negative=["6", 1], latent_image=["6", 2]),
         "8": node("VAEDecode", samples=["7", 0], vae=["4", 0]),
         "9": node("SaveImage", images=["8", 0], filename_prefix=f"wnb/reseat/{key}_s{seed}")}
    ids.append((seed, queue(g)))
for seed, pid in ids:
    for p in download(wait(pid, timeout=1800), os.path.join(SP, "poses", "local"), f"reseat_{key}_s{seed}"):
        print(p)
