"""Новые персонажи через локальный ComfyUI (Qwen Image 2.1 edit), как вторая волна (art_tests/new_v1):
  chair  — рендер нашей 3D-модели (input/wnb_ref3d_<k>.png) перерисовать в стиле игры (образец wnb_m3final.png);
  seat   — посадить персонажа в нарисованную коляску (input/wnb_newchar_chair_<k>.png), стиль — фон мастерской.
python art_tests/gen_new_chars.py chair|seat <key> [seeds...]
Результат: ComfyUI/output/wnb/new_v2/<step>_<key>_s<seed>_00001_.png"""
import sys, json, urllib.request

API = "http://127.0.0.1:8188"

CHAIRS = {
    "yaga": "a Vermeiren D100 folding steel wheelchair: brushed silver steel frame with an X cross brace under the seat, "
            "black sling backrest and seat, padded black armrests, push handles with black grips, swing-away footrests "
            "with black footplates, large spoked rear wheels with grey tires and silver pushrims, grey solid front casters",
    "rusalka": "a Panthera X3 ultralight rigid wheelchair: dark graphite carbon-fibre frame, low black backrest, black seat "
               "cushion, no push handles, spoked rear wheels with black tires and light grey pushrims, small black front "
               "casters, light grey tubular footplate",
    "firebird": "a Quickie Nitrum rigid active wheelchair with a glossy fire-red frame, black backrest and black seat, black "
                "spoked rear wheels with pushrims and large dark grey round power-assist motor hubs in the wheel centres, "
                "small black front casters, black footplate",
    "leshy": "a Magic Mobility Extreme X8 off-road power wheelchair: four large knobby off-road tyres, a red body shell, "
             "black seat with a high contoured backrest and headrest, armrests with a joystick controller, long footplate",
    "raiju": "a Pride Jazzy 614 mid-wheel-drive power wheelchair: grey padded captain's seat with headrest, black armrests, "
             "joystick controller on the right armrest, burgundy power base cover, two large grey drive wheels with "
             "silver rims in the middle, small anti-tip casters front and rear, yellow suspension springs, grey footplate",
}

CHARS = {
    "yaga": ("Baba Yaga, a cheerful, mischievous very old witch from Slavic folk tales: long hooked nose, bright eyes, "
             "a wide grin with one tooth, grey hair under a red-and-black patterned headscarf tied under the chin, "
             "a long dark green skirt, an embroidered blouse and a patched apron, a small wooden broom tucked beside "
             "the seat, colourful woollen socks and felt boots",
             "Her hands rest on the pushrims, ready to zoom off."),
    "rusalka": ("Olga, a young mermaid from Slavic folk tales: short tousled ginger-red hair, freckles, friendly green "
                "eyes, a long shimmering teal-and-turquoise fish tail with a fin instead of legs resting on the "
                "footplate, a sea-green top with small shells, a string of pearls",
                "Her hands rest on the pushrims, sporty and confident."),
    "firebird": ("the Firebird from Russian folk tales: a large, graceful magical bird with glowing golden-orange and "
                 "scarlet feathers, a long flowing tail of flame-coloured plumes curling behind the backrest, a small "
                 "golden crest, kind bright eyes; small sparks drift around her feathers",
                 "Her wing tips rest on the pushrims."),
    "ra": ("Ra, the ancient Egyptian sun god: a friendly, dignified figure with the head of a falcon with golden-brown "
           "feathers and kind dark eyes, a glowing golden sun disc encircled by a cobra above his head, a white linen "
           "kilt, a broad collar necklace of gold, turquoise and lapis, golden arm bands, an ankh in one hand; a warm "
           "golden glow around him",
           "His free hand rests on the pushrim."),
    "gorynych": ("Zmey Gorynych, the three-headed dragon from Russian fairy tales, as a big, chubby, good-natured comic "
                 "character: green scaly body with a lighter yellow belly, small folded wings, a long tail curled around "
                 "the side of the chair, EXACTLY THREE heads (no more, no fewer) on three long necks with different funny expressions (one grinning, one "
                 "grumpy, one sleepy), small horns, a wisp of smoke from one nostril",
                 "One clawed hand rests on the joystick."),
    "leshy": ("Leshy, the friendly forest spirit from Slavic folk tales: a tall, kindly old man made of forest — "
              "bark-textured skin, a long mossy green beard with leaves and tiny mushrooms, small branch antlers, "
              "glowing green eyes, a coat of moss and woven grass, bark sandals",
              "One hand rests on the joystick, the other on the armrest."),
    "raiju": ("Raiju, the thunder beast from Japanese folklore: a fluffy blue-and-white weasel-like creature with fur like "
              "a storm cloud, a lightning-bolt-shaped tail crackling with small blue sparks, bright electric-blue eyes, "
              "a cheerful grin. NOT yellow, not a mouse",
              "One paw rests on the joystick."),
}


def node(cls, **inputs):
    return dict(class_type=cls, inputs=inputs)


def graph(prompt, img1, img2, seed, prefix):
    return {
        "1": node("UNETLoader", unet_name="qwen2.1\\qwen_image_2.1_int8_convrot.safetensors", weight_dtype="default"),
        "2": node("QwenImage21Cache", model=["1", 0], device="auto", dtype="default"),
        "3": node("CLIPLoader", clip_name="Qwen text_encoder\\qwen3vl_8b_int8_convrot.safetensors", type="qwen_image",
                  device="default"),
        "4": node("VAELoader", vae_name="qwen_image_2.1_vae_bf16.safetensors"),
        "L0": node("LoadImage", image=img1),
        "L1": node("LoadImage", image=img2),
        "6": node("TextEncodeQwenImage21", clip=["3", 0], prompt=prompt, negative_prompt="", resolution=0,
                  vae=["4", 0], **{"images.image_1": ["L0", 0], "images.image_2": ["L1", 0]}),
        "7": node("KSampler", model=["2", 0], seed=seed, steps=25, cfg=1.0, sampler_name="euler", scheduler="simple",
                  denoise=1.0, positive=["6", 0], negative=["6", 1], latent_image=["6", 2]),
        "8": node("VAEDecode", samples=["7", 0], vae=["4", 0]),
        "9": node("SaveImage", images=["8", 0], filename_prefix=prefix),
    }


def queue(g):
    req = urllib.request.Request(API + "/prompt", data=json.dumps({"prompt": g}).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["prompt_id"]


if __name__ == "__main__":
    step, key = sys.argv[1], sys.argv[2]
    seeds = [int(s) for s in sys.argv[3:]] or [11, 12]
    for seed in seeds:
        if step == "chair":
            p = ("Redraw the wheelchair from the picture <image1> as a finished illustration in the exact art style of "
                 "the wheelchair in <image2>: the same clean cartoon rendering with soft cel shading, crisp outlines, "
                 "subtle highlights and warm lighting. Keep EXACTLY the same wheelchair model, design, viewing angle, "
                 "proportions and every part visible in <image1>: frame tubes and their bends, wheels, spokes, pushrims, "
                 "casters and forks, wheel locks, footrests, armrests, upholstery, cushions. It is " + CHAIRS[key] + ". "
                 "No logos, no brand names, no text. Single object, whole and uncropped, plain white background, "
                 "no shadow, no people.")
            g = graph(p, f"wnb_ref3d_{key}.png", "wnb_m3final.png", seed, f"wnb/new_v2/chair_{key}_s{seed}")
        else:
            who, hands = CHARS[key]
            p = ("Seat " + who + " in the wheelchair from <image1>, drawn in the exact clean, bright, colorful cartoon "
                 "style of <image2>. The character sits naturally and comfortably upright on the seat with the back "
                 "against the backrest, looking friendly and full of character, facing the viewer. " + hands + " "
                 "Keep the wheelchair exactly as in <image1>: the same viewing angle, size, position, proportions, "
                 "colors and every part. The whole wheelchair and character are fully visible, uncropped. "
                 "Plain white background, no room, no text.")
            chair = {"ra": "firebird", "gorynych": "raiju"}.get(key, key)          # Ра — в коляске, что готовилась для Жар-птицы
            g = graph(p, f"wnb_newchar_chair_{chair}.png", "wnb_bg_workshop.png", seed, f"wnb/new_v2/seat_{key}_s{seed}")
        print(step, key, seed, queue(g))
